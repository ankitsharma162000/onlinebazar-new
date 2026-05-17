import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import ChatSession, ChatMessage, PendingQuestion
from .brain import find_answer


def _get_or_create_session(request):
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    session, _ = ChatSession.objects.get_or_create(
        session_key=session_key,
        defaults={'user_name': request.session.get('user_name', 'Guest')}
    )
    return session


@csrf_exempt
@require_POST
def chat_message(request):
    try:
        data = json.loads(request.body)
        user_msg = data.get('message', '').strip()
        if not user_msg:
            return JsonResponse({'error': 'Empty message'}, status=400)

        session = _get_or_create_session(request)

        # Save user message
        ChatMessage.objects.create(session=session, sender='user', message=user_msg)

        # Find answer
        answer, source = find_answer(user_msg)

        if answer:
            ChatMessage.objects.create(
                session=session, sender='bot', message=answer, status='answered'
            )
            return JsonResponse({'reply': answer, 'source': source, 'status': 'answered'})
        else:
            # Escalate to superadmin
            pending = PendingQuestion.objects.create(session=session, question=user_msg)
            bot_reply = (
                "🙋 I don't have an answer to that yet. Your question has been forwarded to "
                "our support team. Please wait — they will reply shortly in this chat!"
            )
            ChatMessage.objects.create(
                session=session, sender='bot', message=bot_reply, status='pending'
            )
            return JsonResponse({
                'reply': bot_reply,
                'source': 'escalated',
                'status': 'pending',
                'pending_id': str(pending.id),
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def check_updates(request):
    """
    Frontend polls this every 5 seconds.
    Returns any superadmin replies for THIS session that haven't been delivered yet.
    """
    try:
        session = _get_or_create_session(request)

        # Find answered questions for this session not yet delivered
        answered = PendingQuestion.objects.filter(
            session=session,
            status='answered',
            answer__isnull=False,
        ).exclude(answer='')

        replies = []
        for q in answered:
            replies.append({
                'question': q.question,
                'answer': q.answer,
            })
            # Save admin reply as a ChatMessage too
            ChatMessage.objects.create(
                session=session,
                sender='admin',
                message=q.answer,
                status='answered'
            )
            # Mark delivered — delete so it's not sent again
            q.delete()

        return JsonResponse({'replies': replies})
    except Exception as e:
        return JsonResponse({'replies': [], 'error': str(e)})

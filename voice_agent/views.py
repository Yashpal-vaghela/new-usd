from django.shortcuts import render

def chat_bot(request):
    return render(request, 'chat_bot.html')

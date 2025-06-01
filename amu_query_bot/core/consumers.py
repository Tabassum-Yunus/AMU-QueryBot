import json
from channels.generic.websocket import AsyncWebsocketConsumer
from . import utils
from .models import ChatMessage
import traceback
from django.core.cache import cache
from datetime import datetime, timedelta
import asyncio

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chain = None
        self.initialization_error = None

    async def initialize_components(self):
        """Initialize chain if not already initialized"""
        if self.chain is None:
            try:
                print("Initializing ChatConsumer components...")
                # Use the get_qa_chain function from utils
                self.chain = utils.get_qa_chain()
                if self.chain is None:
                    raise ValueError("Failed to initialize QA chain")
                print("ChatConsumer initialization successful")
                return True
            except Exception as e:
                print(f"Error initializing ChatConsumer: {str(e)}")
                print(traceback.format_exc())
                self.initialization_error = str(e)
                return False
        return True

    async def connect(self):
        print(f"WebSocket connect attempt by user: {self.scope['user']}")
        if not self.scope["user"].is_authenticated:
            print("Unauthenticated connection attempt - closing")
            await self.close()
            return

        await self.accept()
        print("Connection accepted")

        # Initialize components after accepting the connection
        if not await self.initialize_components():
            print(f"Connection accepted but closing due to initialization error: {self.initialization_error}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Sorry, the chat service is currently unavailable. Please try again later.'
            }))
            await self.close()
            return

    async def disconnect(self, close_code):
        print(f"WebSocket disconnected with code: {close_code}")
        pass

    def check_rate_limit(self):
        """Rate limit: 30 messages per 5 minutes per user"""
        user_id = self.scope["user"].id
        cache_key = f"chat_rate_limit_{user_id}"
        
        # Get the current timestamp
        now = datetime.now()
        
        # Get or create the list of timestamps for this user
        timestamps = cache.get(cache_key, [])
        
        # Remove timestamps older than 5 minutes
        cutoff = now - timedelta(minutes=5)
        timestamps = [ts for ts in timestamps if ts > cutoff]
        
        # Check if user has exceeded rate limit
        if len(timestamps) >= 30:
            print(f"Rate limit exceeded for user {user_id}")
            return False
        
        # Add current timestamp and update cache
        timestamps.append(now)
        cache.set(cache_key, timestamps, timeout=300)  # 5 minutes timeout
        return True

    async def receive(self, text_data):
        print(f"Received message from user {self.scope['user'].id}")
        try:
            # Check rate limit
            if not self.check_rate_limit():
                print("Rate limit check failed")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'You are sending messages too quickly. Please wait a few minutes and try again.'
                }))
                return

            text_data_json = json.loads(text_data)
            message = text_data_json['message']
            print(f"Processing message: {message[:50]}...")  # Log first 50 chars of message

            # Get response from the AI using utils.get_response
            try:
                print("Getting AI response...")
                full_response = ""
                async for chunk in utils.get_response(message):
                    full_response += chunk
                    await self.send(text_data=json.dumps({
                        'type': 'chat',
                        'message': chunk,
                        'is_final': False
                    }))
                
                # Store the complete message in the database
                try:
                    await asyncio.to_thread(
                        ChatMessage.objects.create,
                        user=self.scope["user"],
                        query=message,
                        response=full_response
                    )
                except Exception as e:
                    print(f"Error storing chat message: {str(e)}")
                    print(traceback.format_exc())
                    # Continue even if storage fails - don't impact user experience

                # Send final message to indicate completion
                await self.send(text_data=json.dumps({
                    'type': 'chat',
                    'message': '',
                    'is_final': True
                }))

            except Exception as e:
                print(f"Error getting AI response: {str(e)}")
                print(traceback.format_exc())
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Sorry, there was an error processing your request. Please try again.'
                }))
                return

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid message format'
            }))
        except KeyError as e:
            print(f"Key error: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message content missing'
            }))
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            print(traceback.format_exc())
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'An unexpected error occurred. Please try again.'
            }))
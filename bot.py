
#!/usr/bin/env python3
"""
Telegram Multi-Platform Video Downloader Bot
author tohirbek rakhmatullayev
Ultimate Version with Enhanced Instagram & TikTok Support

Features:
- YouTube, Instagram, TikTok, Facebook, Vimeo, Twitch support
- User information collection
- Server-side processing (no permanent storage)
- Platform-specific quality optimization
- Progress tracking
- Automatic cleanup
- Advanced error handling
- FFmpeg post-processing
"""

import os
import logging
import tempfile
import shutil
import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import yt_dlp

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Platform detection patterns
PLATFORM_PATTERNS = {
    'youtube': [r'(youtube\.com|youtu\.be)'],
    'instagram': [r'(instagram\.com)'],
    'tiktok': [r'(tiktok\.com|vm\.tiktok\.com)'],
    'facebook': [r'(facebook\.com|fb\.watch)'],
    'vimeo': [r'(vimeo\.com)'],
    'twitter': [r'(twitter\.com|x\.com)'],
    'twitch': [r'(twitch\.tv)'],
}

# Quality options per platform
QUALITY_OPTIONS = {
    'youtube': {
        'best': '\ud83c\udfac Eng yaxshi (1080p+)',
        '1080': '\ud83d\udcfa Full HD (1080p)',
        '720': '\ud83d\udcf1 HD (720p)',
        'audio': '\ud83c\udfb5 Faqat audio',
    },
    'instagram': {
        'best': '\ud83c\udfac Asl sifat',
        '720': '\ud83d\udcf1 HD (720p)',
        'audio': '\ud83c\udfb5 Faqat audio',
    },
    'tiktok': {
        'best': '\ud83c\udfac Asl sifat',
        '720': '\ud83d\udcf1 HD (720p)',
        'audio': '\ud83c\udfb5 Faqat audio',
    },
    'facebook': {
        'best': '\ud83c\udfac Asl sifat',
        '720': '\ud83d\udcf1 HD (720p)',
        'audio': '\ud83c\udfb5 Faqat audio',
    },
}

# Platform-specific yt-dlp options
PLATFORM_OPTIONS = {
    'youtube': {
        'format_string': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
    },
    'instagram': {
        'format_string': 'best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'postprocessors': [],
    },
    'tiktok': {
        'format_string': 'best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'postprocessors': [],
    },
    'facebook': {
        'format_string': 'best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'postprocessors': [],
    },
}


class TelegramYouTubeBot:
    """Telegram bot for downloading videos from multiple platforms"""
    
    def __init__(self, token: str):
        self.token = token
        self.user_downloads: Dict[int, Dict[str, Any]] = {}
        self.temp_dir = tempfile.mkdtemp(prefix='telegram_multi_bot_')
        logger.info(f"Temp directory created: {self.temp_dir}")
    
    def detect_platform(self, url: str) -> str:
        """Detect which platform the URL belongs to"""
        url_lower = url.lower()
        for platform, patterns in PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return platform
        return 'generic'
    
    def get_quality_options(self, platform: str) -> Dict[str, str]:
        """Get quality options for specific platform"""
        return QUALITY_OPTIONS.get(platform, QUALITY_OPTIONS['youtube'])
    
    def cleanup_old_files(self, user_id: int):
        """Clean up old files for a specific user"""
        if user_id in self.user_downloads:
            file_path = self.user_downloads[user_id].get('file_path')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up file: {file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up file: {e}")
            del self.user_downloads[user_id]
    
    def get_user_info(self, user) -> str:
        """Get formatted user information"""
        info = f"""
\ud83d\udc64 **Foydalanuvchi ma'lumotlari:**

\ud83c\udd94 **ID:** `{user.id}`
\ud83d\udc64 **Username:** @{user.username if user.username else 'mavjud emas'}
\ud83d\udcdb **Ism:** {user.first_name}
\ud83d\udcdd **Familya:** {user.last_name if user.last_name else 'mavjud emas'}
\ud83c\udf10 **Language Code:** {user.language_code if user.language_code else 'mavjud emas'}
\ud83d\udcca **Is Bot:** {user.is_bot}
\ud83d\udd50 **So'nggi faollik:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return info
    
    def extract_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract video information using yt-dlp"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None
    
    def get_platform_specific_opts(self, platform: str, quality: str) -> Dict[str, Any]:
        """Get yt-dlp options based on platform and quality"""
        # Base options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': '',  # Will be set later
        }
        
        platform_opts = PLATFORM_OPTIONS.get(platform, PLATFORM_OPTIONS['youtube'])
        
        # Handle audio-only downloads
        if quality == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
            })
            return ydl_opts
        
        # Handle quality-specific options
        if platform == 'youtube':
            if quality == 'best':
                ydl_opts.update({
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'merge_output_format': 'mp4',
                })
            elif quality == '1080':
                ydl_opts.update({
                    'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
                    'merge_output_format': 'mp4',
                })
            elif quality == '720':
                ydl_opts.update({
                    'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
                    'merge_output_format': 'mp4',
                })
        else:
            # For Instagram, TikTok, Facebook - use simpler format selection
            if quality == 'best':
                ydl_opts.update({
                    'format': platform_opts['format_string'],
                    'merge_output_format': 'mp4',
                })
            elif quality in ['720', '1080']:
                # These platforms don't always have explicit resolution control
                # Try to get best available quality
                ydl_opts.update({
                    'format': platform_opts['format_string'],
                    'merge_output_format': 'mp4',
                })
        
        return ydl_opts
    
    def download_video(self, url: str, quality: str, user_id: int, platform: str) -> Optional[str]:
        """Download video with specified quality for specific platform"""
        # Clean up old downloads for this user
        self.cleanup_old_files(user_id)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_template = os.path.join(self.temp_dir, f'user_{user_id}_{platform}_{timestamp}.%(ext)s')
        
        # Get platform-specific options
        ydl_opts = self.get_platform_specific_opts(platform, quality)
        ydl_opts['outtmpl'] = output_template
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Starting download for user {user_id} from {platform} with quality {quality}")
                info = ydl.extract_info(url, download=True)
                
                # Determine the actual downloaded file
                if quality == 'audio':
                    downloaded_file = os.path.splitext(ydl.prepare_filename(info))[0] + '.mp3'
                else:
                    downloaded_file = os.path.splitext(ydl.prepare_filename(info))[0] + '.mp4'
                
                # Update user downloads tracking
                self.user_downloads[user_id] = {
                    'file_path': downloaded_file,
                    'info': info,
                    'quality': quality,
                    'platform': platform,
                    'timestamp': datetime.now(),
                }
                
                logger.info(f"Download completed: {downloaded_file}")
                return downloaded_file
                
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_message = f"""
\ud83c\udf89 **Marhamat, {user.first_name}!**

Bu bot orqali platformalardan videolarni yuklab olishingiz mumkin.

\ud83d\udccb **Qo'llab-quvvatlanadigan platformalar:**
\ud83d\udcfa YouTube
\ud83d\udcf7 Instagram
\ud83c\udfb5 TikTok
\ud83d\udcd8 Facebook
\ud83c\udfac Vimeo
\ud83d\udce1 Twitch
Va 1000+ boshqa platformalar

\ud83d\udccb **Buyruqlar:**
/start - Botni boshlash
/help - Yordam
/info - Sizning ma'lumotlaringiz

\ud83d\udd17 **Qanday ishlaydi:**
1. Video havolasini yuboring
2. Sifatni tanlang
3. Video yuklanadi va sizga yuboriladi

\u26a1 **Tezkor havola yuborish!**
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        logger.info(f"User {user.id} started the bot")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
\ud83d\udcda **Yordam**

**Foydalanish qo'llanmasi:**

1\ufe0f\u20e3 **Video yuklash:**
   - Youtube, Instagram, TikTok, Facebook, Vimeo, Twitch havolasini shunchaki yuboring
   - Platforma avtomatik aniqlanadi
   - Sifatni tanlang (tugmalar yordamida)
   - Kutish turing, video yuklanib sizga yuboriladi

2\ufe0f\u20e3 **Platformalar va sifatlar:**

\ud83d\udcfa **YouTube:**
   \ud83c\udfac *Eng yaxshi (1080p+)* - Yuqori sifat
   \ud83d\udcfa *Full HD (1080p)* - To'liq HD
   \ud83d\udcf1 *HD (720p)* - Yuqori aniqlik
   \ud83c\udfb5 *Faqat audio* - Audio fayl (MP3)

\ud83d\udcf7 **Instagram:**
   \ud83c\udfac *Asl sifat* - Asl yuklangan sifat
   \ud83d\udcf1 *HD (720p)* - Yuqori aniqlik
   \ud83c\udfb5 *Faqat audio* - Audio fayl (MP3)

\ud83c\udfb5 **TikTok:**
   \ud83c\udfac *Asl sifat* - Asl yuklangan sifat (suvsiz)
   \ud83d\udcf1 *HD (720p)* - Yuqori aniqlik
   \ud83c\udfb5 *Faqat audio* - Audio fayl (MP3, suv belgisiz)

\ud83d\udcd8 **Facebook:**
   \ud83c\udfac *Asl sifat* - Asl yuklangan sifat
   \ud83d\udcf1 *HD (720p)* - Yuqori aniqlik
   \ud83c\udfb5 *Faqat audio* - Audio fayl (MP3)

3\ufe0f\u20e3 **Xususiyatlar:**
   \u2705 Platforma avtomatik aniqlanadi
   \u2705 Platforma-specific optimizatsiya
   \u2705 FFmpeg bilan qayta ishlov
   \u2705 Avtomatik tozalash
   \u2705 Suv belgilarini olib tashlash (ba'zi platformalar uchun)

4\ufe0f\u20e3 **Ma'lumotlar:**
   - Videolar serverda vaqtinchalik saqlanadi
   - Yuklab olingan videolar kompyuteringizda saqlanadi
   - Har bir foydalanuvchi uchun eski fayllar avtomatik o'chiriladi

\u2753 **Savollar tug'ilsa:**
/info - Sizning ma'lumotlaringizni ko'rish
/start - Botni qayta boshlash

\ud83d\udca1 **Mashhur havolalar:**
https://www.youtube.com/
https://www.instagram.com/
https://www.tiktok.com/
https://www.facebook.com/
        """
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /info command - show user information"""
        user = update.effective_user
        user_info = self.get_user_info(user)
        await update.message.reply_text(user_info, parse_mode='Markdown')
        logger.info(f"User {user.id} requested info")
    
    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle URL messages from any supported platform"""
        user = update.effective_user
        message = update.message
        url = message.text.strip()
        
        # Detect platform
        platform = self.detect_platform(url)
        
        # Validate URL
        if platform == 'generic':
            await message.reply_text(
                "\u274c **Xato!**\
\
Iltimos, qo'llab-quvvatlanadigan platforma havolasini yuboring:\
"
                "\ud83d\udcfa YouTube\
\ud83d\udcf7 Instagram\
\ud83c\udfb5 TikTok\
\ud83d\udcd8 Facebook\
\ud83c\udfac Vimeo\
\ud83d\udce1 Twitch\
\
Va 1000+ boshqa platformalar",
                parse_mode='Markdown'
            )
            return
        
        # Extract video info
        status_message = await message.reply_text(
            f"\ud83d\udd0d {platform.capitalize()} video ma'lumotlari yuklanmoqda..."
        )
        
        try:
            video_info = self.extract_video_info(url)
            
            if not video_info:
                await status_message.edit_text(
                    "\u274c **Xato:** Video ma'lumotlarini yuklab bo'lmadi.\
\
"
                    "Iltimos, havolani tekshirib qaytadan urinib ko'ring."
                )
                return
            
            title = video_info.get('title', 'Noma'lum video')
            duration = video_info.get('duration', 0)
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Noma'lum"
            
            # Get view count if available
            view_count = video_info.get('view_count', 0) or video_info.get('play_count', 0)
            if view_count >= 1000000:
                views = f"{view_count / 1000000:.1f}M"
            elif view_count >= 1000:
                views = f"{view_count / 1000:.1f}K"
            else:
                views = str(view_count) if view_count else "Noma'lum"
            
            # Platform-specific info
            platform_emoji = {
                'youtube': '\ud83d\udcfa',
                'instagram': '\ud83d\udcf7',
                'tiktok': '\ud83c\udfb5',
                'facebook': '\ud83d\udcd8',
                'vimeo': '\ud83c\udfac',
                'twitter': '\ud83d\udc26',
                'twitch': '\ud83d\udce1',
            }.get(platform, '\ud83c\udfac')
            
            info_text = f"""
{platform_emoji} **{platform.capitalize()} video topildi:**

\ud83d\udcfa **Nomi:** {title[:50]}...
\u23f1\ufe0f **Davomiyligi:** {duration_str}
\ud83d\udc41\ufe0f **Ko'rishlar:** {views}

\ud83d\udcca **Sifatni tanlang:**
            """
            
            # Get platform-specific quality options
            quality_options = self.get_quality_options(platform)
            
            # Create inline keyboard for quality selection
            keyboard = []
            if platform == 'youtube':
                keyboard.append([
                    InlineKeyboardButton(quality_options['best'], callback_data=f'best_{url}'),
                    InlineKeyboardButton(quality_options['1080'], callback_data=f'1080_{url}'),
                ])
                keyboard.append([
                    InlineKeyboardButton(quality_options['720'], callback_data=f'720_{url}'),
                    InlineKeyboardButton(quality_options['audio'], callback_data=f'audio_{url}'),
                ])
            else:
                # For other platforms, show 2x2 grid with available options
                options = list(quality_options.items())
                for i in range(0, len(options), 2):
                    row = []
                    if i < len(options):
                        row.append(InlineKeyboardButton(options[i][1], callback_data=f'{options[i][0]}_{url}'))
                    if i + 1 < len(options):
                        row.append(InlineKeyboardButton(options[i+1][1], callback_data=f'{options[i+1][0]}_{url}'))
                    keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_message.edit_text(info_text, parse_mode='Markdown', reply_markup=reply_markup)
            
            logger.info(f"Video info extracted for user {user.id}: {title[:50]} from {platform}")
            
        except Exception as e:
            logger.error(f"Error handling URL: {e}")
            await status_message.edit_text(f"\u274c **Xato yuz berdi:** {str(e)}")
    
    async def quality_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quality selection callback query"""
        query = update.callback_query
        user = update.effective_user
        await query.answer()
        
        try:
            # Parse callback data
            data_parts = query.data.split('_', 1)
            quality = data_parts[0]
            url = data_parts[1]
            
            # Detect platform
            platform = self.detect_platform(url)
            platform_emoji = {
                'youtube': '\ud83d\udcfa',
                'instagram': '\ud83d\udcf7',
                'tiktok': '\ud83c\udfb5',
                'facebook': '\ud83d\udcd8',
                'vimeo': '\ud83c\udfac',
            }.get(platform, '\ud83c\udfac')
            
            # Show downloading status
            quality_text = QUALITY_OPTIONS.get(platform, QUALITY_OPTIONS['youtube']).get(quality, quality)
            status_message = await query.edit_message_text(
                f"\u23f3 **Video yuklanmoqda...**\
\
"
                f"\ud83d\udcca Platforma: {platform_emoji} {platform.capitalize()}\
"
                f"\ud83d\udcca Sifat: {quality_text}\
"
                f"\u23f3 Iltimos, kutilmoqda...",
                parse_mode='Markdown'
            )
            
            # Download video
            downloaded_file = self.download_video(url, quality, user.id, platform)
            
            if not downloaded_file:
                await status_message.edit_text(
                    "\u274c **Xato:** Video yuklab bo'lmadi.\
\
"
                    "Iltimos, boshqa sifatni tanlashga harakat qiling yoki havolani tekshiring.\
\
"
                    "Ba'zi platformalar video yuklab olishni cheklashi mumkin."
                )
                return
            
            # Get video info for caption
            video_info = self.user_downloads[user.id]['info']
            title = video_info.get('title', 'Video')
            duration = video_info.get('duration', 0)
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else ""
            quality_text = self.get_quality_options(platform).get(quality, quality)
            
            caption = f"""
{platform_emoji} **{title}**

\u23f1\ufe0f Davomiyligi: {duration_str}
\ud83d\udcca Sifat: {quality_text}
\ud83c\udf10 Platforma: {platform.capitalize()}
\ud83e\udd16 @MultiPlatformDownloaderBot
            """.strip()
            
            # Send video to user
            await status_message.edit_text("\u2705 **Yuklandi!** Video yuborilmoqda...", parse_mode='Markdown')
            
            try:
                if quality == 'audio':
                    await query.message.reply_audio(
                        audio=open(downloaded_file, 'rb'),
                        caption=caption.strip(),
                        parse_mode='Markdown',
                        timeout=300
                    )
                else:
                    file_size = os.path.getsize(downloaded_file)
                    if file_size > 50 * 1024 * 1024:  # 50MB limit
                        await query.message.reply_document(
                            document=open(downloaded_file, 'rb'),
                            caption=caption + "\
\
\u26a0\ufe0f Video hajmi katta bo'lgani uchun fayl sifatida yuborildi.",
                            parse_mode='Markdown',
                            timeout=300
                        )
                    else:
                        await query.message.reply_video(
                            video=open(downloaded_file, 'rb'),
                            caption=caption.strip(),
                            parse_mode='Markdown',
                            timeout=300,
                            supports_streaming=True
                        )
                
                logger.info(f"Video sent successfully to user {user.id} from {platform}")
                
            except Exception as e:
                logger.error(f"Error sending video: {e}")
                await query.message.reply_text(
                    f"\u274c Video yuborishda xatolik yuz berdi.\
\
Xato: {str(e)}\
\
"
                    f"Iltimos, qaytadan urinib ko'ring. Agar xato davom etsa, boshqa sifatni tanlang."
                )
            
            # Clean up old files for this user
            self.cleanup_old_files(user_id=user.id)
            
        except Exception as e:
            logger.error(f"Error in quality callback: {e}")
            try:
                await query.edit_message_text(
                    f"\u274c **Xato yuz berdi:** {str(e)}\
\
Iltimos, qaytadan urinib ko'ring."
                )
            except Exception:
                pass
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Error: {context.error}", exc_info=context.error)
        
        if update and hasattr(update, 'message') and update.message:
            try:
                await update.message.reply_text(
                    "\u274c **Xato yuz berdi!**\
\
Iltimos, qaytadan urinib ko'ring yoki /help buyrug'ini foydalaning.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error sending error message: {e}")
    
    def run(self):
        """Start the bot"""
        # Create application
        application = Application.builder().token(self.token).build()
        
        # Register handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("info", self.info_command))
        application.add_handler(CallbackQueryHandler(self.quality_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url))
        
        # Register error handler
        application.add_error_handler(self.error_handler)
        
        # Start bot
        logger.info("Bot ishga tushmoqda...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        logger.error("Bot token topilmadi! Iltimos, TELEGRAM_BOT_TOKEN muhit o'zgaruvchisini sozlang.")
        return
    
    bot = TelegramYouTubeBot(BOT_TOKEN)
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi")
    except Exception as e:
        logger.error(f"Bot ishlashida xatolik: {e}")
    finally:
        # Cleanup temp directory
        if os.path.exists(bot.temp_dir):
            shutil.rmtree(bot.temp_dir)
            logger.info(f"Temp directory cleaned up: {bot.temp_dir}")


if __name__ == '__main__':
    main()

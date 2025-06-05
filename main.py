import customtkinter as ctk
import ttkbootstrap as ttk
import tkinter as tk
import vlc
import yt_dlp
import os
import time
import json
import hashlib
import subprocess
from PIL import Image
from fuzzywuzzy import process, fuzz
import threading

class VideoManager():
    def __init__(self) -> None:
        self.app = ctk.CTk(fg_color="#000000")
        self.app.title("Video Manager")
        self.app.geometry("800x600")
        self.app._windows_set_titlebar_color("#2c3e50")

        search_and_download_frame = ctk.CTkFrame(self.app, fg_color="#2c3e50")
        search_and_download_frame.pack(fill=tk.X, padx=20, pady=10)
        search_bar = ctk.CTkEntry(search_and_download_frame, placeholder_text="Enter video text or url to download...", width=400)
        search_bar.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        search_button = ctk.CTkButton(search_and_download_frame, text="Search", command=lambda: self.search_videos(search_bar.get()))
        search_button.grid(row=0, column=1, padx=10, pady=10)
        download_button = ctk.CTkButton(search_and_download_frame, text="⤓", command=lambda: self.start_long_running_task(search_bar.get()))
        download_button.grid(row=0, column=2, padx=10, pady=10)


        self.display_video_frame = ctk.CTkScrollableFrame(self.app, fg_color="#0F0F0F")
        self.display_video_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        # Initialize vlc_instance once for the application
        
        # Initialize media_player to None; it will be created per playback


        # Ensure 'downloads' and 'thumbnails' and 'metadata' directories exist
        os.makedirs("downloads", exist_ok=True)
        os.makedirs("thumbnails", exist_ok=True)
        os.makedirs("metadata", exist_ok=True)


        videos = self.get_videos()
        self.show_videos_on_ui(videos)

        self.app.mainloop()
    def search_videos(self, query):
        if query:
            query = query.lower().split()
            metadata_files = os.listdir("metadata")
            matching_videos = []
            for metadata_file in metadata_files:
                if metadata_file.endswith('.json'):
                    with open(os.path.join("metadata", metadata_file), 'r') as f:
                        metadata = json.load(f)
                        if all(word in metadata.get("title", "").lower() for word in query):
                            matching_videos.append(metadata_file.replace('.json', '.mp4'))  # Assuming video files are named the same as metadata files
                        elif any(word in metadata.get("uploader", "").lower() for word in query):
                            matching_videos.append(metadata_file.replace('.json', '.mp4'))

            print(f"\n\n\n{matching_videos}")
            self.show_videos_on_ui(matching_videos)
        else:
            print("Search query is empty. Displaying all videos.")
            video_files = self.get_videos()
            self.show_videos_on_ui(video_files)
    def get_videos(self):
        files = os.listdir("downloads")
        video_files = [f for f in files if f.endswith(('.mp4', '.avi', '.mkv'))]
        return video_files

    def show_videos_on_ui(self, video_files):
        for widget in self.display_video_frame.winfo_children():
            widget.destroy()
        print(f"Showing {len(video_files)} videos on UI.")
        row = 0
        col = 0
        for video_file in video_files:
            video_path = os.path.join("downloads", video_file)
            thumbnail_path = os.path.join("thumbnails", video_file)
            thumbnail_path = thumbnail_path.replace('.mp4', '.webp')  # Adjust for thumbnail extension

            if os.path.exists(thumbnail_path): # Added check for thumbnail file existence
                # print(f"Thumbnail found for {video_file}: {thumbnail_path}")
                pil_img = Image.open(thumbnail_path)

                temp_img = pil_img.copy()
                temp_img.thumbnail((200, 200), Image.Resampling.LANCZOS)  # Resize to fit the UI

                img = ctk.CTkImage(temp_img, size=temp_img.size)
                video_frame = ctk.CTkFrame(self.display_video_frame, fg_color="#0F0F0F")
                video_frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
                video_image_label = ctk.CTkLabel(video_frame, image=img, text="")
                video_image_label.pack(padx=10, pady=10)
                video_image_label.bind("<Button-1>", lambda e, path=video_path: self.play_video(path))

                json_file_path = os.path.join("metadata", video_file.replace('.mp4', '.json'))
                try:
                    with open(json_file_path, 'r') as f:
                        metadata = json.load(f)
                        video_title = metadata.get("title", "Unknown Title")
                        video_uploader = metadata.get("uploader", "Unknown Uploader")
                        video_duration = metadata.get("duration", "Unknown Duration")
                    video_info_label = ctk.CTkLabel(video_frame, text=f"{video_title}\n{video_uploader}\n{video_duration} seconds", fg_color="#0F0F0F", text_color="white",width=200, height=60,wraplength=250)
                    video_info_label.pack(padx=10, pady=10)
                    video_info_label.bind("<Button-1>", lambda e, path=video_path: self.play_video(path))
                    # print(f"Metadata loaded for {video_file}: {video_title}, {video_uploader}, {video_duration} seconds")
                except FileNotFoundError:
                    print(f"Metadata file not found for {json_file_path}. Using default values.")
                    video_info_label = ctk.CTkLabel(video_frame, text="Unknown Title\nUnknown Uploader\nUnknown Duration", fg_color="#0F0F0F", text_color="white")
                    video_info_label.pack(padx=10, pady=10)

                col += 1
                if col > 3: # Adjust this for desired number of columns
                    col = 0
                    row += 1
            else:
                print(f"Thumbnail not found for {video_file} at {thumbnail_path}. Skipping display.")


    # This is the method for extracting thumbnails from *local* video files using FFmpeg
    def get_video_thumbnail(self, video_path, output_thumbnail_path=None, timestamp_seconds=1, width=150, height=100):
        if not os.path.exists(video_path):
            print(f"Error: Video file not found at {video_path}")
            return None

        if not output_thumbnail_path:
            os.makedirs("thumbnails", exist_ok=True)
            hash_object = hashlib.md5(video_path.encode())
            hex_dig = hash_object.hexdromd()# type: ignore
            output_thumbnail_path = os.path.join("thumbnails", f"{hex_dig}.png")

        output_dir = os.path.dirname(output_thumbnail_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        command = [
            "ffmpeg",
            "-ss", str(timestamp_seconds),
            "-i", video_path,
            "-vframes", "1",
            "-s", f"{width}x{height}",
            "-y",
            output_thumbnail_path
        ]

        try:
            print(f"Attempting FFmpeg thumbnail extraction for: {video_path}")
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
            print(f"FFmpeg thumbnail saved to: {output_thumbnail_path}")
            return output_thumbnail_path
        except subprocess.CalledProcessError as e:
            print(f"Error generating thumbnail with FFmpeg:")
            print(f"Command: {' '.join(command)}")
            print(f"STDOUT: {e.stdout.decode()}")
            print(f"STDERR: {e.stderr.decode()}")
            return None
        except FileNotFoundError:
            print("Error: FFmpeg not found in system PATH. Please ensure FFmpeg is installed and accessible.")
            return None

    def play_video(self, video_path):
        def on_video_frame_configure(self, event):
            # Only set HWND if media_player exists and is valid
            if media_player:
                media_player.set_hwnd(event.widget.winfo_id())
        def _stop_and_close_player(self, player_window, media_player):
            """Stops the current video, releases its resources, and closes the player window."""
            if media_player:
                media_player.stop()
                media_player.release()  # Release resources for this specific player
                media_player = None     # Reset media_player to None
            player_window.destroy()          # Close the Toplevel window
        def pause_video(self):
            if media_player:
                if media_player.is_playing():
                    media_player.pause()
                else:
                    media_player.play()
        def toggle_fullscreen(root):
            if controls_frame.winfo_viewable():
                root.attributes("-fullscreen",True)
                controls_frame.grid_forget()
            else:
                root.attributes("-fullscreen",False)
                controls_frame.grid(row=0,column=0, sticky="ew")
        def increase_volume(self, volume_slider):
            if media_player:
                current_volume = media_player.audio_get_volume()
                new_volume = min(current_volume+10, 200)
                media_player.audio_set_volume(new_volume)
                volume_slider.set(new_volume)
        def decrease_volume(self, volume_slider):
            if media_player:
                current_volume = media_player.audio_get_volume()
                new_volume = max(current_volume-10, 0)
                media_player.audio_set_volume(new_volume)
                volume_slider.set(new_volume)

        def update_playback_ui():
            if media_player and media_player.is_playing():
                position = media_player.get_position() * 100
                progress_bar.set(position)

                length_ms = media_player.get_length()
                current_time_ms = media_player.get_time()

                if length_ms > 0: # Avoid division by zero
                    current_minutes, current_seconds = divmod(current_time_ms // 1000, 60)
                    total_minutes, total_seconds = divmod(length_ms // 1000, 60)
                    progress_bar_label.configure(text=f"{int(current_minutes):02}:{int(current_seconds):02} / {int(total_minutes):02}:{int(total_seconds):02}")
                else:
                    progress_bar_label.configure(text="00:00 / 00:00")
            root.after(1000, update_playback_ui)  # Update every second
        print(f"Attempting to play video: {video_path}")
        root = ctk.CTkToplevel(self.app)
        root.title("Video Player")
        root.geometry("800x600")
        vlc_instance = vlc.Instance()
        media_player = vlc_instance.media_player_new()

        controls_frame = ctk.CTkFrame(root, fg_color="#2c3e50",height=30)
        controls_frame.grid(row=0, column=0, sticky="ew")
        root.grid_rowconfigure(0, weight=0)

        pause_button = ctk.CTkButton(controls_frame, text="Pause/play", command=lambda: pause_video(self=self))
        pause_button.pack(side=tk.LEFT, padx=0, pady=0)

        stop_button = ctk.CTkButton(controls_frame, text="Stop", command=lambda: _stop_and_close_player(self=self,player_window=root,media_player=media_player))
        stop_button.pack(side=tk.LEFT, padx=0, pady=0)

        volume_slider = ctk.CTkSlider(controls_frame, from_=0, to=200, command=lambda value: media_player.audio_set_volume(int(value)))#type: ignore
        volume_slider.set(50)
        volume_slider.pack(side=tk.LEFT, padx=0, pady=0)

        video_frame = ctk.CTkFrame(root, fg_color="black")
        video_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        root.grid_rowconfigure(1, weight=1)  # Allow video frame to expand
        root.grid_columnconfigure(0, weight=1)

        video_frame.bind("<Configure>", lambda event: on_video_frame_configure(self=self,event=event))

        progress_bar = ctk.CTkSlider(root, width=800,from_=0, to=100, command=lambda value: media_player.set_position(float(value)/100))#type: ignore
        progress_bar.grid(row=2, column=0, padx=0, pady=0, sticky="ew")
        progress_bar.columnconfigure(0, weight=1)  # Allow progress bar to expand
        progress_bar_label = ctk.CTkLabel(root, text=f"00:00 / 00:00", fg_color="#2c3e50")
        progress_bar_label.grid(row=3, column=0, padx=0, pady=0, sticky="ew")
        media = vlc_instance.media_new(video_path)
        media_player.set_media(media)

        root.update_idletasks()
        media_player.set_hwnd(video_frame.winfo_id())

        media_player.play()

        root.bind("<Left>", lambda e: media_player.set_position(max(0, media_player.get_position() - 0.05)))# type: ignore
        root.bind("<Right>", lambda e: media_player.set_position(min(1, media_player.get_position() + 0.05)))# type: ignore
        root.bind("<Up>", lambda e: increase_volume(self=self,volume_slider=volume_slider))
        root.bind("<Down>", lambda e: decrease_volume(self=self,volume_slider=volume_slider))
        root.bind("<space>", lambda e: pause_video(root))
        root.bind("<f>",lambda e: toggle_fullscreen(root=root))

        # update_playback_ui() # Start the periodic update
        # Handle window close protocol (e.g., clicking the 'X' button)
        update_playback_ui()
        root.protocol("WM_DELETE_WINDOW", lambda: _stop_and_close_player(self=self, player_window=root,media_player=media_player))

    def download_video(self, url):
        

        # Inner function to get video title using yt-dlp
        def get_video_title_yt(video_url):
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return info.get('title', 'Unknown Title')# type: ignore

        print(f"Attempting to get title for URL: {url}")
        print(f"Video Title: {get_video_title_yt(url)}")

        # Inner function to get video thumbnail using yt-dlp
        def get_video_thumbnail_yt(video_url, width=150, height=100):
            # The explicit ffmpeg_path is often necessary for yt-dlp to find it
            ffmpeg_path = r"C:\ffmpeg-7.1.1-full_build\bin" 
            
            if not os.path.exists(ffmpeg_path):
                print(f"WARNING: Explicit FFmpeg path '{ffmpeg_path}' does not exist. Relying on system PATH.")
                ffmpeg_location_option = {}
            else:
                ffmpeg_location_option = {'ffmpeg_location': ffmpeg_path}
            
            url_hash = hashlib.sha256(video_url.encode('utf-8')).hexdigest()
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'writethumbnail': True,
                'outtmpl': os.path.join("thumbnails", f'{url_hash}.%(ext)s'),
                **ffmpeg_location_option, 
            }
            
            os.makedirs("thumbnails", exist_ok=True)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(video_url, download=True)
                    # yt-dlp saves the thumbnail automatically based on 'outtmpl'
                    # It might save as .webp or .jpg depending on the source
                    thumbnail_filename = f"{url_hash}.webp" # Default to webp as you use it for display
                    # Check for actual extension if needed, but the outtmpl should handle it
                    
                    thumbnail_path = os.path.join("thumbnails", thumbnail_filename)
                    # A more robust check might be to glob for the hash in the thumbnails dir
                    found_thumbnails = [f for f in os.listdir("thumbnails") if f.startswith(url_hash) and f.endswith(('.webp', '.jpg', '.png'))]
                    if found_thumbnails:
                        thumbnail_path = os.path.join("thumbnails", found_thumbnails[0])
                        print(f"yt-dlp thumbnail saved to: {thumbnail_path}")
                        return thumbnail_path
                    else:
                        print(f"yt-dlp reported success but thumbnail not found at expected path: {thumbnail_path}")
                        return None
                except yt_dlp.DownloadError as e:
                    print(f"Error downloading thumbnail with yt-dlp: {e}")
                    return None
                except Exception as e:
                    print(f"An unexpected error occurred during yt-dlp thumbnail download: {e}")
                    return None

        def get_video_metadata(url):
                ydl_opts = {
                    'quiet': True,
                    'extract_flat': True,
                    'force_generic_extractor': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=False)
                    metadata = {
                        "title": info_dict.get("title"),# type: ignore
                        "id": info_dict.get("id"),# type: ignore
                        "original_url": info_dict.get("original_url") or url,# type: ignore
                        "duration": info_dict.get("duration"),# type: ignore
                        "uploader": info_dict.get("uploader")# type: ignore
                    }
                    os.makedirs("metadata", exist_ok=True) # Ensure metadata dir exists
                    with open(os.path.join("metadata", f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"), 'w') as f:
                        json.dump(metadata, f, indent=4)

        def install_video(url):
            url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
            ydl_opts = {
                'format': 'bestvideo*+bestaudio/best',
                'outtmpl': os.path.join("downloads", f'{url_hash}.%(ext)s'),
                'merge_output_format': 'mp4',
                'ffmpeg_location': r"C:\ffmpeg-7.1.1-full_build\bin",
                'noplaylist': True,
                'nocheckcertificate': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'quiet': False, # Set to False to see progress/errors
                'progress': True, # Show progress
                'retries': 3,
                'fragment_retries': 3,
                'postprocessors': [],
            }
            os.makedirs("downloads", exist_ok=True)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    print(f"Downloading video from URL: {url}")
                    ydl.download([url])
                    print("Video download complete.")
                except yt_dlp.DownloadError as e:
                    print(f"Error downloading video with yt-dlp: {e}")
                except Exception as e:
                    print(f"An unexpected error occurred during video download: {e}")

        print("Attempting yt-dlp thumbnail download...")
        downloaded_thumbnail_path = get_video_thumbnail_yt(url)
        install_video(url)
        get_video_metadata(url)
        if downloaded_thumbnail_path:
            print(f"yt-dlp thumbnail process complete.")
        else:
            print(f"yt-dlp thumbnail process failed or file not found.")
    def refresh_ui_after_download(self):
        print("Refreshing UI after download...")
        video_files = self.get_videos()
        self.show_videos_on_ui(video_files)
        print("UI refreshed with new video list.")
    def long_running_task(self, url):
        print(f"Starting long-running task for URL: {url}")
        time.sleep(5)
        self.download_video(url)
        self.app.after(0, self.refresh_ui_after_download)
    def start_long_running_task(self, url):
        thread = threading.Thread(target=self.long_running_task, args=(url,))
        thread.daemon = True
        thread.start()
        print(f"Thread started for URL: {url}")

if __name__ == "__main__":
    video_manager = VideoManager()
    print("VideoManager initialized.")
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import vlc
import os
import time

class VideoPlayerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CustomTkinter VLC Video Player")
        self.geometry("900x600")
        self.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle window closing event

        # --- VLC Instance and Player ---
        # Initialize VLC instance
        # If VLC is not found, you might need to provide the path to its installation directory
        # Example for Windows: self.vlc_instance = vlc.Instance(r'--plugin-path=C:\Program Files\VideoLAN\VLC\plugins')
        # Ensure the path points to the 'plugins' directory inside your VLC installation.
        self.vlc_instance = vlc.Instance()
        self.media_player = self.vlc_instance.media_player_new()
        self.current_media = None # To keep track of the loaded media

        # --- UI Layout ---
        # Video Display Frame
        self.video_frame = ctk.CTkFrame(self, fg_color="black")
        self.video_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        # Bind configure event to resize VLC video output
        self.video_frame.bind("<Configure>", self.on_video_frame_configure)

        # Controls Frame
        self.controls_frame = ctk.CTkFrame(self, fg_color="#2c3e50")
        self.controls_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        # --- Buttons ---
        self.open_button = ctk.CTkButton(self.controls_frame, text="Open Video", command=self.open_video)
        self.open_button.pack(side="left", padx=5, pady=5)

        self.play_button = ctk.CTkButton(self.controls_frame, text="Play", command=self.play_video)
        self.play_button.pack(side="left", padx=5, pady=5)

        self.pause_button = ctk.CTkButton(self.controls_frame, text="Pause", command=self.pause_video)
        self.pause_button.pack(side="left", padx=5, pady=5)

        self.stop_button = ctk.CTkButton(self.controls_frame, text="Stop", command=self.stop_video)
        self.stop_button.pack(side="left", padx=5, pady=5)

        # --- Volume Slider ---
        self.volume_slider = ctk.CTkSlider(self.controls_frame, from_=0, to=100, command=self.set_volume, width=100)
        self.volume_slider.set(70) # Default volume
        self.media_player.audio_set_volume(70)
        self.volume_slider.pack(side="left", padx=10, pady=5)
        
        self.mute_button = ctk.CTkButton(self.controls_frame, text="Mute", command=self.toggle_mute, width=60)
        self.mute_button.pack(side="left", padx=5, pady=5)
        self.is_muted = False

        # --- Progress Slider ---
        self.progress_slider = ctk.CTkSlider(self, from_=0, to=1000, command=self.set_position)
        self.progress_slider.pack(side="bottom", fill="x", padx=10, pady=5)
        self.progress_slider.set(0) # Initial position
        
        self.time_label = ctk.CTkLabel(self, text="00:00 / 00:00")
        self.time_label.pack(side="bottom", padx=10, pady=2)

        # Start updating progress bar periodically
        self.update_progress_bar()

    def on_video_frame_configure(self, event):
        """Called when the video frame is resized."""
        if self.media_player and self.media_player.get_state() != vlc.State.in_dll:
            # Set the video output window handle to the frame's ID
            # This is crucial for VLC to render inside the Tkinter frame
            # winfo_id() provides the HWND on Windows
            self.media_player.set_hwnd(self.video_frame.winfo_id())
            # VLC might need a slight delay or re-rendering to adjust perfectly
            # For simplicity, we just set the HWND on configure.
            # More advanced handling might involve media_player.video_set_scale()
            # or media_player.set_aspect_ratio() if you want to control aspect.

    def open_video(self):
        """Opens a file dialog to select a video and starts playback."""
        filepath = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=(("Video files", "*.mp4 *.avi *.mkv *.mov *.wmv"), ("All files", "*.*"))
        )
        if filepath:
            self.current_media = self.vlc_instance.media_new(filepath)
            self.media_player.set_media(self.current_media)
            
            # Ensure the video frame is ready for VLC output
            # This call is important to ensure the HWND is set before playback starts
            self.on_video_frame_configure(None) # Pass None as event, as it's not a real configure event
            
            self.play_video()
            self.progress_slider.set(0) # Reset slider
            self.time_label.configure(text="00:00 / 00:00") # Reset time label
            print(f"Loaded video: {filepath}")

    def play_video(self):
        """Starts or resumes video playback."""
        if self.media_player.get_media():
            self.media_player.play()
            print("Playing video.")
        else:
            print("No video loaded to play.")

    def pause_video(self):
        """Pauses video playback."""
        if self.media_player.get_media():
            self.media_player.pause()
            print("Paused video.")

    def stop_video(self):
        """Stops video playback."""
        if self.media_player.get_media():
            self.media_player.stop()
            self.progress_slider.set(0)
            self.time_label.configure(text="00:00 / 00:00")
            print("Stopped video.")

    def set_volume(self, value):
        """Sets the volume of the media player."""
        self.media_player.audio_set_volume(int(value))
        # If muted, unmute when volume is changed
        if self.is_muted and value > 0:
            self.media_player.audio_toggle_mute()
            self.is_muted = False
            self.mute_button.configure(text="Mute")
        elif not self.is_muted and value == 0:
            self.is_muted = True
            self.mute_button.configure(text="Unmute")

    def toggle_mute(self):
        """Toggles mute state."""
        if self.media_player.get_media():
            self.media_player.audio_toggle_mute()
            self.is_muted = not self.is_muted
            self.mute_button.configure(text="Unmute" if self.is_muted else "Mute")
            print(f"Volume {'muted' if self.is_muted else 'unmuted'}.")

    def set_position(self, value):
        """Sets the playback position based on the slider value."""
        # VLC position is a float between 0.0 and 1.0
        # Our slider is 0 to 1000, so divide by 1000.0
        if self.media_player.get_media():
            self.media_player.set_position(float(value) / 1000.0)
            print(f"Set position to {value/10.0}%")

    def update_progress_bar(self):
        """Updates the progress slider and time label periodically."""
        if self.media_player and self.media_player.get_media():
            # Get current position (0.0 to 1.0)
            position = self.media_player.get_position()
            # Get current time in milliseconds
            current_time_ms = self.media_player.get_time()
            # Get total duration in milliseconds
            total_duration_ms = self.media_player.get_length()

            if position != -1: # -1 means no media or not playing
                self.progress_slider.set(position * 1000) # Scale to 0-1000

            # Update time label
            if current_time_ms != -1 and total_duration_ms != -1:
                current_s = current_time_ms // 1000
                total_s = total_duration_ms // 1000
                
                current_minutes = current_s // 60
                current_seconds = current_s % 60
                total_minutes = total_s // 60
                total_seconds = total_s % 60

                time_text = f"{current_minutes:02}:{current_seconds:02} / {total_minutes:02}:{total_seconds:02}"
                self.time_label.configure(text=time_text)
            else:
                self.time_label.configure(text="00:00 / 00:00")

            # Check if video has ended
            if self.media_player.get_state() == vlc.State.Ended:
                self.stop_video() # Automatically stop and reset UI

        # Schedule the next update
        self.after(100, self.update_progress_bar) # Update every 100ms

    def on_closing(self):
        """Ensures VLC resources are released when the app closes."""
        if self.media_player:
            self.media_player.stop()
            self.media_player.release() # Release the media player
        if self.vlc_instance:
            self.vlc_instance.release() # Release the VLC instance
        self.destroy() # Destroy the CustomTkinter window

if __name__ == "__main__":
    app = VideoPlayerApp()
    app.mainloop()

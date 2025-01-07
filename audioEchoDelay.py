import numpy as np
import soundfile as sf
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import pygame
import time
import os


class AudioEchoApp:
    """Application for adding an echo effect to audio files using a graphical user interface."""

    def __init__(self, root):
        """Initialize the application with the main window and UI components."""
        self.root = root
        self.sound_data = None  # Loaded audio data (numpy array)
        self.sound_rate = None  # Sampling rate of the audio file
        self.sound_file = None  # Path to the currently loaded audio file
        self.setup_ui()  # Set up the UI elements

    def setup_ui(self):
        """Set up the graphical user interface components."""
        self.root.title("Audio Echo & Delay Application")
        self.root.geometry("400x300")

        # Register drag-and-drop support
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

        # UI Components
        self.file_label = tk.Label(self.root, text="Drag and drop an audio file here or click to load")
        self.file_label.pack(pady=10)

        open_button = tk.Button(self.root, text="Open File", command=self.open_file)
        open_button.pack(pady=5)

        tk.Label(self.root, text="Delay (ms)").pack()  # Label for delay input
        self.delay_entry = tk.Entry(self.root)  # Entry widget for delay
        self.delay_entry.pack()

        tk.Label(self.root, text="Decay (0.0 - 1.0)").pack()  # Label for decay input
        self.decay_entry = tk.Entry(self.root)  # Entry widget for decay
        self.decay_entry.pack()

        save_button = tk.Button(self.root, text="Save File", command=self.save_file)
        save_button.pack(pady=10)

        play_button = tk.Button(self.root, text="Play", command=self.play_sound)
        play_button.pack(side=tk.LEFT, padx=5)

        stop_button = tk.Button(self.root, text="Stop", command=self.stop_sound)
        stop_button.pack(side=tk.RIGHT, padx=5)

    def load_audio(self, file_path):
        """
        Load an audio file into memory.

        Args:
            file_path (str): Path to the audio file to load.
        """
        try:
            self.sound_data, self.sound_rate = sf.read(file_path)
            self.sound_file = file_path
            self.file_label.config(text=f"Loaded: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def add_echo(self, delay_ms, decay):
        """
        Apply an echo effect to the loaded audio data.

        Args:
            delay_ms (int): Delay for the echo effect in milliseconds.
            decay (float): Decay factor for the echo effect (0.0 to 1.0).

        Returns:
            numpy.ndarray: Audio data with the echo effect applied.

        Raises:
            ValueError: If no audio data is loaded.
        """
        if self.sound_data is None:
            raise ValueError("No audio data loaded.")

        # Convert delay from milliseconds to samples
        delay_samples = int((delay_ms / 1000) * self.sound_rate)

        # Create an echo array initialized to zeros
        echo = np.zeros_like(self.sound_data)

        # Apply echo effect for mono and stereo audio
        if self.sound_data.ndim == 1:  # Mono audio
            for i in range(delay_samples, len(self.sound_data)):
                echo[i] = decay * self.sound_data[i - delay_samples]
        else:  # Stereo audio
            for i in range(delay_samples, len(self.sound_data)):
                echo[i, 0] = decay * self.sound_data[i - delay_samples, 0]
                echo[i, 1] = decay * self.sound_data[i - delay_samples, 1]

        # Return the audio data with the echo effect applied
        return np.clip(self.sound_data + echo, -1.0, 1.0)

    def play_sound(self):
        """Play the audio file with the echo effect applied."""
        try:
            # Retrieve parameters from input fields
            delay_ms = int(self.delay_entry.get())
            decay = float(self.decay_entry.get())

            # Apply echo effect
            modified_data = self.add_echo(delay_ms, decay)

            # Initialize pygame mixer
            pygame.mixer.quit()  # Ensure no existing mixer instance is running
            pygame.mixer.init(frequency=self.sound_rate)

            # Generate a unique temporary filename using a timestamp
            temp_file = f"temp_with_echo_{int(time.time() * 1000)}.wav"
            sf.write(temp_file, modified_data, self.sound_rate)

            # Save the modified audio to a temporary file
            temp_file = "temp_with_echo.wav"
            sf.write(temp_file, modified_data, self.sound_rate)

            # Play the temporary file using pygame
            pygame.mixer.init()
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play sound: {e}")
        # Schedule the temporary file for deletion after playback finishes
            self.root.after(int(pygame.mixer.Sound(temp_file).get_length() * 1000) + 100,
                lambda: os.remove(temp_file))
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play sound: {e}")
    
    def stop_sound(self):
        """Stop playback of the currently playing audio."""
        pygame.mixer.music.stop()



    def save_file(self):
        """Save the audio file with the echo effect applied."""
        try:
            if self.sound_data is None:
                raise ValueError("No audio data to save.")

            # Retrieve parameters from input fields
            delay_ms = int(self.delay_entry.get())
            decay = float(self.decay_entry.get())

            # Apply echo effect
            modified_data = self.add_echo(delay_ms, decay)

            # Prompt user to select a save location
            save_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV Files", "*.wav")])
            if save_path:
                # Write the modified audio to the selected file
                sf.write(save_path, modified_data, self.sound_rate)
                messagebox.showinfo("Success", f"File saved: {save_path}")
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

    def open_file(self):
        """Open a file dialog to select an audio file and load it."""
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav")])
        if file_path:
            self.load_audio(file_path)

    def on_drop(self, event):
        """
        Handle drag-and-drop file loading.

        Args:
            event: The TkinterDnD drop event containing the file path.
        """
        file_path = event.data.strip("{}")
        self.load_audio(file_path)


if __name__ == "__main__":
    # Create the main application window and start the app
    root = TkinterDnD.Tk()
    app = AudioEchoApp(root)
    root.mainloop()

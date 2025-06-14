import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import markdown
import pyttsx3
import os
import threading
import queue
from bs4 import BeautifulSoup
from langdetect import detect, LangDetectException
from tkinterdnd2 import DND_FILES, TkinterDnD
from gtts import gTTS
import tempfile
import re
from typing import List

class MarkdownSpeaker:
    def __init__(self, master):
        self.master = master
        self.setup_ui()
        self.setup_tts_engine()
        self.setup_drag_and_drop()
        self.current_files = []
        self.current_text = ""
        
    def setup_ui(self):
        self.master.title("Advanced Markdown Speaker")
        self.master.geometry("600x500")
        self.master.resizable(True, True)
        
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TButton', font=('Arial', 10), padding=5)
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        
        self.main_frame = ttk.Frame(self.master, padding=10)
        self.main_frame.pack(expand=True, fill=tk.BOTH)
        
        ttk.Label(self.main_frame, text="Selected Files:").grid(row=0, column=0, sticky="w")
        self.file_listbox = tk.Listbox(self.main_frame, height=5, selectmode=tk.EXTENDED)
        self.file_listbox.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=5)
        
        scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.grid(row=1, column=3, sticky="ns")
        self.file_listbox.config(yscrollcommand=scrollbar.set)
    
        self.add_btn = ttk.Button(self.main_frame, text="Add Files", command=self.add_files)
        self.add_btn.grid(row=2, column=0, pady=5, sticky="ew")
        
        self.clear_btn = ttk.Button(self.main_frame, text="Clear List", command=self.clear_files)
        self.clear_btn.grid(row=2, column=1, pady=5, sticky="ew")
        
        self.convert_btn = ttk.Button(self.main_frame, text="Convert to Text", command=self.convert_text)
        self.convert_btn.grid(row=3, column=0, columnspan=3, pady=5, sticky="ew")
        
        ttk.Label(self.main_frame, text="Text Preview:").grid(row=4, column=0, sticky="w")
        self.text_preview = tk.Text(self.main_frame, height=10, wrap=tk.WORD)
        self.text_preview.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=5)
        
        preview_scroll = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.text_preview.yview)
        preview_scroll.grid(row=5, column=3, sticky="ns")
        self.text_preview.config(yscrollcommand=preview_scroll.set)
        
        ttk.Label(self.main_frame, text="Speech Settings:").grid(row=6, column=0, sticky="w")
        
        self.rate_label = ttk.Label(self.main_frame, text="Speed:")
        self.rate_label.grid(row=7, column=0, sticky="w")
        self.rate_slider = ttk.Scale(self.main_frame, from_=100, to=300, value=150)
        self.rate_slider.grid(row=7, column=1, sticky="ew")
        
        self.volume_label = ttk.Label(self.main_frame, text="Volume:")
        self.volume_label.grid(row=8, column=0, sticky="w")
        self.volume_slider = ttk.Scale(self.main_frame, from_=0, to=1, value=0.9)
        self.volume_slider.grid(row=8, column=1, sticky="ew")
        
        self.preview_btn = ttk.Button(self.main_frame, text="Preview Speech", command=self.start_speaking)
        self.preview_btn.grid(row=9, column=0, pady=10, sticky="ew")
        
        self.export_btn = ttk.Button(self.main_frame, text="Export to MP3", command=self.export_to_mp3)
        self.export_btn.grid(row=9, column=1, pady=10, sticky="ew")
        
        self.stop_btn = ttk.Button(self.main_frame, text="Stop", command=self.stop_speech)
        self.stop_btn.grid(row=9, column=2, pady=10, sticky="ew")
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief="sunken")
        self.status_bar.grid(row=10, column=0, columnspan=3, sticky="ew", pady=10)
        
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(5, weight=2)
        self.main_frame.grid_columnconfigure(1, weight=1)
    
    def setup_tts_engine(self):
        self.engine = pyttsx3.init()
        self.is_speaking = False
        self.speech_thread = None
        self.text_queue = queue.Queue()
        
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)
    
    def setup_drag_and_drop(self):
        self.master.drop_target_register(DND_FILES)
        self.master.dnd_bind('<<Drop>>', self.handle_drop)
    
    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt")])
        if files:
            self.current_files.extend(files)
            self.update_file_list()
    
    def handle_drop(self, event):
        files = [f.strip("{}") for f in event.data.split()]
        valid_files = [f for f in files if f.lower().endswith(('.md', '.txt'))]
        
        if valid_files:
            self.current_files.extend(valid_files)
            self.update_file_list()
        else:
            messagebox.showerror("Error", "Only .md and .txt files are supported")
    
    def clear_files(self):
        self.current_files = []
        self.file_listbox.delete(0, tk.END)
        self.text_preview.delete(1.0, tk.END)
        self.status_var.set("File list cleared")
    
    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        for file in self.current_files:
            self.file_listbox.insert(tk.END, os.path.basename(file))
        self.status_var.set(f"{len(self.current_files)} files loaded")
    
    def convert_text(self):
        if not self.current_files:
            messagebox.showerror("Error", "No files selected")
            return
        
        try:
            combined_text = []
            for file in self.current_files:
                with open(file, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                md_content = self.preprocess_markdown(md_content)
                html = markdown.markdown(md_content)
                soup = BeautifulSoup(html, 'html.parser')
                
                for element in soup(['style', 'script']):
                    element.decompose()
                
                text = self.format_text_for_speech(soup.get_text())
                combined_text.append(text)
            
            self.current_text = "\n\n".join(combined_text)
            self.text_preview.delete(1.0, tk.END)
            self.text_preview.insert(tk.END, self.current_text)
            
            try:
                sample_text = self.current_text[:500]  
                self.language = detect(sample_text)[:2]
            except LangDetectException:
                self.language = 'en'  
            
            self.status_var.set(f"Converted {len(self.current_files)} files ({self.language.upper()})")
            
        except Exception as e:
            messagebox.showerror("Error", f"Conversion failed:\n{str(e)}")
    
    def preprocess_markdown(self, text):
        text = re.sub(r'```([a-z]*)\n(.*?)\n```', 
                     r'<pre><code>\2</code></pre>', 
                     text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        return text
    
    def format_text_for_speech(self, text):
        
        text = re.sub(r'(\d+)\.(\d+\b)', r'\1 точка \2', text)
        
        text = re.sub(r'^(#+)\s*(.+?)\s*$', 
                     lambda m: f"{m.group(2)} (уровень {len(m.group(1))})", 
                     text, flags=re.MULTILINE)
        
        text = re.sub(r'^\s*[\*\-+]\s+(.+?)$', r'• \1', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+(.+?)$', r'Номер \1', text, flags=re.MULTILINE)
        
        text = re.sub(r'<pre><code>(.*?)</code></pre>', 
                     r'[БЛОК КОДА: \1]', 
                     text, flags=re.DOTALL)
        text = re.sub(r'<code>(.*?)</code>', r'код: \1', text)
        
        text = re.sub(r'[ \t]+', ' ', text)  
        text = re.sub(r'\n\s+\n', '\n\n', text)  
        text = text.strip()
        
        return text
    
    def start_speaking(self):
        if not self.current_text:
            messagebox.showerror("Error", "No text to speak. Convert first.")
            return
        
        if self.is_speaking:
            messagebox.showwarning("Warning", "Already speaking")
            return
        
        try:
            rate = self.rate_slider.get()
            volume = self.volume_slider.get()
            
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if self.language in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            
            self.is_speaking = True
            self.text_queue.queue.clear()
            self.text_queue.put(self.current_text)
            
            self.speech_thread = threading.Thread(target=self.speak_with_intonation, daemon=True)
            self.speech_thread.start()
            
            self.status_var.set("Speaking...")
            self.preview_btn.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Speech failed:\n{str(e)}")
            self.is_speaking = False
    
    def speak_with_intonation(self):
        while self.is_speaking and not self.text_queue.empty():
            text = self.text_queue.get()
            
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            for para in paragraphs:
                if not self.is_speaking:
                    break
                
                if "уровень" in para:
                    self.engine.setProperty('volume', min(1.0, self.volume_slider.get() + 0.1))
                    self.engine.setProperty('rate', max(100, self.rate_slider.get() - 20))
                    self.engine.say(para)
                    self.engine.runAndWait()
                    self.engine.setProperty('volume', self.volume_slider.get())
                    self.engine.setProperty('rate', self.rate_slider.get())
                elif para.startswith(('•', 'Номер', '[БЛОК КОДА:')):
                    self.engine.say("<silence msec='300'/>" + para)
                    self.engine.runAndWait()
                else:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    for sentence in sentences:
                        if not self.is_speaking:
                            break
                        if sentence.strip():
                            self.engine.say(sentence)
                            self.engine.runAndWait()
        
        self.is_speaking = False
        self.master.after(0, self.speaking_completed)
    
    def speaking_completed(self):
        self.status_var.set("Speech completed")
        self.preview_btn.config(state=tk.NORMAL)
    
    def export_to_mp3(self):
        if not self.current_text:
            messagebox.showerror("Error", "No text to export. Convert first.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 Files", "*.mp3")],
            title="Save MP3 File"
        )
        
        if not file_path:
            return
        
        try:
            chunks = [self.current_text[i:i+4000] for i in range(0, len(self.current_text), 4000)]
            temp_files = []
            
            for i, chunk in enumerate(chunks):
                formatted_chunk = self.add_ssml_tags(chunk)
                
                tts = gTTS(text=formatted_chunk, lang=self.language, slow=False)
                temp_file = os.path.join(tempfile.gettempdir(), f"tts_temp_{i}.mp3")
                tts.save(temp_file)
                temp_files.append(temp_file)
            
            with open(file_path, 'wb') as out_file:
                for temp_file in temp_files:
                    with open(temp_file, 'rb') as f:
                        out_file.write(f.read())
                    os.remove(temp_file)
            
            self.status_var.set(f"Exported to {os.path.basename(file_path)}")
            messagebox.showinfo("Success", f"Audio saved to:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
    
    def add_ssml_tags(self, text):
        text = re.sub(r'(.*?)\s*\(уровень \d\)', r'<prosody rate="slow" volume="loud">\1</prosody>', text)
        text = re.sub(r'(•|Номер)(.+?)(?=\n|$)', r'<break time="300ms"/>\1\2', text)
        text = re.sub(r'\[БЛОК КОДА:(.+?)\]', r'<prosody rate="fast" pitch="low">Блок кода: \1</prosody>', text)
        return f"<speak>{text}</speak>"
    
    def stop_speech(self):
        if self.is_speaking:
            self.is_speaking = False
            self.engine.stop()
            self.status_var.set("Speech stopped")
            self.preview_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = MarkdownSpeaker(root)
    root.mainloop()

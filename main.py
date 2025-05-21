import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk


class BoundingBoxApp:
    def __init__(self, parent):
        self.parent = parent

        # Variables for image handling
        self.image_path = ""
        self.image = None
        self.tk_image = None
        self.canvas_image = None

        # Variables for bounding box drawing
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.bboxes = []

        # Main frames
        self.main_frame = tk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Image frame
        self.image_frame = tk.LabelFrame(self.main_frame, text="Изображение", padx=5, pady=5)
        self.image_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.image_frame, bg="gray", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Control frame
        self.control_frame = tk.LabelFrame(self.main_frame, text="Управление разметкой", padx=5, pady=5)
        self.control_frame.pack(fill=tk.X)

        # Control buttons
        tk.Button(self.control_frame, text="Загрузить изображение", command=self.load_image).pack(side=tk.LEFT, padx=5)
        tk.Button(self.control_frame, text="Добавить разметку", command=self.add_bbox).pack(side=tk.LEFT, padx=5)
        tk.Button(self.control_frame, text="Удалить последнюю", command=self.remove_last_bbox).pack(side=tk.LEFT,
                                                                                                    padx=5)
        tk.Button(self.control_frame, text="Очистить все", command=self.clear_bboxes).pack(side=tk.LEFT, padx=5)

        # Object description and bbox list
        self.bbox_list_frame = tk.LabelFrame(self.main_frame, text="Список разметки", padx=5, pady=5)
        self.bbox_list_frame.pack(fill=tk.X)

        tk.Label(self.bbox_list_frame, text="Описание:").pack(side=tk.LEFT, padx=5)
        self.obj_desc = tk.Entry(self.bbox_list_frame, width=20)
        self.obj_desc.pack(side=tk.LEFT, padx=5)

        self.bbox_list = tk.Listbox(self.bbox_list_frame, height=4)
        self.bbox_list.pack(fill=tk.X, expand=True, padx=5, pady=5)

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)

    def load_image(self, file_path=None):
        if not file_path:
            file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])

        if file_path:
            self.image_path = file_path
            self.image = Image.open(file_path)

            # Scale down large images
            max_size = (800, 600)
            if self.image.width > max_size[0] or self.image.height > max_size[1]:
                self.image.thumbnail(max_size, Image.Resampling.LANCZOS)

            self.tk_image = ImageTk.PhotoImage(self.image)

            # Clear canvas and display image
            self.canvas.delete("all")
            self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

            # Set canvas size to image size
            self.canvas.config(width=self.tk_image.width(), height=self.tk_image.height())

            # Clear existing bounding boxes
            self.clear_bboxes()

    def on_mouse_press(self, event):
        # Remove previous temporary rectangle
        if self.rect:
            self.canvas.delete(self.rect)

        self.start_x = event.x
        self.start_y = event.y

        # Create new rectangle
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline="red", width=2, tags="temp_rect"
        )

    def on_mouse_drag(self, event):
        # Update rectangle coordinates
        if self.rect:
            self.canvas.coords(
                self.rect,
                self.start_x, self.start_y,
                event.x, event.y
            )

    def on_mouse_release(self, event):
        if not self.rect:
            return

        # Check if rectangle is large enough
        if abs(event.x - self.start_x) < 5 or abs(event.y - self.start_y) < 5:
            self.canvas.delete(self.rect)
            self.rect = None
            return

    def add_bbox(self):
        if not self.rect:
            messagebox.showwarning("Предупреждение", "Сначала выделите область на изображении!")
            return

        description = self.obj_desc.get()
        if not description:
            messagebox.showwarning("Предупреждение", "Введите описание объекта!")
            return

        # Get rectangle coordinates
        coords = self.canvas.coords(self.rect)
        x1, y1, x2, y2 = coords

        # Add to list
        bbox_data = {
            "coords": (x1, y1, x2, y2),
            "description": description
        }
        self.bboxes.append(bbox_data)

        # Add to listbox
        self.bbox_list.insert(tk.END, f"{description}: ({int(x1)},{int(y1)})-({int(x2)},{int(y2)})")

        # Redraw permanent bounding boxes
        self.redraw_bboxes()

        # Remove temporary rectangle
        self.canvas.delete(self.rect)
        self.rect = None
        self.obj_desc.delete(0, tk.END)

    def remove_last_bbox(self):
        if self.bboxes:
            self.bboxes.pop()
            self.bbox_list.delete(self.bbox_list.size() - 1)
            self.redraw_bboxes()

    def clear_bboxes(self):
        self.bboxes = []
        self.bbox_list.delete(0, tk.END)
        self.canvas.delete("bbox")
        if self.rect:
            self.canvas.delete(self.rect)
            self.rect = None

    def redraw_bboxes(self):
        self.canvas.delete("bbox")
        for bbox in self.bboxes:
            x1, y1, x2, y2 = bbox["coords"]
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="red", width=2,
                tags="bbox"
            )


class JSONDatasetCreator:
    def __init__(self, root):
        self.root = root
        self.root.title("Создатель JSON датасета с визуальной разметкой")
        self.root.state('zoomed')  # Fullscreen mode

        self.entries = []
        self.current_id = 1
        self.current_conversation = []
        self.current_file = None
        self.editing_index = None

        # Main canvas with scrollbar
        self.main_canvas = tk.Canvas(root)
        self.scrollbar = tk.Scrollbar(root, command=self.main_canvas.yview)

        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.main_frame = tk.Frame(self.main_canvas)
        self.main_canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        # Configure scroll region
        self.main_frame.bind("<Configure>",
                             lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all")))

        # Mouse wheel scrolling
        self.main_canvas.bind_all("<MouseWheel>",
                                  lambda e: self.main_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # Menu
        self.menu_bar = tk.Menu(root)

        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Открыть JSON", command=self.load_json)
        self.file_menu.add_command(label="Сохранить", command=self.save_to_json)
        self.file_menu.add_command(label="Сохранить как...", command=self.save_as_json)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Выход", command=root.quit)
        self.menu_bar.add_cascade(label="Файл", menu=self.file_menu)

        root.config(menu=self.menu_bar)

        # Image annotation frame
        self.bbox_frame = tk.LabelFrame(self.main_frame, text="Разметка изображений", padx=5, pady=5)
        self.bbox_frame.pack(fill=tk.BOTH, expand=True)

        # Create annotation app instance
        self.bbox_app = BoundingBoxApp(self.bbox_frame)

        # Bind mouse events for annotation canvas
        self.bbox_app.canvas.bind("<ButtonPress-1>", self.bbox_app.on_mouse_press)
        self.bbox_app.canvas.bind("<B1-Motion>", self.bbox_app.on_mouse_drag)
        self.bbox_app.canvas.bind("<ButtonRelease-1>", self.bbox_app.on_mouse_release)

        # Conversation control frame
        self.conversation_frame = tk.LabelFrame(self.main_frame, text="Управление беседой", padx=5, pady=5)
        self.conversation_frame.pack(fill=tk.X)

        # Configure grid
        self.conversation_frame.grid_columnconfigure(1, weight=1)
        self.conversation_frame.grid_columnconfigure(2, weight=1)

        # Entry ID
        tk.Label(self.conversation_frame, text="ID записи:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.id_entry = tk.Entry(self.conversation_frame, width=20)
        self.id_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.id_entry.insert(0, "identity_1")

        # Image path
        tk.Label(self.conversation_frame, text="URL/путь к изображению:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.image_path_entry = tk.Entry(self.conversation_frame)
        self.image_path_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=5)

        self.browse_btn = tk.Button(self.conversation_frame, text="Обзор", command=self.browse_image)
        self.browse_btn.grid(row=1, column=3, padx=5)

        # Question
        tk.Label(self.conversation_frame, text="Текст вопроса:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.question_entry = tk.Entry(self.conversation_frame)
        self.question_entry.grid(row=2, column=1, columnspan=3, sticky=tk.EW, padx=5)

        # Answer
        tk.Label(self.conversation_frame, text="Текст ответа:").grid(row=3, column=0, sticky=tk.W, padx=5)
        self.answer_entry = tk.Entry(self.conversation_frame)
        self.answer_entry.grid(row=3, column=1, columnspan=3, sticky=tk.EW, padx=5)

        # Buttons
        self.add_qa_btn = tk.Button(self.conversation_frame, text="Добавить вопрос-ответ", command=self.add_qa)
        self.add_qa_btn.grid(row=4, column=1, pady=5, sticky=tk.EW, padx=5)

        self.add_bbox_btn = tk.Button(self.conversation_frame, text="Добавить разметку",
                                      command=self.add_bbox_from_selection)
        self.add_bbox_btn.grid(row=4, column=2, pady=5, sticky=tk.EW, padx=5)

        self.finish_entry_btn = tk.Button(self.conversation_frame, text="Завершить запись", command=self.finish_entry)
        self.finish_entry_btn.grid(row=4, column=3, pady=5, sticky=tk.EW, padx=5)

        # Messages frame with edit controls
        self.messages_frame = tk.LabelFrame(self.main_frame, text="Текущая беседа (двойной клик для удаления)", padx=5,
                                            pady=5)
        self.messages_frame.pack(fill=tk.BOTH, expand=True)

        self.messages_text = tk.Text(self.messages_frame, wrap=tk.WORD)
        scrollbar = tk.Scrollbar(self.messages_frame, command=self.messages_text.yview)
        self.messages_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.messages_text.pack(fill=tk.BOTH, expand=True)

        # Bind double click to delete message
        self.messages_text.bind("<Double-Button-1>", self.delete_selected_message)

        # Entries list frame
        self.entries_frame = tk.LabelFrame(self.main_frame, text="Добавленные записи", padx=5, pady=5)
        self.entries_frame.pack(fill=tk.BOTH, expand=True)

        self.entries_listbox = tk.Listbox(self.entries_frame)
        scrollbar = tk.Scrollbar(self.entries_frame, command=self.entries_listbox.yview)
        self.entries_listbox.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.entries_listbox.pack(fill=tk.BOTH, expand=True)

        # Bind double click to edit entry
        self.entries_listbox.bind("<Double-Button-1>", self.edit_selected_entry)

        # Edit/Delete buttons
        self.edit_frame = tk.Frame(self.entries_frame)
        self.edit_frame.pack(fill=tk.X)

        self.edit_btn = tk.Button(self.edit_frame, text="Редактировать", command=self.edit_selected_entry)
        self.edit_btn.pack(side=tk.LEFT, padx=5)

        self.delete_btn = tk.Button(self.edit_frame, text="Удалить", command=self.delete_selected_entry)
        self.delete_btn.pack(side=tk.LEFT, padx=5)

        # Save/clear buttons
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=5)

        self.save_btn = tk.Button(self.button_frame, text="Сохранить", command=self.save_to_json)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.save_as_btn = tk.Button(self.button_frame, text="Сохранить как...", command=self.save_as_json)
        self.save_as_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = tk.Button(self.button_frame, text="Очистить все", command=self.clear_all)
        self.clear_btn.pack(side=tk.RIGHT, padx=5)

    def load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.entries = json.load(f)
                self.current_file = file_path

                # Update entries list
                self.update_entries_list()

                # Find max ID to continue numbering
                max_id = 0
                for entry in self.entries:
                    if entry['id'].startswith("identity_"):
                        try:
                            current_id = int(entry['id'].split("_")[1])
                            if current_id > max_id:
                                max_id = current_id
                        except:
                            pass

                self.current_id = max_id + 1
                self.id_entry.delete(0, tk.END)
                self.id_entry.insert(0, f"identity_{self.current_id}")

                messagebox.showinfo("Успех", f"Файл успешно загружен! Текущий ID: {self.current_id}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{str(e)}")

    def save_to_json(self):
        if not self.entries:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения!")
            return

        if self.current_file:
            file_path = self.current_file
        else:
            file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                     filetypes=[("JSON files", "*.json")])
            if not file_path:
                return
            self.current_file = file_path

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Успех", "Файл успешно сохранен!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{str(e)}")

    def save_as_json(self):
        if not self.entries:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения!")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                 filetypes=[("JSON files", "*.json")])
        if file_path:
            self.current_file = file_path
            self.save_to_json()

    def browse_image(self):
        filename = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if filename:
            self.image_path_entry.delete(0, tk.END)
            self.image_path_entry.insert(0, filename)
            self.bbox_app.load_image(filename)

    def add_qa(self):
        question = self.question_entry.get()
        answer = self.answer_entry.get()
        image_path = self.image_path_entry.get()

        if not all([question, answer, image_path]):
            messagebox.showwarning("Предупреждение", "Все поля должны быть заполнены!")
            return

        # Format question with image
        if image_path.startswith(("http://", "https://")):
            image_ref = image_path
        else:
            image_ref = os.path.basename(image_path)

        user_msg = f"Picture {self.current_id}: <img>{image_ref}</img>\n{question}"

        # Add to conversation
        self.current_conversation.append({"from": "user", "value": user_msg})
        self.current_conversation.append({"from": "assistant", "value": answer})

        # Update messages
        self.update_conversation_display()

        # Clear fields
        self.question_entry.delete(0, tk.END)
        self.answer_entry.delete(0, tk.END)

    def add_bbox_from_selection(self):
        if not self.bbox_app.bboxes:
            messagebox.showwarning("Предупреждение", "Сначала выделите объекты на изображении!")
            return

        for bbox in self.bbox_app.bboxes:
            x1, y1, x2, y2 = bbox["coords"]
            description = bbox["description"]

            # Format bbox message
            bbox_msg = f"<ref>{description}</ref><box>({int(x1)},{int(y1)}),({int(x2)},{int(y2)})</box>"

            # Add to conversation
            self.current_conversation.append({"from": "user", "value": f"Отметьте {description}"})
            self.current_conversation.append({"from": "assistant", "value": bbox_msg})

        # Update messages
        self.update_conversation_display()

        # Clear bboxes
        self.bbox_app.clear_bboxes()

    def update_conversation_display(self):
        """Update the conversation display with current messages"""
        self.messages_text.delete(1.0, tk.END)
        for msg in self.current_conversation:
            self.messages_text.insert(tk.END, f"{msg['from']}: {msg['value']}\n")
        self.messages_text.see(tk.END)

    def delete_selected_message(self, event=None):
        """Delete selected message from conversation"""
        if not self.current_conversation:
            return

        # Get selected line
        line = self.messages_text.index("insert").split('.')[0]
        try:
            line_num = int(line) - 1
            if 0 <= line_num < len(self.current_conversation):
                self.current_conversation.pop(line_num)
                self.update_conversation_display()
        except:
            pass

    def finish_entry(self):
        if not self.current_conversation:
            messagebox.showwarning("Предупреждение", "Нет сообщений для сохранения!")
            return

        entry_id = self.id_entry.get()
        if not entry_id:
            messagebox.showwarning("Предупреждение", "ID записи не может быть пустым!")
            return

        entry = {
            "id": entry_id,
            "conversations": self.current_conversation.copy()
        }

        if self.editing_index is not None:
            # Update existing entry
            self.entries[self.editing_index] = entry
            self.editing_index = None
        else:
            # Add new entry
            self.entries.append(entry)
            # Increment ID only for new entries
            self.current_id += 1

        # Update entries list
        self.update_entries_list()

        # Reset current conversation
        self.reset_conversation()

    def reset_conversation(self):
        """Reset conversation to initial state"""
        self.current_conversation = []
        self.messages_text.delete(1.0, tk.END)
        self.id_entry.delete(0, tk.END)
        self.id_entry.insert(0, f"identity_{self.current_id}")
        self.image_path_entry.delete(0, tk.END)
        self.question_entry.delete(0, tk.END)
        self.answer_entry.delete(0, tk.END)
        self.bbox_app.clear_bboxes()

    def update_entries_list(self):
        """Update the entries listbox with current entries"""
        self.entries_listbox.delete(0, tk.END)
        for entry in self.entries:
            self.entries_listbox.insert(tk.END, f"{entry['id']} ({len(entry['conversations'])} сообщений)")

    def edit_selected_entry(self, event=None):
        """Load selected entry for editing"""
        selection = self.entries_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите запись для редактирования!")
            return

        index = selection[0]
        entry = self.entries[index]

        # Set editing mode
        self.editing_index = index
        self.current_conversation = [msg.copy() for msg in entry['conversations']]  # Deep copy

        # Update UI
        self.id_entry.delete(0, tk.END)
        self.id_entry.insert(0, entry['id'])

        # Find image path from conversations
        image_path = ""
        for msg in entry['conversations']:
            if msg['from'] == 'user' and '<img>' in msg['value']:
                img_tag = msg['value'].split('<img>')[1].split('</img>')[0]
                if img_tag.startswith(('http://', 'https://')):
                    image_path = img_tag
                else:
                    # Try to find local file
                    if os.path.exists(img_tag):
                        image_path = img_tag
                break

        self.image_path_entry.delete(0, tk.END)
        self.image_path_entry.insert(0, image_path)

        # Load image if exists
        if image_path and os.path.exists(image_path):
            self.bbox_app.load_image(image_path)

        # Display conversation
        self.update_conversation_display()

        messagebox.showinfo("Редактирование",
                            "Запись загружена для редактирования. Можно удалять сообщения двойным кликом, добавлять новые или изменять существующие.")

    def delete_selected_entry(self):
        """Delete selected entry from dataset"""
        selection = self.entries_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите запись для удаления!")
            return

        if messagebox.askyesno("Подтверждение", "Вы действительно хотите удалить выбранную запись?"):
            index = selection[0]
            self.entries.pop(index)
            self.update_entries_list()

            # If we were editing this entry, cancel editing
            if self.editing_index == index:
                self.editing_index = None
                self.reset_conversation()
            elif self.editing_index is not None and self.editing_index > index:
                self.editing_index -= 1

    def clear_all(self):
        """Clear all data"""
        if messagebox.askyesno("Подтверждение", "Вы действительно хотите очистить все данные?"):
            self.entries = []
            self.current_conversation = []
            self.entries_listbox.delete(0, tk.END)
            self.messages_text.delete(1.0, tk.END)
            self.current_id = 1
            self.id_entry.delete(0, tk.END)
            self.id_entry.insert(0, f"identity_{self.current_id}")
            self.image_path_entry.delete(0, tk.END)
            self.question_entry.delete(0, tk.END)
            self.answer_entry.delete(0, tk.END)
            self.bbox_app.clear_bboxes()
            self.current_file = None
            self.editing_index = None


if __name__ == "__main__":
    root = tk.Tk()
    app = JSONDatasetCreator(root)
    root.mainloop()
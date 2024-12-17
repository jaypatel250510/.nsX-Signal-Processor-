import sys
import os
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QLineEdit, QFileDialog, QWidget, QInputDialog
)
from pyqtgraph import PlotWidget, InfiniteLine, RectROI, TextItem
from pyqtgraph.exporters import ImageExporter
from neo.io import BlackrockIO


class RippleSoftware(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()

        
        self.file_label = QLabel("No file selected.")
        self.upload_button = QPushButton("Upload .nsX File")
        self.upload_button.clicked.connect(self.upload_file)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.upload_button)
        file_layout.addWidget(self.file_label)
        self.layout.addLayout(file_layout)

        
        self.time_label = QLabel("Total recording time: N/A")
        self.calculate_button = QPushButton("Calculate Total Time")
        self.calculate_button.clicked.connect(self.calculate_total_time)

        time_layout = QHBoxLayout()
        time_layout.addWidget(self.calculate_button)
        time_layout.addWidget(self.time_label)
        self.layout.addLayout(time_layout)

        
        self.start_time_input = QLineEdit()
        self.start_time_input.setPlaceholderText("Start Time (e.g., 3110)")
        self.end_time_input = QLineEdit()
        self.end_time_input.setPlaceholderText("End Time (e.g., 3120)")

        time_range_layout = QHBoxLayout()
        time_range_layout.addWidget(QLabel("Specify Time Range:"))
        time_range_layout.addWidget(self.start_time_input)
        time_range_layout.addWidget(self.end_time_input)
        self.layout.addLayout(time_range_layout)

        
        self.x_axis_label = QLabel("X-Axis Scaling:")
        self.x_axis_dropdown = QComboBox()
        self.x_axis_dropdown.addItems(
            ["Auto", "Full Range", "1 Second", "0.1 Seconds", "0.01 Seconds", "0.001 Seconds", "0.0001 Seconds", "Custom Range"]
        )
        self.x_axis_dropdown.currentIndexChanged.connect(self.handle_x_axis_selection)

        
        self.y_axis_label = QLabel("Y-Axis Scaling:")
        self.y_axis_dropdown = QComboBox()
        self.y_axis_dropdown.addItems(["Auto", "±10 µV", "±50 µV", "Custom Range"])
        self.y_axis_dropdown.currentIndexChanged.connect(self.handle_y_axis_selection)

        
        self.x_start_scale = QLineEdit()
        self.x_start_scale.setPlaceholderText("X Start")
        self.x_start_scale.setVisible(False)

        self.x_end_scale = QLineEdit()
        self.x_end_scale.setPlaceholderText("X End")
        self.x_end_scale.setVisible(False)

        self.y_min_input = QLineEdit()
        self.y_min_input.setPlaceholderText("Y Min")
        self.y_min_input.setVisible(False)

        self.y_max_input = QLineEdit()
        self.y_max_input.setPlaceholderText("Y Max")
        self.y_max_input.setVisible(False)

        scaling_layout = QHBoxLayout()
        scaling_layout.addWidget(self.x_axis_label)
        scaling_layout.addWidget(self.x_axis_dropdown)
        scaling_layout.addWidget(self.x_start_scale)
        scaling_layout.addWidget(self.x_end_scale)

        scaling_layout.addWidget(self.y_axis_label)
        scaling_layout.addWidget(self.y_axis_dropdown)
        scaling_layout.addWidget(self.y_min_input)
        scaling_layout.addWidget(self.y_max_input)
        self.layout.addLayout(scaling_layout)

        
        self.graph_widget = PlotWidget()
        self.graph_widget.setLabel('left', 'Voltage (µV)')  
        self.graph_widget.setLabel('bottom', 'Time (s)')  
        self.layout.addWidget(self.graph_widget)

        
        self.vline = InfiniteLine(angle=90, movable=False, pen="g")  
        self.hline = InfiniteLine(angle=0, movable=False, pen="g")   
        self.graph_widget.addItem(self.vline, ignoreBounds=True)
        self.graph_widget.addItem(self.hline, ignoreBounds=True)

        
        self.cursor_label = QLabel("Cursor: X= N/A, Y= N/A")
        self.layout.addWidget(self.cursor_label)

        
        self.graph_widget.scene().sigMouseMoved.connect(self.update_cursor)

        
        self.add_note_button = QPushButton("Add Note")
        self.add_note_button.clicked.connect(self.activate_add_note_mode)
        self.layout.addWidget(self.add_note_button)

    
        self.measure_height_button = QPushButton("Measure Height")
        self.measure_height_button.clicked.connect(self.activate_measure_height_mode)
        self.height_label = QLabel("Height: N/A")
        self.layout.addWidget(self.measure_height_button)
        self.layout.addWidget(self.height_label)

        self.measure_width_button = QPushButton("Measure Width")
        self.measure_width_button.clicked.connect(self.activate_measure_width_mode)
        self.width_label = QLabel("Width: N/A")
        self.layout.addWidget(self.measure_width_button)
        self.layout.addWidget(self.width_label)

        
        self.add_roi_button = QPushButton("Add ROI")
        self.add_roi_button.clicked.connect(self.add_roi)
        self.reset_zoom_button = QPushButton("Reset Zoom")
        self.reset_zoom_button.clicked.connect(self.reset_zoom)

        roi_layout = QHBoxLayout()
        roi_layout.addWidget(self.add_roi_button)
        roi_layout.addWidget(self.reset_zoom_button)
        self.layout.addLayout(roi_layout)

        
        self.graph_button = QPushButton("Show Graph")
        self.graph_button.clicked.connect(self.plot_graph)
        self.export_button = QPushButton("Export Graph")
        self.export_button.clicked.connect(self.export_graph)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.graph_button)
        button_layout.addWidget(self.export_button)
        self.layout.addLayout(button_layout)

        
        self.setLayout(self.layout)
        self.setWindowTitle("Ripple Graphing Software")

        
        self.file_path = None
        self.sampling_rate = None
        self.total_samples = None
        self.roi = None
        self.add_note_mode = False
        self.notes = []

    def activate_add_note_mode(self):
        self.add_note_mode = True
        self.graph_widget.scene().sigMouseClicked.connect(self.add_note)

    def add_note(self, event):
        if not self.add_note_mode:
            return

        pos = self.graph_widget.plotItem.vb.mapSceneToView(event.scenePos())
        x = pos.x()
        y = pos.y()

        note_text, ok = QInputDialog.getText(self, "Add Note", f"Enter note for X={x:.3f}, Y={y:.3f}:")
        if ok and note_text:
            
            text_item = TextItem(text=note_text, anchor=(0.5, 0.5))
            text_item.setPos(x, y)
            self.graph_widget.addItem(text_item)

            
            if self.file_path:
                base_name = os.path.splitext(os.path.basename(self.file_path))[0]
                note_filename = f"{base_name}_x_{x:.3f}_y_{y:.3f}.txt"
                save_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Save Note")
                if save_dir:
                    file_path = os.path.join(save_dir, note_filename)
                    with open(file_path, "w") as note_file:
                        note_file.write(f"Note for X={x:.3f}, Y={y:.3f}:\n")
                        note_file.write(note_text)
                    print(f"Note saved as {file_path}")

        self.add_note_mode = False
        self.graph_widget.scene().sigMouseClicked.disconnect(self.add_note)

    def activate_measure_height_mode(self):
        self.measure_mode = "height"
        self.line1 = None
        self.line2 = None
        self.temp_line = InfiniteLine(angle=0, movable=False, pen="r")
        self.graph_widget.addItem(self.temp_line)
        self.height_label.setText("Height: N/A µV")
        self.graph_widget.scene().sigMouseClicked.connect(self.place_measure_lines)
        self.graph_widget.scene().sigMouseMoved.connect(self.update_temp_line)

    def activate_measure_width_mode(self):
        self.measure_mode = "width"
        self.line1 = None
        self.line2 = None
        self.temp_line = InfiniteLine(angle=90, movable=False, pen="r")
        self.graph_widget.addItem(self.temp_line)
        self.width_label.setText("Width: N/A secs")
        self.graph_widget.scene().sigMouseClicked.connect(self.place_measure_lines)
        self.graph_widget.scene().sigMouseMoved.connect(self.update_temp_line)

    def update_temp_line(self, pos):
        if self.graph_widget.sceneBoundingRect().contains(pos):
            point = self.graph_widget.plotItem.vb.mapSceneToView(pos)
            if self.temp_line is not None:
                if self.measure_mode == "height":
                    self.temp_line.setPos(point.y())
                elif self.measure_mode == "width":
                    self.temp_line.setPos(point.x())

    def place_measure_lines(self, event):
        pos = self.graph_widget.plotItem.vb.mapSceneToView(event.scenePos())
        if self.measure_mode == "height":
            y = pos.y()
            x = pos.x()
            if self.line1 is None:
                
                self.line1 = InfiniteLine(angle=0, movable=False, pen="r")
                self.line1.setPos(y)
                self.graph_widget.addItem(self.line1)
            elif self.line2 is None:
                
                self.line2 = InfiniteLine(angle=0, movable=False, pen="r")
                self.line2.setPos(y)
                self.graph_widget.addItem(self.line2)
                height = abs(self.line2.pos().y() - self.line1.pos().y())
                self.height_label.setText(f"Height: {height:.3f} µV")
                
                
                self.height_text = TextItem(f"{height:.3f} µV", anchor=(0.5, 1.0))
                self.height_text.setPos(x, self.line2.pos().y())
                self.graph_widget.addItem(self.height_text)
            else:
                
                self.reset_measurement()

        elif self.measure_mode == "width":
            x = pos.x()
            y = pos.y()
            if self.line1 is None:
                
                self.line1 = InfiniteLine(angle=90, movable=False, pen="r")
                self.line1.setPos(x)
                self.graph_widget.addItem(self.line1)
            elif self.line2 is None:
                
                self.line2 = InfiniteLine(angle=90, movable=False, pen="r")
                self.line2.setPos(x)
                self.graph_widget.addItem(self.line2)
                width = abs(self.line2.pos().x() - self.line1.pos().x())
                self.width_label.setText(f"Width: {width:.3f} seconds")
                
                
                self.width_text = TextItem(f"{width:.3f} s", anchor=(1.0, 0.5))
                self.width_text.setPos(self.line2.pos().x(), y)
                self.graph_widget.addItem(self.width_text)
            else:
                
                self.reset_measurement()

    def clear_temp_line(self):
        if self.temp_line:
            self.graph_widget.removeItem(self.temp_line)
            self.temp_line = None
            self.graph_widget.scene().sigMouseMoved.disconnect(self.update_temp_line)

    def reset_measurement(self):
        self.graph_widget.scene().sigMouseClicked.disconnect(self.place_measure_lines)
        if self.line1:
            self.graph_widget.removeItem(self.line1)
        if self.line2:
            self.graph_widget.removeItem(self.line2)
        if self.temp_line:
            self.graph_widget.removeItem(self.temp_line)
            self.temp_line = None
            self.graph_widget.scene().sigMouseMoved.disconnect(self.update_temp_line)
        if hasattr(self, 'height_text'):
            self.graph_widget.removeItem(self.height_text)
            self.height_text = None
        if hasattr(self, 'width_text'):
            self.graph_widget.removeItem(self.width_text)
            self.width_text = None
        self.line1 = None
        self.line2 = None
        self.measure_mode = False

    def upload_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Upload .nsX File", "", "NSX Files (*.ns*)", options=options)
        if file_name:
            self.file_path = file_name
            self.file_label.setText(f"File: {file_name}")

    def calculate_total_time(self):
        if not self.file_path:
            self.time_label.setText("Please upload a file first.")
            return

        reader = BlackrockIO(filename=self.file_path)
        seg = reader.read_segment()
        analog_signals = seg.analogsignals
        signal = analog_signals[0]
        self.sampling_rate = signal.sampling_rate.magnitude
        self.total_samples = len(signal)

        total_time = self.total_samples / self.sampling_rate
        self.time_label.setText(f"Total recording time: {total_time:.2f} seconds")

    def handle_x_axis_selection(self):
        if self.x_axis_dropdown.currentText() == "Custom Range":
            self.x_start_scale.setVisible(True)
            self.x_end_scale.setVisible(True)
        else:
            self.x_start_scale.setVisible(False)
            self.x_end_scale.setVisible(False)

    def handle_y_axis_selection(self):
        if self.y_axis_dropdown.currentText() == "Custom Range":
            self.y_min_input.setVisible(True)
            self.y_max_input.setVisible(True)
        else:
            self.y_min_input.setVisible(False)
            self.y_max_input.setVisible(False)

    def update_cursor(self, pos):
        if self.graph_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.graph_widget.plotItem.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            self.vline.setPos(x)
            self.hline.setPos(y)
            self.cursor_label.setText(f"Cursor: X= {x:.3f}, Y= {y:.3f}")

    def add_roi(self):
        if self.roi is None:
            self.roi = RectROI([0, 0], [1, 1], pen='r')
            self.graph_widget.addItem(self.roi)
            self.roi.sigRegionChanged.connect(self.zoom_to_roi)
        else:
            self.roi.setVisible(True)

    def zoom_to_roi(self):
        if self.roi:
            bounds = self.roi.getArraySlice(self.graph_widget.plotItem.curves[0].getData(), self.graph_widget.plotItem)
            x_range, y_range = bounds[0], bounds[1]
            self.graph_widget.setXRange(x_range[0], x_range[1])
            self.graph_widget.setYRange(y_range[0], y_range[1])

    def reset_zoom(self):
        self.graph_widget.getViewBox().autoRange()
        if self.roi:
            self.roi.setVisible(False)

    def plot_graph(self):
        if not self.file_path:
            self.time_label.setText("Please upload a file first.")
            return

        try:
            start_time = float(self.start_time_input.text())
            end_time = float(self.end_time_input.text())
        except ValueError:
            self.time_label.setText("Invalid time range.")
            return

        if start_time < 0 or end_time <= start_time:
            self.time_label.setText("Invalid time range.")
            return

        start_sample = int(start_time * self.sampling_rate)
        end_sample = int(end_time * self.sampling_rate)

        reader = BlackrockIO(filename=self.file_path)
        seg = reader.read_segment()
        analog_signals = seg.analogsignals
        signal = analog_signals[0]
        voltage = np.array(signal[start_sample:end_sample]).flatten()
        time = np.linspace(start_time, end_time, len(voltage))

        self.graph_widget.clear()
        self.graph_widget.plot(time, voltage, pen="y")

        
        x_range = None
        if self.x_axis_dropdown.currentText() == "1 Second":
            x_range = [start_time, start_time + 1]
        elif self.x_axis_dropdown.currentText() == "0.1 Seconds":
            x_range = [start_time, start_time + 0.1]
        elif self.x_axis_dropdown.currentText() == "0.01 Seconds":
            x_range = [start_time, start_time + 0.01]
        elif self.x_axis_dropdown.currentText() == "0.001 Seconds":
            x_range = [start_time, start_time + 0.001]
        elif self.x_axis_dropdown.currentText() == "0.0001 Seconds":
            x_range = [start_time, start_time + 0.0001]
        elif self.x_axis_dropdown.currentText() == "Custom Range":
            try:
                x_start = float(self.x_start_scale.text())
                x_end = float(self.x_end_scale.text())
                x_range = [x_start, x_end]
            except ValueError:
                x_range = None

        
        y_range = None
        if self.y_axis_dropdown.currentText() == "±10 µV":
            y_range = [-10, 10]
        elif self.y_axis_dropdown.currentText() == "±50 µV":
            y_range = [-50, 50]
        elif self.y_axis_dropdown.currentText() == "Custom Range":
            try:
                y_min = float(self.y_min_input.text())
                y_max = float(self.y_max_input.text())
                y_range = [y_min, y_max]
            except ValueError:
                y_range = None

        
        if x_range:
            self.graph_widget.setXRange(x_range[0], x_range[1])
        if y_range:
            self.graph_widget.setYRange(y_range[0], y_range[1])

    def export_graph(self):
        if self.graph_widget:
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Graph As", "", "PNG Files (*.png)")
            if save_path:
                exporter = ImageExporter(self.graph_widget.plotItem)
                exporter.parameters()['width'] = 1920
                exporter.export(save_path)
                print(f"Graph exported to {save_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = RippleSoftware()
    viewer.show()
    sys.exit(app.exec_())

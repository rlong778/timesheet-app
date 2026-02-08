"""
PDF Generator for Georgia Tech ENGAGES Timesheet
Fills the actual template with fillable form fields
"""

from pypdf import PdfReader, PdfWriter
import os

class TimesheetPDFGenerator:
    """Fills the actual ENGAGES template PDF with student data"""
    
    def __init__(self, template_path="Updated_Weekly_Timesheet__2_.pdf"):
        """
        Initialize with path to the template PDF
        
        Args:
            template_path: Path to the blank ENGAGES timesheet template
        """
        self.template_path = template_path
    
    def create_timesheet(self, data, output_path):
        """
        Fill the template PDF with student data
        
        Args:
            data: Dictionary containing:
                - student_name: str
                - gt_id: str
                - week_start: str (date of Monday)
                - daily_entries: list of dicts with day, date, time_in, time_out, mentor_initials
                - weekly_summary: str (AI-generated summary)
            output_path: Where to save the filled PDF
        """
        
        # Check if template exists
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(
                f"Template PDF not found at: {self.template_path}\n"
                f"Please place 'Updated_Weekly_Timesheet__2_.pdf' in the same directory as this script."
            )
        
        # Read the template
        reader = PdfReader(self.template_path)
        writer = PdfWriter()
        
        # Get the first page
        writer.append(reader)
        
        # Create field values dictionary
        field_values = {}
        
        # Fill student info
        field_values["Student Name"] = data['student_name']
        field_values["GT ID"] = data['gt_id']
        
        # Map day entries to the 5 rows (PDF only has 5 rows)
        # We'll fill Monday-Friday
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        # Create a mapping of days to entries
        # Handle both "Monday" and "Monday, January 5" formats
        entry_map = {}
        for entry in data.get('daily_entries', []):
            day_text = entry['day']
            # Extract just the day name (before the comma if present)
            day_name = day_text.split(',')[0].strip() if ',' in day_text else day_text
            entry_map[day_name] = entry
        
        # Fill the 5 rows
        for i, day_name in enumerate(days_of_week, 1):
            row_num = i
            
            if day_name in entry_map:
                entry = entry_map[day_name]
                # Use the full day format from the entry (e.g., "Monday, January 5")
                field_values[f"DayRow{row_num}"] = entry['day']
                field_values[f"Time InRow{row_num}"] = entry.get('time_in', '')
                field_values[f"Time OutRow{row_num}"] = entry.get('time_out', '')
                field_values[f"Mentor InitialsRow{row_num}"] = entry.get('mentor_initials', '')
            else:
                # Leave blank if no data for this day
                field_values[f"DayRow{row_num}"] = day_name
                field_values[f"Time InRow{row_num}"] = ''
                field_values[f"Time OutRow{row_num}"] = ''
                field_values[f"Mentor InitialsRow{row_num}"] = ''
        
        # Fill the weekly summary in the signature field (closest we have)
        # Note: The template doesn't have a separate field for the weekly report text
        # We'll need to add it as an annotation
        summary = data.get('weekly_summary', '')
        
        # Update the form fields
        writer.update_page_form_field_values(
            writer.pages[0], 
            field_values
        )
        
        # Add the weekly summary as a text annotation overlay
        # (since there's no form field for it)
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        # Create overlay for weekly summary
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFont("Helvetica", 9)
        
        # Position for weekly summary (approximate - below the table)
        summary_x = 80
        summary_y = 250
        max_width = 450
        
        # Draw wrapped text
        self._draw_wrapped_text(can, summary, summary_x, summary_y, max_width)
        
        can.save()
        
        # Merge the overlay with the filled form
        packet.seek(0)
        overlay_reader = PdfReader(packet)
        
        # Merge overlay onto the first page
        page = writer.pages[0]
        page.merge_page(overlay_reader.pages[0])
        
        # Write the final PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
    
    def _draw_wrapped_text(self, canvas_obj, text, x, y, max_width):
        """Draw text with word wrapping"""
        from reportlab.pdfbase.pdfmetrics import stringWidth
        
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            width = stringWidth(test_line, "Helvetica", 9)
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw each line
        line_height = 11
        current_y = y
        
        # Limit to ~10 lines to fit in the box
        for i, line in enumerate(lines):
            if i >= 10:
                break
            canvas_obj.drawString(x, current_y, line)
            current_y -= line_height


class EnhancedTimesheetGenerator:
    """
    Fallback generator if template is not available
    Creates a complete timesheet from scratch
    """
    
    def create_complete_timesheet(self, data, output_path):
        """Create a complete timesheet PDF matching the template"""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, height - 60, "Project ENGAGES Timesheet")
        
        # Student info
        c.setFont("Helvetica", 11)
        y_pos = height - 95
        c.drawString(72, y_pos, "Student Name: ")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(165, y_pos, data['student_name'])
        
        c.setFont("Helvetica", 11)
        y_pos -= 20
        c.drawString(72, y_pos, "GT ID#: ")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(120, y_pos, data['gt_id'])
        
        # Mentor signature line
        c.setFont("Helvetica", 10)
        y_pos -= 25
        c.drawString(72, y_pos, "Mentor's Signature: __________________________________________________________")
        
        # Instructions
        c.setFont("Helvetica", 9)
        y_pos -= 20
        instructions = [
            "Your mentor must sign and approve your work hours each week. Turn the completed",
            "timesheet into Dr. Glenn on Friday afternoon. You are responsible for your timesheet.",
            "Timesheets can be turned in electronically by taking a picture and emailing to Dr.",
            "Glenn, michael.glenn@ibb.gatech.edu or you may leave in yellow basket outside his",
            "office door, IBB 3319."
        ]
        for line in instructions:
            c.drawString(72, y_pos, line)
            y_pos -= 12
        
        # Table
        y_pos -= 25
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, y_pos, "Day")
        c.drawString(250, y_pos, "Time In")
        c.drawString(350, y_pos, "Time Out")
        c.drawString(470, y_pos, "Mentor Initials")
        
        y_pos -= 3
        c.setLineWidth(1)
        c.line(72, y_pos, 570, y_pos)
        
        # Table rows - only 5 rows (Monday-Friday)
        c.setFont("Helvetica", 10)
        y_pos -= 20
        row_height = 22
        
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        entry_map = {}
        for entry in data.get('daily_entries', []):
            entry_map[entry['day']] = entry
        
        for day_name in days_of_week:
            c.drawString(72, y_pos, day_name)
            
            if day_name in entry_map:
                entry = entry_map[day_name]
                c.drawString(250, y_pos, entry.get('time_in', ''))
                c.drawString(350, y_pos, entry.get('time_out', ''))
                c.drawString(470, y_pos, entry.get('mentor_initials', ''))
            
            y_pos -= 3
            c.setLineWidth(0.5)
            c.line(72, y_pos, 570, y_pos)
            y_pos -= (row_height - 3)
        
        # Weekly report
        y_pos -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(72, y_pos, "Weekly Report:")
        
        c.setFont("Helvetica", 9)
        y_pos -= 15
        report_instructions = [
            "You must provide a weekly report of what you worked on during this week. This",
            "report should be at least a paragraph (5-7 sentences) and requires your mentor's",
            "approval to verify the work that's been done."
        ]
        for line in report_instructions:
            c.drawString(72, y_pos, line)
            y_pos -= 12
        
        # Summary box
        y_pos -= 10
        box_height = 120
        c.setLineWidth(1)
        c.rect(72, y_pos - box_height, 500, box_height)
        
        c.setFont("Helvetica", 10)
        self._draw_wrapped_text_in_box(c, data.get('weekly_summary', ''), 
                                       82, y_pos - 15, 480, box_height - 20)
        
        c.save()
    
    def _draw_wrapped_text_in_box(self, c, text, x, y_start, max_width, max_height):
        """Helper to draw wrapped text inside a box"""
        from reportlab.pdfbase.pdfmetrics import stringWidth
        
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            width = stringWidth(test_line, "Helvetica", 10)
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        current_y = y_start
        line_height = 13
        
        for line in lines:
            if current_y - y_start + line_height > max_height:
                break
            c.drawString(x, current_y, line)
            current_y -= line_height

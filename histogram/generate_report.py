import numpy as np

import io
from svglib.svglib import svg2rlg
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4


class FooterCanvas(canvas.Canvas):

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_canvas(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_canvas(self, page_count):
        page = "Page %s of %s" % (self._pageNumber, page_count)
        x = 128
        self.saveState()
        self.setStrokeColorRGB(0, 0, 0)
        self.setLineWidth(0.5)
        self.line(66, 78, A4[0] - 66, 78)
        self.setFont('Helvetica', 10)
        self.drawString(A4[0]-x, 65, page)
        self.restoreState()


def scale(drawing, scaling_factor):
    """
    Scale a reportlab.graphics.shapes.Drawing()
    object while maintaining the aspect ratio
    """
    scaling_x = scaling_factor
    scaling_y = scaling_factor

    drawing.width = drawing.minWidth() * scaling_x
    drawing.height = drawing.height * scaling_y
    drawing.scale(scaling_x, scaling_y)
    return drawing


buf = io.BytesIO()

# --- Create histogram, legend and title ---
plt.figure()
r = np.random.randn(100)
r1 = r + 1
labels = ['Rabbits', 'Frogs']
H = plt.hist([r, r1], label=labels)
containers = H[-1]
leg = plt.legend(frameon=False)
plt.title("From a web browser, click on the legend\n"
          "marker to toggle the corresponding histogram.")

plt.savefig(buf, format="svg")
buf.seek(0)


flowable_image = scale(svg2rlg(buf), scaling_factor=.5)



styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))

story=[]
# logo = "image.png"
#
# # We really want to scale the image to fit in a box and keep proportions.
# im = Image(logo, 3*inch, 3*inch)
story.append(flowable_image)

#ptext = '<font size=12>Some text</font>'
#story.append(Paragraph(ptext, styles["Normal"]))

ptext = '''
<seq>. </seq>Some Text<br/>
<seq>. </seq>Some more test Text
'''
story.append(Paragraph(ptext, styles["Bullet"]))

ptext='<bullet>&bull;</bullet>Some Text'
story.append(Paragraph(ptext, styles["Bullet"]))

data = [['00', '01', '02', '03', '04'],
        ['10', '11', '12', '13', '14'],
        ['20', '21', '22', '23', '24'],
        ['30', '31', '32', '33', '34']]

t = Table(data)

t.setStyle(TableStyle([('BACKGROUND', (1, 1), (-2, -2), colors.green),
                       ('TEXTCOLOR', (0, 0), (1, -1), colors.red)]))

story.append(t)
doc = SimpleDocTemplate("form_letter.pdf",
                        rightMargin=72, leftMargin=72,
                        topMargin=72, bottomMargin=18)

doc.multiBuild(story, canvasmaker=FooterCanvas)

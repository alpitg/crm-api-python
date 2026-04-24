from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from io import BytesIO
from datetime import datetime

from app.modules.orders.schemas.invoice import InvoiceOut

class PDFService:
    @staticmethod
    def generate_invoice_pdf(invoice: InvoiceOut) -> BytesIO:
        """Generate PDF for invoice"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 12))

        # Invoice details
        invoice_info = [
            [f"Invoice Number: {invoice.invoiceNumber}", f"Date: {invoice.billDate.strftime('%d/%m/%Y')}"],
            [f"Payment Status: {invoice.paymentStatus.upper()}", f"Payment Mode: {invoice.paymentMode}"]
        ]

        table = Table(invoice_info, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))

        # Bill From and Bill To
        bill_info = [
            ["From:", "To:"],
            [Paragraph(f"<b>{invoice.billFrom.name}</b><br/>{invoice.billFrom.address or ''}<br/>{invoice.billFrom.phone or ''}<br/>{invoice.billFrom.email or ''}", styles['Normal']),
             Paragraph(f"<b>{invoice.billTo.name}</b><br/>{invoice.billTo.address or ''}<br/>{invoice.billTo.phone or ''}<br/>{invoice.billTo.email or ''}", styles['Normal'])]
        ]

        table = Table(bill_info, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))

        # Items table
        items_data = [["Item", "Qty", "Unit Price", "Discount", "Total"]]
        for item in invoice.items:
            items_data.append([
                item.name or item.description or "N/A",
                item.quantity - item.cancelledQty,
                f"₹{item.unitPrice:.2f}",
                f"₹{item.discountAmount:.2f}",
                f"₹{item.lineTotal:.2f}"
            ])

        table = Table(items_data, colWidths=[2.5*inch, 0.7*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))

        # Totals
        totals_data = [
            ["Subtotal:", f"₹{invoice.subtotal:.2f}"],
            ["Discount:", f"₹{invoice.discountAmount:.2f}"],
            ["Tax:", f"₹{invoice.taxAmount:.2f}"],
            ["Total Amount:", f"₹{invoice.totalAmount:.2f}"],
            ["Advance Paid:", f"₹{invoice.advancePaid:.2f}"],
            ["Balance Amount:", f"₹{invoice.balanceAmount:.2f}"]
        ]

        table = Table(totals_data, colWidths=[4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -2), (-1, -1), 1, colors.black),
        ]))
        story.append(table)

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
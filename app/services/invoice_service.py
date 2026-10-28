import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from flask import current_app
from app.models.payment import Invoice


class InvoiceService:
    """Generates official, downloadable PDF tax invoices using ReportLab."""

    @staticmethod
    def generate_pdf_invoice(invoice: Invoice) -> BytesIO:
        """
        Creates a PDF document in memory and returns a BytesIO buffer.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#0d6efd'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'InvoiceSub',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6c757d'),
            spaceAfter=12
        )
        section_style = ParagraphStyle(
            'InvoiceSection',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#212529'),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'InvoiceBody',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#212529')
        )
        bold_style = ParagraphStyle(
            'InvoiceBold',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#212529')
        )

        elements = []

        # Header Banner
        elements.append(Paragraph("<b>FixMate</b> — Home Service Management", title_style))
        elements.append(Paragraph("Official Tax Invoice | GST Registration: 27AABCF1234F1Z5", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0d6efd'), spaceAfter=15))

        # Invoice Metadata & Parties Table
        meta_data = [
            [
                Paragraph(f"<b>Invoice No:</b> {invoice.invoice_number}", body_style),
                Paragraph(f"<b>Date:</b> {invoice.generated_at.strftime('%d-%b-%Y %H:%M')}", body_style),
            ],
            [
                Paragraph(f"<b>Booking Ref:</b> {invoice.booking.booking_code}", body_style),
                Paragraph(f"<b>Payment Ref:</b> {invoice.payment.transaction_reference}", body_style),
            ],
            [
                Paragraph(f"<b>Billed To (Customer):</b><br/>{invoice.customer_name}<br/>{invoice.booking.service_address} (Pincode: {invoice.booking.pincode})", body_style),
                Paragraph(f"<b>Service Provider:</b><br/>{invoice.provider_name}<br/>Status: Verified FixMate Partner", body_style),
            ]
        ]
        meta_table = Table(meta_data, colWidths=[270, 270])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e9ecef')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 15))

        # Line Items Table
        elements.append(Paragraph("Service Item Details", section_style))
        items_data = [
            [
                Paragraph("<b>Description</b>", bold_style),
                Paragraph("<b>Service Date & Slot</b>", bold_style),
                Paragraph("<b>Amount (INR)</b>", bold_style),
            ],
            [
                Paragraph(f"Home Service: <b>{invoice.service_title}</b>", body_style),
                Paragraph(f"{invoice.booking.scheduled_date.strftime('%d-%b-%Y')}<br/>{invoice.booking.scheduled_time_slot}", body_style),
                Paragraph(f"₹{invoice.subtotal:.2f}", body_style),
            ],
            [
                Paragraph("Subtotal", bold_style),
                Paragraph("", body_style),
                Paragraph(f"₹{invoice.subtotal:.2f}", body_style),
            ],
            [
                Paragraph(f"Goods & Services Tax (GST @ {invoice.gst_rate}%)", body_style),
                Paragraph("CGST 9% + SGST 9%", subtitle_style),
                Paragraph(f"₹{invoice.gst_amount:.2f}", body_style),
            ],
            [
                Paragraph("<b>Total Paid</b>", bold_style),
                Paragraph(f"Paid via {invoice.payment.payment_method}", subtitle_style),
                Paragraph(f"<b>₹{invoice.total_amount:.2f}</b>", bold_style),
            ]
        ]
        items_table = Table(items_data, colWidths=[240, 180, 120])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e7f1ff')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#b6d4fe')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d1e7dd')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 20))

        # Footer notes
        footer_text = Paragraph(
            "<i>Note: This is a system-generated invoice generated for FixMate Home Service Management Platform (VESIT Academic Demo). Payments are handled in Demo Mode. Complaints or queries may be lodged within 7 days of service completion.</i>",
            subtitle_style
        )
        elements.append(footer_text)

        doc.build(elements)
        buffer.seek(0)
        return buffer

import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString('ar-SA', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const getStatusText = (status) => {
  const statusMap = {
    pending_engineer: 'بانتظار المهندس',
    approved_by_engineer: 'معتمد من المهندس',
    rejected_by_engineer: 'مرفوض',
    purchase_order_issued: 'تم إصدار أمر الشراء'
  };
  return statusMap[status] || status;
};

export const exportRequestToPDF = (request) => {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  doc.setR2L(true);
  
  // Title
  doc.setFontSize(20);
  doc.text('طلب مواد', 105, 20, { align: 'center' });
  
  doc.setFontSize(12);
  
  // Request info
  let yPos = 40;
  doc.text(`المشروع: ${request.project_name}`, 190, yPos, { align: 'right' });
  yPos += 10;
  doc.text(`المشرف: ${request.supervisor_name}`, 190, yPos, { align: 'right' });
  yPos += 10;
  doc.text(`المهندس: ${request.engineer_name}`, 190, yPos, { align: 'right' });
  yPos += 10;
  doc.text(`الحالة: ${getStatusText(request.status)}`, 190, yPos, { align: 'right' });
  yPos += 10;
  doc.text(`التاريخ: ${formatDate(request.created_at)}`, 190, yPos, { align: 'right' });
  yPos += 15;

  // Items table
  doc.text('الأصناف المطلوبة:', 190, yPos, { align: 'right' });
  yPos += 5;

  const items = request.items || [];
  const tableData = items.map((item, idx) => [
    item.unit || 'قطعة',
    String(item.quantity),
    item.name,
    idx + 1
  ]);

  doc.autoTable({
    head: [['الوحدة', 'الكمية', 'اسم المادة', '#']],
    body: tableData,
    startY: yPos,
    styles: { halign: 'right', fontSize: 11 },
    headStyles: { fillColor: [234, 88, 12], textColor: 255 },
    columnStyles: {
      0: { cellWidth: 30 },
      1: { cellWidth: 25 },
      2: { cellWidth: 100 },
      3: { cellWidth: 15 }
    }
  });

  yPos = doc.lastAutoTable.finalY + 15;
  doc.text(`سبب الطلب: ${request.reason}`, 190, yPos, { align: 'right' });

  if (request.rejection_reason) {
    yPos += 10;
    doc.setTextColor(255, 0, 0);
    doc.text(`سبب الرفض: ${request.rejection_reason}`, 190, yPos, { align: 'right' });
    doc.setTextColor(0, 0, 0);
  }

  // Footer
  doc.setFontSize(10);
  doc.text('نظام إدارة طلبات المواد', 105, 280, { align: 'center' });

  doc.save(`طلب_مواد_${request.id.slice(0, 8)}.pdf`);
};

export const exportPurchaseOrderToPDF = (order) => {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  doc.setR2L(true);
  
  // Title
  doc.setFontSize(22);
  doc.text('أمر شراء', 105, 20, { align: 'center' });
  
  doc.setFontSize(14);
  doc.text(`رقم الأمر: ${order.id?.slice(0, 8).toUpperCase() || 'N/A'}`, 105, 30, { align: 'center' });

  doc.setLineWidth(0.5);
  doc.line(20, 35, 190, 35);

  doc.setFontSize(12);
  
  let yPos = 50;
  doc.text(`المشروع: ${order.project_name || '-'}`, 190, yPos, { align: 'right' });
  yPos += 10;
  doc.text(`المورد: ${order.supplier_name || '-'}`, 190, yPos, { align: 'right' });
  yPos += 10;
  doc.text(`مدير المشتريات: ${order.manager_name || '-'}`, 190, yPos, { align: 'right' });
  yPos += 10;
  doc.text(`تاريخ الإصدار: ${order.created_at ? formatDate(order.created_at) : '-'}`, 190, yPos, { align: 'right' });
  yPos += 15;

  // Items table
  doc.text('المواد:', 190, yPos, { align: 'right' });
  yPos += 5;

  // Ensure items is always an array
  const items = Array.isArray(order.items) ? order.items : [];
  const tableData = items.map((item, idx) => [
    item.unit || 'قطعة',
    String(item.quantity || 0),
    item.name || '-',
    idx + 1
  ]);

  doc.autoTable({
    head: [['الوحدة', 'الكمية', 'اسم المادة', '#']],
    body: tableData,
    startY: yPos,
    styles: { halign: 'right', fontSize: 11 },
    headStyles: { fillColor: [234, 88, 12], textColor: 255 },
    columnStyles: {
      0: { cellWidth: 30 },
      1: { cellWidth: 25 },
      2: { cellWidth: 100 },
      3: { cellWidth: 15 }
    }
  });

  if (order.notes) {
    yPos = doc.lastAutoTable.finalY + 15;
    doc.text(`ملاحظات: ${order.notes}`, 190, yPos, { align: 'right' });
  }

  // Signature area
  yPos = doc.lastAutoTable.finalY + 40;
  doc.setLineWidth(0.3);
  doc.line(130, yPos, 190, yPos);
  doc.text('توقيع مدير المشتريات', 160, yPos + 7, { align: 'center' });

  // Footer
  doc.setFontSize(10);
  doc.text('نظام إدارة طلبات المواد', 105, 280, { align: 'center' });

  doc.save(`امر_شراء_${order.id?.slice(0, 8) || 'order'}.pdf`);
};

export const exportRequestsTableToPDF = (requests, title = 'قائمة الطلبات') => {
  const doc = new jsPDF({
    orientation: 'landscape',
    unit: 'mm',
    format: 'a4'
  });

  doc.setR2L(true);
  
  doc.setFontSize(18);
  doc.text(title, 148, 15, { align: 'center' });

  const tableData = requests.map(r => {
    const itemsCount = r.items?.length || 0;
    const itemsSummary = itemsCount > 0 
      ? (itemsCount === 1 ? r.items[0].name : `${r.items[0].name} + ${itemsCount - 1}`)
      : '-';
    return [
      formatDate(r.created_at),
      getStatusText(r.status),
      r.engineer_name,
      r.project_name,
      itemsSummary
    ];
  });

  const headers = [['التاريخ', 'الحالة', 'المهندس', 'المشروع', 'الأصناف']];

  doc.autoTable({
    head: headers,
    body: tableData,
    startY: 25,
    styles: { halign: 'right', fontSize: 10 },
    headStyles: { fillColor: [234, 88, 12], textColor: 255, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [248, 250, 252] }
  });

  doc.setFontSize(10);
  doc.text('نظام إدارة طلبات المواد', 148, 200, { align: 'center' });

  doc.save(`${title.replace(/\s/g, '_')}.pdf`);
};

export const exportPurchaseOrdersTableToPDF = (orders) => {
  const doc = new jsPDF({
    orientation: 'landscape',
    unit: 'mm',
    format: 'a4'
  });

  doc.setR2L(true);
  
  doc.setFontSize(18);
  doc.text('قائمة أوامر الشراء', 148, 15, { align: 'center' });

  const tableData = orders.map(o => {
    const itemsCount = o.items?.length || 0;
    const itemsSummary = itemsCount > 0 
      ? (itemsCount === 1 ? o.items[0].name : `${o.items[0].name} + ${itemsCount - 1}`)
      : '-';
    return [
      formatDate(o.created_at),
      o.supplier_name,
      o.project_name,
      itemsSummary
    ];
  });

  const headers = [['تاريخ الإصدار', 'المورد', 'المشروع', 'الأصناف']];

  doc.autoTable({
    head: headers,
    body: tableData,
    startY: 25,
    styles: { halign: 'right', fontSize: 10 },
    headStyles: { fillColor: [234, 88, 12], textColor: 255, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [248, 250, 252] }
  });

  doc.setFontSize(10);
  doc.text('نظام إدارة طلبات المواد', 148, 200, { align: 'center' });

  doc.save('اوامر_الشراء.pdf');
};

import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

// Arabic font support - using built-in Helvetica with UTF-8
const setupArabicFont = (doc) => {
  // For proper Arabic text, we'll use a different approach
  // jsPDF has limited Arabic support, so we'll configure it properly
  doc.setLanguage('ar');
  doc.setR2L(true);
};

const formatDate = (dateString) => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('ar-SA', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const formatDateShort = (dateString) => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('ar-SA', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

const getStatusText = (status) => {
  const statusMap = {
    pending_engineer: 'بانتظار المهندس',
    approved_by_engineer: 'معتمد من المهندس',
    rejected_by_engineer: 'مرفوض',
    purchase_order_issued: 'تم إصدار أمر الشراء',
    partially_ordered: 'جاري الإصدار'
  };
  return statusMap[status] || status;
};

const getOrderStatusText = (status) => {
  const statusMap = {
    pending_approval: 'بانتظار الاعتماد',
    approved: 'معتمد',
    printed: 'تمت الطباعة'
  };
  return statusMap[status] || status;
};

// Helper function to draw Arabic text using canvas
const drawArabicText = (doc, text, x, y, options = {}) => {
  const { align = 'right', fontSize = 12 } = options;
  doc.setFontSize(fontSize);
  doc.text(text || '-', x, y, { align });
};

export const exportRequestToPDF = (request) => {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  setupArabicFont(doc);
  
  // Header with border
  doc.setDrawColor(234, 88, 12);
  doc.setLineWidth(2);
  doc.line(20, 15, 190, 15);
  
  // Title
  doc.setFontSize(24);
  doc.setTextColor(234, 88, 12);
  drawArabicText(doc, 'طلب مواد', 105, 25, { align: 'center', fontSize: 24 });
  
  doc.setTextColor(0, 0, 0);
  doc.setFontSize(10);
  drawArabicText(doc, `رقم الطلب: ${request.id?.slice(0, 8).toUpperCase() || 'N/A'}`, 105, 32, { align: 'center', fontSize: 10 });
  
  doc.setLineWidth(0.5);
  doc.line(20, 38, 190, 38);

  // Request Details Section
  doc.setFontSize(12);
  let yPos = 48;
  
  // Box for request info
  doc.setFillColor(248, 250, 252);
  doc.rect(20, yPos - 5, 170, 45, 'F');
  
  doc.setFontSize(11);
  drawArabicText(doc, `المشروع: ${request.project_name || '-'}`, 185, yPos, { align: 'right', fontSize: 11 });
  yPos += 8;
  drawArabicText(doc, `المشرف: ${request.supervisor_name || '-'}`, 185, yPos, { align: 'right', fontSize: 11 });
  yPos += 8;
  drawArabicText(doc, `المهندس المسؤول: ${request.engineer_name || '-'}`, 185, yPos, { align: 'right', fontSize: 11 });
  yPos += 8;
  drawArabicText(doc, `تاريخ الطلب: ${formatDate(request.created_at)}`, 185, yPos, { align: 'right', fontSize: 11 });
  yPos += 8;
  drawArabicText(doc, `الحالة: ${getStatusText(request.status)}`, 185, yPos, { align: 'right', fontSize: 11 });
  yPos += 15;

  // Items table header
  doc.setFontSize(12);
  doc.setTextColor(234, 88, 12);
  drawArabicText(doc, 'الأصناف المطلوبة:', 185, yPos, { align: 'right', fontSize: 12 });
  doc.setTextColor(0, 0, 0);
  yPos += 5;

  const items = Array.isArray(request.items) ? request.items : [];
  const tableData = items.map((item, idx) => [
    item.unit || 'قطعة',
    String(item.quantity || 0),
    item.name || '-',
    String(idx + 1)
  ]);

  autoTable(doc, {
    head: [['الوحدة', 'الكمية', 'اسم المادة', '#']],
    body: tableData,
    startY: yPos,
    styles: { 
      halign: 'right', 
      fontSize: 10,
      cellPadding: 4,
      lineColor: [200, 200, 200],
      lineWidth: 0.1
    },
    headStyles: { 
      fillColor: [234, 88, 12], 
      textColor: 255,
      fontStyle: 'bold'
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252]
    },
    columnStyles: {
      0: { cellWidth: 25 },
      1: { cellWidth: 25, halign: 'center' },
      2: { cellWidth: 100 },
      3: { cellWidth: 15, halign: 'center' }
    }
  });

  yPos = doc.lastAutoTable.finalY + 10;
  
  // Reason section
  if (request.reason) {
    doc.setFillColor(255, 251, 235);
    doc.rect(20, yPos - 3, 170, 12, 'F');
    drawArabicText(doc, `سبب الطلب: ${request.reason}`, 185, yPos + 4, { align: 'right', fontSize: 10 });
    yPos += 15;
  }

  // Rejection reason if exists
  if (request.rejection_reason) {
    doc.setFillColor(254, 242, 242);
    doc.rect(20, yPos - 3, 170, 12, 'F');
    doc.setTextColor(220, 38, 38);
    drawArabicText(doc, `سبب الرفض: ${request.rejection_reason}`, 185, yPos + 4, { align: 'right', fontSize: 10 });
    doc.setTextColor(0, 0, 0);
  }

  // Footer
  doc.setDrawColor(200, 200, 200);
  doc.setLineWidth(0.5);
  doc.line(20, 275, 190, 275);
  doc.setFontSize(9);
  doc.setTextColor(100, 100, 100);
  drawArabicText(doc, 'نظام إدارة طلبات المواد', 105, 282, { align: 'center', fontSize: 9 });
  drawArabicText(doc, `تاريخ الطباعة: ${formatDate(new Date().toISOString())}`, 105, 287, { align: 'center', fontSize: 8 });

  doc.save(`طلب_مواد_${request.id?.slice(0, 8) || 'request'}.pdf`);
};

export const exportPurchaseOrderToPDF = (order) => {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  setupArabicFont(doc);
  
  // Header with double border
  doc.setDrawColor(234, 88, 12);
  doc.setLineWidth(2);
  doc.line(20, 12, 190, 12);
  doc.setLineWidth(0.5);
  doc.line(20, 15, 190, 15);
  
  // Title
  doc.setFontSize(26);
  doc.setTextColor(234, 88, 12);
  drawArabicText(doc, 'أمر شراء', 105, 28, { align: 'center', fontSize: 26 });
  
  doc.setTextColor(0, 0, 0);
  doc.setFontSize(12);
  drawArabicText(doc, `رقم الأمر: ${order.id?.slice(0, 8).toUpperCase() || 'N/A'}`, 105, 36, { align: 'center', fontSize: 12 });

  doc.setLineWidth(0.5);
  doc.line(20, 42, 190, 42);

  // Order Details Box
  let yPos = 52;
  doc.setFillColor(248, 250, 252);
  doc.rect(20, yPos - 5, 170, 50, 'F');
  
  doc.setFontSize(11);
  
  // Two columns layout
  // Right column
  drawArabicText(doc, `المشروع: ${order.project_name || '-'}`, 185, yPos, { align: 'right', fontSize: 11 });
  yPos += 8;
  drawArabicText(doc, `المورد: ${order.supplier_name || '-'}`, 185, yPos, { align: 'right', fontSize: 11 });
  yPos += 8;
  drawArabicText(doc, `مدير المشتريات: ${order.manager_name || '-'}`, 185, yPos, { align: 'right', fontSize: 11 });
  yPos += 8;
  drawArabicText(doc, `تاريخ الإصدار: ${formatDate(order.created_at)}`, 185, yPos, { align: 'right', fontSize: 11 });
  yPos += 8;
  drawArabicText(doc, `الحالة: ${getOrderStatusText(order.status)}`, 185, yPos, { align: 'right', fontSize: 11 });
  
  if (order.approved_at) {
    yPos += 8;
    drawArabicText(doc, `تاريخ الاعتماد: ${formatDate(order.approved_at)}`, 185, yPos, { align: 'right', fontSize: 11 });
  }
  
  yPos += 15;

  // Items table header
  doc.setFontSize(12);
  doc.setTextColor(234, 88, 12);
  drawArabicText(doc, 'المواد:', 185, yPos, { align: 'right', fontSize: 12 });
  doc.setTextColor(0, 0, 0);
  yPos += 5;

  const items = Array.isArray(order.items) ? order.items : [];
  const tableData = items.map((item, idx) => [
    item.unit || 'قطعة',
    String(item.quantity || 0),
    item.name || '-',
    String(idx + 1)
  ]);

  autoTable(doc, {
    head: [['الوحدة', 'الكمية', 'اسم المادة', '#']],
    body: tableData,
    startY: yPos,
    styles: { 
      halign: 'right', 
      fontSize: 10,
      cellPadding: 4,
      lineColor: [200, 200, 200],
      lineWidth: 0.1
    },
    headStyles: { 
      fillColor: [234, 88, 12], 
      textColor: 255,
      fontStyle: 'bold'
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252]
    },
    columnStyles: {
      0: { cellWidth: 25 },
      1: { cellWidth: 25, halign: 'center' },
      2: { cellWidth: 100 },
      3: { cellWidth: 15, halign: 'center' }
    }
  });

  yPos = doc.lastAutoTable.finalY + 10;

  // Notes section
  if (order.notes) {
    doc.setFillColor(255, 251, 235);
    doc.rect(20, yPos - 3, 170, 12, 'F');
    drawArabicText(doc, `ملاحظات: ${order.notes}`, 185, yPos + 4, { align: 'right', fontSize: 10 });
    yPos += 20;
  }

  // Signature area
  yPos = Math.max(yPos, 220);
  doc.setDrawColor(150, 150, 150);
  doc.setLineWidth(0.3);
  
  // Manager signature
  doc.line(130, yPos, 185, yPos);
  drawArabicText(doc, 'توقيع مدير المشتريات', 157, yPos + 6, { align: 'center', fontSize: 9 });
  
  // Supplier signature
  doc.line(25, yPos, 80, yPos);
  drawArabicText(doc, 'توقيع المورد', 52, yPos + 6, { align: 'center', fontSize: 9 });

  // Footer
  doc.setDrawColor(200, 200, 200);
  doc.setLineWidth(0.5);
  doc.line(20, 275, 190, 275);
  doc.setFontSize(9);
  doc.setTextColor(100, 100, 100);
  drawArabicText(doc, 'نظام إدارة طلبات المواد', 105, 282, { align: 'center', fontSize: 9 });
  drawArabicText(doc, `تاريخ الطباعة: ${formatDate(new Date().toISOString())}`, 105, 287, { align: 'center', fontSize: 8 });

  doc.save(`امر_شراء_${order.id?.slice(0, 8) || 'order'}.pdf`);
};

export const exportRequestsTableToPDF = (requests, title = 'قائمة الطلبات') => {
  const doc = new jsPDF({
    orientation: 'landscape',
    unit: 'mm',
    format: 'a4'
  });

  setupArabicFont(doc);
  
  doc.setFontSize(18);
  doc.setTextColor(234, 88, 12);
  drawArabicText(doc, title, 148, 15, { align: 'center', fontSize: 18 });
  doc.setTextColor(0, 0, 0);

  const tableData = requests.map(r => {
    const items = Array.isArray(r.items) ? r.items : [];
    const itemsCount = items.length;
    const itemsSummary = itemsCount > 0 
      ? (itemsCount === 1 ? items[0].name : `${items[0].name} + ${itemsCount - 1}`)
      : '-';
    return [
      formatDateShort(r.created_at),
      getStatusText(r.status),
      r.engineer_name || '-',
      r.supervisor_name || '-',
      r.project_name || '-',
      itemsSummary
    ];
  });

  const headers = [['التاريخ', 'الحالة', 'المهندس', 'المشرف', 'المشروع', 'الأصناف']];

  autoTable(doc, {
    head: headers,
    body: tableData,
    startY: 25,
    styles: { halign: 'right', fontSize: 9, cellPadding: 3 },
    headStyles: { fillColor: [234, 88, 12], textColor: 255, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [248, 250, 252] }
  });

  // Footer
  doc.setFontSize(9);
  doc.setTextColor(100, 100, 100);
  drawArabicText(doc, `نظام إدارة طلبات المواد - تاريخ التصدير: ${formatDateShort(new Date().toISOString())}`, 148, 200, { align: 'center', fontSize: 9 });

  doc.save(`${title.replace(/\s/g, '_')}.pdf`);
};

export const exportPurchaseOrdersTableToPDF = (orders) => {
  const doc = new jsPDF({
    orientation: 'landscape',
    unit: 'mm',
    format: 'a4'
  });

  setupArabicFont(doc);
  
  doc.setFontSize(18);
  doc.setTextColor(234, 88, 12);
  drawArabicText(doc, 'قائمة أوامر الشراء', 148, 15, { align: 'center', fontSize: 18 });
  doc.setTextColor(0, 0, 0);

  const tableData = orders.map(o => {
    const items = Array.isArray(o.items) ? o.items : [];
    const itemsCount = items.length;
    const itemsSummary = itemsCount > 0 
      ? (itemsCount === 1 ? items[0].name : `${items[0].name} + ${itemsCount - 1}`)
      : '-';
    return [
      formatDateShort(o.created_at),
      getOrderStatusText(o.status),
      o.manager_name || '-',
      o.supplier_name || '-',
      o.project_name || '-',
      itemsSummary
    ];
  });

  const headers = [['التاريخ', 'الحالة', 'مدير المشتريات', 'المورد', 'المشروع', 'الأصناف']];

  autoTable(doc, {
    head: headers,
    body: tableData,
    startY: 25,
    styles: { halign: 'right', fontSize: 9, cellPadding: 3 },
    headStyles: { fillColor: [234, 88, 12], textColor: 255, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [248, 250, 252] }
  });

  // Footer
  doc.setFontSize(9);
  doc.setTextColor(100, 100, 100);
  drawArabicText(doc, `نظام إدارة طلبات المواد - تاريخ التصدير: ${formatDateShort(new Date().toISOString())}`, 148, 200, { align: 'center', fontSize: 9 });

  doc.save('اوامر_الشراء.pdf');
};

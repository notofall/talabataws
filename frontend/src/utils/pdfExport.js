import jsPDF from 'jspdf';
import 'jspdf-autotable';

// Arabic font support - using built-in helvetica for now
// For full Arabic support, you'd need to add an Arabic font

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

  // Set RTL direction
  doc.setR2L(true);
  
  // Title
  doc.setFontSize(20);
  doc.text('طلب مواد', 105, 20, { align: 'center' });
  
  // Request details
  doc.setFontSize(12);
  
  const details = [
    ['اسم المادة:', request.material_name],
    ['الكمية:', String(request.quantity)],
    ['اسم المشروع:', request.project_name],
    ['سبب الطلب:', request.reason],
    ['المشرف:', request.supervisor_name],
    ['المهندس:', request.engineer_name],
    ['الحالة:', getStatusText(request.status)],
    ['تاريخ الإنشاء:', formatDate(request.created_at)]
  ];

  if (request.rejection_reason) {
    details.push(['سبب الرفض:', request.rejection_reason]);
  }

  let yPos = 40;
  details.forEach(([label, value]) => {
    doc.text(`${label} ${value}`, 190, yPos, { align: 'right' });
    yPos += 10;
  });

  // Footer
  doc.setFontSize(10);
  doc.text('نظام إدارة طلبات المواد', 105, 280, { align: 'center' });

  // Save
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
  
  // Order number
  doc.setFontSize(14);
  doc.text(`رقم الأمر: ${order.id.slice(0, 8).toUpperCase()}`, 105, 30, { align: 'center' });

  // Horizontal line
  doc.setLineWidth(0.5);
  doc.line(20, 35, 190, 35);

  // Details
  doc.setFontSize(12);
  
  const details = [
    ['اسم المادة:', order.material_name],
    ['الكمية:', String(order.quantity)],
    ['اسم المشروع:', order.project_name],
    ['المورد:', order.supplier_name],
    ['مدير المشتريات:', order.manager_name],
    ['تاريخ الإصدار:', formatDate(order.created_at)]
  ];

  if (order.notes) {
    details.push(['ملاحظات:', order.notes]);
  }

  let yPos = 50;
  details.forEach(([label, value]) => {
    doc.text(`${label} ${value}`, 190, yPos, { align: 'right' });
    yPos += 12;
  });

  // Signature area
  yPos += 20;
  doc.setLineWidth(0.3);
  doc.line(130, yPos + 15, 190, yPos + 15);
  doc.text('توقيع مدير المشتريات', 160, yPos + 22, { align: 'center' });

  // Footer
  doc.setFontSize(10);
  doc.text('نظام إدارة طلبات المواد', 105, 280, { align: 'center' });

  // Save
  doc.save(`امر_شراء_${order.id.slice(0, 8)}.pdf`);
};

export const exportRequestsTableToPDF = (requests, title = 'قائمة الطلبات') => {
  const doc = new jsPDF({
    orientation: 'landscape',
    unit: 'mm',
    format: 'a4'
  });

  doc.setR2L(true);
  
  // Title
  doc.setFontSize(18);
  doc.text(title, 148, 15, { align: 'center' });

  // Table data
  const tableData = requests.map(r => [
    formatDate(r.created_at),
    getStatusText(r.status),
    r.engineer_name,
    r.project_name,
    String(r.quantity),
    r.material_name
  ]);

  // Table headers (RTL order)
  const headers = [['التاريخ', 'الحالة', 'المهندس', 'المشروع', 'الكمية', 'اسم المادة']];

  doc.autoTable({
    head: headers,
    body: tableData,
    startY: 25,
    styles: {
      font: 'helvetica',
      halign: 'right',
      fontSize: 10
    },
    headStyles: {
      fillColor: [234, 88, 12],
      textColor: 255,
      fontStyle: 'bold'
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252]
    }
  });

  // Footer
  doc.setFontSize(10);
  doc.text('نظام إدارة طلبات المواد', 148, 200, { align: 'center' });

  // Save
  doc.save(`${title.replace(/\s/g, '_')}.pdf`);
};

export const exportPurchaseOrdersTableToPDF = (orders) => {
  const doc = new jsPDF({
    orientation: 'landscape',
    unit: 'mm',
    format: 'a4'
  });

  doc.setR2L(true);
  
  // Title
  doc.setFontSize(18);
  doc.text('قائمة أوامر الشراء', 148, 15, { align: 'center' });

  // Table data
  const tableData = orders.map(o => [
    formatDate(o.created_at),
    o.supplier_name,
    o.project_name,
    String(o.quantity),
    o.material_name
  ]);

  // Table headers
  const headers = [['تاريخ الإصدار', 'المورد', 'المشروع', 'الكمية', 'اسم المادة']];

  doc.autoTable({
    head: headers,
    body: tableData,
    startY: 25,
    styles: {
      font: 'helvetica',
      halign: 'right',
      fontSize: 10
    },
    headStyles: {
      fillColor: [234, 88, 12],
      textColor: 255,
      fontStyle: 'bold'
    },
    alternateRowStyles: {
      fillColor: [248, 250, 252]
    }
  });

  // Footer
  doc.setFontSize(10);
  doc.text('نظام إدارة طلبات المواد', 148, 200, { align: 'center' });

  // Save
  doc.save('اوامر_الشراء.pdf');
};

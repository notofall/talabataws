import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const formatDate = (dateString) => {
  if (!dateString) return '-';
  try {
    return new Date(dateString).toLocaleDateString('ar-SA', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateString;
  }
};

const formatDateShort = (dateString) => {
  if (!dateString) return '-';
  try {
    return new Date(dateString).toLocaleDateString('ar-SA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch {
    return dateString;
  }
};

const getStatusText = (status) => {
  const statusMap = {
    pending_engineer: 'Pending Engineer',
    approved_by_engineer: 'Approved',
    rejected_by_engineer: 'Rejected',
    purchase_order_issued: 'PO Issued',
    partially_ordered: 'Partially Ordered'
  };
  return statusMap[status] || status;
};

const getStatusTextAr = (status) => {
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
    pending_approval: 'Pending Approval',
    approved: 'Approved',
    printed: 'Printed'
  };
  return statusMap[status] || status;
};

const getOrderStatusTextAr = (status) => {
  const statusMap = {
    pending_approval: 'بانتظار الاعتماد',
    approved: 'معتمد',
    printed: 'تمت الطباعة'
  };
  return statusMap[status] || status;
};

export const exportRequestToPDF = (request) => {
  const doc = new jsPDF();
  
  // Title
  doc.setFontSize(20);
  doc.setTextColor(234, 88, 12);
  doc.text('Material Request', 105, 20, { align: 'center' });
  doc.text('طلب مواد', 105, 28, { align: 'center' });
  
  doc.setTextColor(0, 0, 0);
  doc.setFontSize(10);
  doc.text(`Request #: ${request.id?.slice(0, 8).toUpperCase() || 'N/A'}`, 105, 36, { align: 'center' });
  
  doc.setLineWidth(0.5);
  doc.setDrawColor(234, 88, 12);
  doc.line(20, 40, 190, 40);

  // Request Info
  doc.setFontSize(11);
  let y = 50;
  
  doc.text(`Project: ${request.project_name || '-'}`, 20, y);
  doc.text(`Date: ${formatDateShort(request.created_at)}`, 120, y);
  y += 8;
  
  doc.text(`Supervisor: ${request.supervisor_name || '-'}`, 20, y);
  doc.text(`Engineer: ${request.engineer_name || '-'}`, 120, y);
  y += 8;
  
  doc.text(`Status: ${getStatusText(request.status)}`, 20, y);
  if (request.reason) {
    doc.text(`Reason: ${request.reason}`, 120, y);
  }
  y += 15;

  // Items Table
  doc.setFontSize(12);
  doc.setTextColor(234, 88, 12);
  doc.text('Items:', 20, y);
  doc.setTextColor(0, 0, 0);
  y += 5;

  const items = Array.isArray(request.items) ? request.items : [];
  const tableData = items.map((item, idx) => [
    idx + 1,
    item.name || '-',
    item.quantity || 0,
    item.unit || 'pcs'
  ]);

  autoTable(doc, {
    head: [['#', 'Material Name', 'Qty', 'Unit']],
    body: tableData,
    startY: y,
    styles: { fontSize: 10, cellPadding: 3 },
    headStyles: { fillColor: [234, 88, 12], textColor: 255 },
    alternateRowStyles: { fillColor: [248, 250, 252] }
  });

  // Rejection reason
  if (request.rejection_reason) {
    y = doc.lastAutoTable.finalY + 10;
    doc.setTextColor(220, 38, 38);
    doc.text(`Rejection Reason: ${request.rejection_reason}`, 20, y);
    doc.setTextColor(0, 0, 0);
  }

  // Footer
  doc.setFontSize(9);
  doc.setTextColor(100, 100, 100);
  doc.text('Material Request Management System', 105, 285, { align: 'center' });

  doc.save(`request_${request.id?.slice(0, 8) || 'doc'}.pdf`);
};

export const exportPurchaseOrderToPDF = (order) => {
  const doc = new jsPDF();
  
  // Header
  doc.setDrawColor(234, 88, 12);
  doc.setLineWidth(2);
  doc.line(20, 15, 190, 15);
  
  // Title
  doc.setFontSize(22);
  doc.setTextColor(234, 88, 12);
  doc.text('Purchase Order', 105, 25, { align: 'center' });
  doc.text('أمر شراء', 105, 33, { align: 'center' });
  
  doc.setTextColor(0, 0, 0);
  doc.setFontSize(11);
  doc.text(`PO #: ${order.id?.slice(0, 8).toUpperCase() || 'N/A'}`, 105, 42, { align: 'center' });
  doc.setFontSize(10);
  doc.setTextColor(100, 100, 100);
  doc.text(`Request #: ${order.request_id?.slice(0, 8).toUpperCase() || 'N/A'}`, 105, 48, { align: 'center' });
  
  doc.setLineWidth(0.5);
  doc.setDrawColor(234, 88, 12);
  doc.line(20, 52, 190, 52);

  // Order Info
  doc.setTextColor(0, 0, 0);
  doc.setFontSize(11);
  let y = 62;
  
  doc.text(`Project: ${order.project_name || '-'}`, 20, y);
  doc.text(`Issue Date: ${formatDateShort(order.created_at)}`, 120, y);
  y += 8;
  
  doc.text(`Supplier: ${order.supplier_name || '-'}`, 20, y);
  doc.text(`Manager: ${order.manager_name || '-'}`, 120, y);
  y += 8;
  
  doc.text(`Status: ${getOrderStatusText(order.status)}`, 20, y);
  if (order.approved_at) {
    doc.text(`Approved: ${formatDateShort(order.approved_at)}`, 120, y);
  }
  y += 15;

  // Items Table
  doc.setFontSize(12);
  doc.setTextColor(234, 88, 12);
  doc.text('Items:', 20, y);
  doc.setTextColor(0, 0, 0);
  y += 5;

  const items = Array.isArray(order.items) ? order.items : [];
  const tableData = items.map((item, idx) => [
    idx + 1,
    item.name || '-',
    item.quantity || 0,
    item.unit || 'pcs'
  ]);

  autoTable(doc, {
    head: [['#', 'Material Name', 'Qty', 'Unit']],
    body: tableData,
    startY: y,
    styles: { fontSize: 10, cellPadding: 3 },
    headStyles: { fillColor: [234, 88, 12], textColor: 255 },
    alternateRowStyles: { fillColor: [248, 250, 252] }
  });

  y = doc.lastAutoTable.finalY + 10;

  // Notes
  if (order.notes) {
    doc.text(`Notes: ${order.notes}`, 20, y);
    y += 15;
  }

  // Signature Lines
  y = Math.max(y + 20, 220);
  doc.setDrawColor(150, 150, 150);
  doc.setLineWidth(0.3);
  
  doc.line(20, y, 80, y);
  doc.setFontSize(9);
  doc.text('Supplier Signature', 50, y + 6, { align: 'center' });
  
  doc.line(130, y, 190, y);
  doc.text('Manager Signature', 160, y + 6, { align: 'center' });

  // Footer
  doc.setFontSize(9);
  doc.setTextColor(100, 100, 100);
  doc.text('Material Request Management System', 105, 285, { align: 'center' });

  doc.save(`PO_${order.id?.slice(0, 8) || 'doc'}.pdf`);
};

export const exportRequestsTableToPDF = (requests, title = 'Requests List') => {
  const doc = new jsPDF('landscape');
  
  doc.setFontSize(16);
  doc.setTextColor(234, 88, 12);
  doc.text(title, 148, 15, { align: 'center' });
  doc.setTextColor(0, 0, 0);

  const tableData = requests.map(r => {
    const items = Array.isArray(r.items) ? r.items : [];
    const itemsSummary = items.length > 0 
      ? (items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`)
      : '-';
    return [
      itemsSummary,
      r.project_name || '-',
      r.supervisor_name || '-',
      r.engineer_name || '-',
      getStatusText(r.status),
      formatDateShort(r.created_at)
    ];
  });

  autoTable(doc, {
    head: [['Items', 'Project', 'Supervisor', 'Engineer', 'Status', 'Date']],
    body: tableData,
    startY: 25,
    styles: { fontSize: 9, cellPadding: 3 },
    headStyles: { fillColor: [234, 88, 12], textColor: 255 },
    alternateRowStyles: { fillColor: [248, 250, 252] }
  });

  doc.setFontSize(9);
  doc.setTextColor(100, 100, 100);
  doc.text(`Exported: ${formatDateShort(new Date().toISOString())}`, 148, 200, { align: 'center' });

  doc.save(`${title.replace(/\s/g, '_')}.pdf`);
};

export const exportPurchaseOrdersTableToPDF = (orders) => {
  const doc = new jsPDF('landscape');
  
  doc.setFontSize(16);
  doc.setTextColor(234, 88, 12);
  doc.text('Purchase Orders List', 148, 15, { align: 'center' });
  doc.setTextColor(0, 0, 0);

  const tableData = orders.map(o => {
    const items = Array.isArray(o.items) ? o.items : [];
    const itemsSummary = items.length > 0 
      ? (items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`)
      : '-';
    return [
      o.id?.slice(0, 8).toUpperCase() || '-',
      itemsSummary,
      o.project_name || '-',
      o.supplier_name || '-',
      o.manager_name || '-',
      getOrderStatusText(o.status),
      formatDateShort(o.created_at)
    ];
  });

  autoTable(doc, {
    head: [['PO #', 'Items', 'Project', 'Supplier', 'Manager', 'Status', 'Date']],
    body: tableData,
    startY: 25,
    styles: { fontSize: 9, cellPadding: 3 },
    headStyles: { fillColor: [234, 88, 12], textColor: 255 },
    alternateRowStyles: { fillColor: [248, 250, 252] }
  });

  doc.setFontSize(9);
  doc.setTextColor(100, 100, 100);
  doc.text(`Exported: ${formatDateShort(new Date().toISOString())}`, 148, 200, { align: 'center' });

  doc.save('purchase_orders.pdf');
};

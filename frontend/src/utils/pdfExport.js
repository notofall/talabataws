// PDF Export using Browser Print (Full Arabic Support)

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

const getOrderStatusTextAr = (status) => {
  const statusMap = {
    pending_approval: 'بانتظار الاعتماد',
    approved: 'معتمد',
    printed: 'تمت الطباعة'
  };
  return statusMap[status] || status;
};

const printHTML = (html, title) => {
  const printWindow = window.open('', '_blank', 'width=800,height=600');
  printWindow.document.write(`
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
      <meta charset="UTF-8">
      <title>${title}</title>
      <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }
        body {
          font-family: 'Cairo', 'Segoe UI', Tahoma, Arial, sans-serif;
          direction: rtl;
          text-align: right;
          padding: 20px;
          background: white;
          color: #1e293b;
        }
        @media print {
          body { padding: 0; }
          .no-print { display: none !important; }
        }
        table {
          width: 100%;
          border-collapse: collapse;
        }
        th, td {
          padding: 10px;
          border: 1px solid #e2e8f0;
        }
        th {
          background: #ea580c;
          color: white;
        }
        .header {
          border-bottom: 4px solid #ea580c;
          padding-bottom: 15px;
          margin-bottom: 25px;
          text-align: center;
        }
        .title {
          color: #ea580c;
          font-size: 32px;
          font-weight: 700;
          margin-bottom: 5px;
        }
        .subtitle {
          color: #475569;
          font-size: 14px;
        }
        .info-box {
          background: #f8fafc;
          padding: 20px;
          border-radius: 8px;
          margin-bottom: 25px;
        }
        .info-row {
          display: flex;
          margin-bottom: 10px;
        }
        .info-label {
          color: #64748b;
          font-weight: 600;
          min-width: 120px;
        }
        .badge {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 4px;
          font-size: 12px;
        }
        .badge-green {
          background: #dcfce7;
          color: #166534;
        }
        .badge-blue {
          background: #dbeafe;
          color: #1e40af;
        }
        .section-title {
          color: #ea580c;
          font-size: 16px;
          border-bottom: 2px solid #ea580c;
          padding-bottom: 8px;
          margin-bottom: 15px;
        }
        .signature-area {
          display: flex;
          justify-content: space-between;
          margin-top: 60px;
          padding: 0 50px;
        }
        .signature-box {
          text-align: center;
          width: 40%;
        }
        .signature-line {
          border-top: 2px solid #94a3b8;
          padding-top: 10px;
          margin-top: 50px;
          color: #64748b;
          font-size: 13px;
        }
        .footer {
          border-top: 2px solid #e2e8f0;
          padding-top: 20px;
          margin-top: 40px;
          text-align: center;
          color: #64748b;
          font-size: 11px;
        }
        .notes-box {
          background: #fffbeb;
          border: 1px solid #fde68a;
          padding: 15px;
          border-radius: 8px;
          margin-bottom: 25px;
        }
        .print-btn {
          position: fixed;
          top: 20px;
          left: 20px;
          background: #ea580c;
          color: white;
          border: none;
          padding: 10px 20px;
          border-radius: 8px;
          cursor: pointer;
          font-family: inherit;
          font-size: 14px;
        }
        .print-btn:hover {
          background: #c2410c;
        }
      </style>
    </head>
    <body>
      <button class="print-btn no-print" onclick="window.print()">طباعة / حفظ PDF</button>
      ${html}
      <script>
        // Auto print after fonts load
        document.fonts.ready.then(() => {
          setTimeout(() => window.print(), 500);
        });
      </script>
    </body>
    </html>
  `);
  printWindow.document.close();
};

export const exportRequestToPDF = (request) => {
  const items = Array.isArray(request.items) ? request.items : [];
  const itemsRows = items.map((item, idx) => `
    <tr style="background: ${idx % 2 === 0 ? '#f8fafc' : '#fff'};">
      <td style="text-align: center; width: 40px;">${idx + 1}</td>
      <td>${item.name || '-'}</td>
      <td style="text-align: center; width: 80px;">${item.quantity || 0}</td>
      <td style="text-align: center; width: 80px;">${item.unit || 'قطعة'}</td>
    </tr>
  `).join('');

  const requestNumber = request.request_number || request.id?.slice(0, 8).toUpperCase() || '-';

  const html = `
    <div class="header">
      <div class="title">طلب مواد</div>
      <div class="subtitle">رقم الطلب: ${requestNumber}</div>
    </div>
    
    <div class="info-box">
      <table style="border: none;">
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0; width: 50%;"><span class="info-label">المشروع:</span> ${request.project_name || '-'}</td>
          <td style="border: none; padding: 8px 0;"><span class="info-label">تاريخ الطلب:</span> ${formatDate(request.created_at)}</td>
        </tr>
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0;"><span class="info-label">المشرف:</span> ${request.supervisor_name || '-'}</td>
          <td style="border: none; padding: 8px 0;"><span class="info-label">المهندس:</span> ${request.engineer_name || '-'}</td>
        </tr>
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0;"><span class="info-label">الحالة:</span> <span class="badge badge-green">${getStatusTextAr(request.status)}</span></td>
          <td style="border: none; padding: 8px 0;"><span class="info-label">سبب الطلب:</span> ${request.reason || '-'}</td>
        </tr>
      </table>
    </div>
    
    <div class="section-title">الأصناف المطلوبة</div>
    <table>
      <thead>
        <tr>
          <th style="width: 40px;">#</th>
          <th>اسم المادة</th>
          <th style="width: 80px;">الكمية</th>
          <th style="width: 80px;">الوحدة</th>
        </tr>
      </thead>
      <tbody>${itemsRows}</tbody>
    </table>
    
    ${request.rejection_reason ? `
      <div class="notes-box" style="background: #fef2f2; border-color: #fecaca; margin-top: 20px;">
        <strong style="color: #dc2626;">سبب الرفض:</strong> ${request.rejection_reason}
      </div>
    ` : ''}
    
    <div class="footer">
      <p>نظام إدارة طلبات المواد</p>
      <p style="margin-top: 5px;">تاريخ الطباعة: ${formatDate(new Date().toISOString())}</p>
    </div>
  `;

  printHTML(html, `طلب مواد - ${requestNumber}`);
};

export const exportPurchaseOrderToPDF = (order) => {
  const items = Array.isArray(order.items) ? order.items : [];
  const itemsRows = items.map((item, idx) => `
    <tr style="background: ${idx % 2 === 0 ? '#f8fafc' : '#fff'};">
      <td style="text-align: center; width: 40px;">${idx + 1}</td>
      <td>${item.name || '-'}</td>
      <td style="text-align: center; width: 80px;">${item.quantity || 0}</td>
      <td style="text-align: center; width: 80px;">${item.unit || 'قطعة'}</td>
    </tr>
  `).join('');

  const html = `
    <div style="border: 4px solid #ea580c; padding: 20px; margin-bottom: 25px; text-align: center;">
      <div class="title">أمر شراء</div>
      <div style="font-size: 16px; font-weight: bold; margin-top: 10px;">رقم الأمر: ${order.id?.slice(0, 8).toUpperCase() || '-'}</div>
      <div class="subtitle">رقم الطلب: ${order.request_id?.slice(0, 8).toUpperCase() || '-'}</div>
    </div>
    
    <div class="info-box">
      <table style="border: none;">
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0; width: 50%;"><span class="info-label">المشروع:</span> ${order.project_name || '-'}</td>
          <td style="border: none; padding: 8px 0;"><span class="info-label">تاريخ الإصدار:</span> ${formatDate(order.created_at)}</td>
        </tr>
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0;"><span class="info-label">المورد:</span> <span class="badge badge-green">${order.supplier_name || '-'}</span></td>
          <td style="border: none; padding: 8px 0;"><span class="info-label">مدير المشتريات:</span> ${order.manager_name || '-'}</td>
        </tr>
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0;"><span class="info-label">المشرف:</span> ${order.supervisor_name || '-'}</td>
          <td style="border: none; padding: 8px 0;"><span class="info-label">المهندس:</span> ${order.engineer_name || '-'}</td>
        </tr>
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0;"><span class="info-label">الحالة:</span> <span class="badge badge-blue">${getOrderStatusTextAr(order.status)}</span></td>
          <td style="border: none; padding: 8px 0;">${order.approved_at ? `<span class="info-label">تاريخ الاعتماد:</span> ${formatDate(order.approved_at)}` : ''}</td>
        </tr>
      </table>
    </div>
    
    <div class="section-title">المواد</div>
    <table>
      <thead>
        <tr>
          <th style="width: 40px;">#</th>
          <th>اسم المادة</th>
          <th style="width: 80px;">الكمية</th>
          <th style="width: 80px;">الوحدة</th>
        </tr>
      </thead>
      <tbody>${itemsRows}</tbody>
    </table>
    
    ${order.notes ? `
      <div class="notes-box" style="margin-top: 20px;">
        <strong style="color: #92400e;">ملاحظات:</strong> ${order.notes}
      </div>
    ` : ''}
    
    <div class="signature-area">
      <div class="signature-box">
        <div class="signature-line">توقيع المورد</div>
      </div>
      <div class="signature-box">
        <div class="signature-line">توقيع مدير المشتريات</div>
      </div>
    </div>
    
    <div class="footer">
      <p>نظام إدارة طلبات المواد</p>
      <p style="margin-top: 5px;">تاريخ الطباعة: ${formatDate(new Date().toISOString())}</p>
    </div>
  `;

  printHTML(html, `أمر شراء - ${order.id?.slice(0, 8) || ''}`);
};

export const exportRequestsTableToPDF = (requests, title = 'قائمة الطلبات') => {
  const rows = requests.map((r, idx) => {
    const items = Array.isArray(r.items) ? r.items : [];
    const itemsSummary = items.length > 0 
      ? (items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`)
      : '-';
    return `
      <tr style="background: ${idx % 2 === 0 ? '#f8fafc' : '#fff'};">
        <td>${itemsSummary}</td>
        <td>${r.project_name || '-'}</td>
        <td>${r.supervisor_name || '-'}</td>
        <td>${r.engineer_name || '-'}</td>
        <td><span class="badge badge-green">${getStatusTextAr(r.status)}</span></td>
        <td>${formatDateShort(r.created_at)}</td>
      </tr>
    `;
  }).join('');

  const html = `
    <div class="header">
      <div class="title">${title}</div>
    </div>
    
    <table>
      <thead>
        <tr>
          <th>الأصناف</th>
          <th>المشروع</th>
          <th>المشرف</th>
          <th>المهندس</th>
          <th>الحالة</th>
          <th>التاريخ</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    
    <div class="footer">
      <p>نظام إدارة طلبات المواد - تاريخ التصدير: ${formatDateShort(new Date().toISOString())}</p>
    </div>
  `;

  printHTML(html, title);
};

export const exportPurchaseOrdersTableToPDF = (orders) => {
  const rows = orders.map((o, idx) => {
    const items = Array.isArray(o.items) ? o.items : [];
    const itemsSummary = items.length > 0 
      ? (items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`)
      : '-';
    return `
      <tr style="background: ${idx % 2 === 0 ? '#f8fafc' : '#fff'};">
        <td style="font-weight: bold;">${o.id?.slice(0, 8).toUpperCase() || '-'}</td>
        <td>${itemsSummary}</td>
        <td>${o.project_name || '-'}</td>
        <td><span class="badge badge-green">${o.supplier_name || '-'}</span></td>
        <td>${o.manager_name || '-'}</td>
        <td><span class="badge badge-blue">${getOrderStatusTextAr(o.status)}</span></td>
        <td>${formatDateShort(o.created_at)}</td>
      </tr>
    `;
  }).join('');

  const html = `
    <div class="header">
      <div class="title">قائمة أوامر الشراء</div>
    </div>
    
    <table>
      <thead>
        <tr>
          <th>رقم الأمر</th>
          <th>الأصناف</th>
          <th>المشروع</th>
          <th>المورد</th>
          <th>مدير المشتريات</th>
          <th>الحالة</th>
          <th>التاريخ</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    
    <div class="footer">
      <p>نظام إدارة طلبات المواد - تاريخ التصدير: ${formatDateShort(new Date().toISOString())}</p>
    </div>
  `;

  printHTML(html, 'قائمة أوامر الشراء');
};

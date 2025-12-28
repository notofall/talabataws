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
    printed: 'تمت الطباعة',
    shipped: 'تم الشحن',
    partially_delivered: 'تسليم جزئي',
    delivered: 'تم التسليم'
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
          padding: 25px;
          background: white;
          color: #1e293b;
          font-size: 12px;
          max-width: 900px;
          margin: 0 auto;
        }
        @media print {
          body { 
            padding: 15px; 
            font-size: 11px;
          }
          .no-print { display: none !important; }
          @page {
            size: A4;
            margin: 15mm;
          }
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 11px;
          margin: 15px 0;
        }
        th, td {
          padding: 8px 10px;
          border: 1px solid #e2e8f0;
        }
        th {
          background: #ea580c;
          color: white;
          font-size: 11px;
          font-weight: 600;
        }
        td {
          font-size: 11px;
        }
        .header {
          border-bottom: 3px solid #ea580c;
          padding-bottom: 12px;
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
  
  // Calculate totals
  const totalAmount = items.reduce((sum, item) => sum + (item.total_price || (item.unit_price || 0) * (item.quantity || 0)), 0);
  
  const itemsRows = items.map((item, idx) => {
    const unitPrice = item.unit_price || 0;
    const itemTotal = item.total_price || (unitPrice * (item.quantity || 0));
    return `
    <tr style="background: ${idx % 2 === 0 ? '#f8fafc' : '#fff'};">
      <td style="text-align: center; width: 40px;">${idx + 1}</td>
      <td>${item.name || '-'}</td>
      <td style="text-align: center; width: 70px;">${item.quantity || 0}</td>
      <td style="text-align: center; width: 70px;">${item.unit || 'قطعة'}</td>
      <td style="text-align: center; width: 90px;">${unitPrice > 0 ? unitPrice.toLocaleString('ar-SA') : '-'}</td>
      <td style="text-align: center; width: 100px; font-weight: bold;">${itemTotal > 0 ? itemTotal.toLocaleString('ar-SA') : '-'}</td>
    </tr>
  `}).join('');

  const requestNumber = order.request_number || order.request_id?.slice(0, 8).toUpperCase() || '-';
  const expectedDelivery = order.expected_delivery_date ? formatDate(order.expected_delivery_date) : '-';

  const html = `
    <div style="border: 4px solid #ea580c; padding: 20px; margin-bottom: 25px; text-align: center;">
      <div class="title">أمر شراء</div>
      <div style="font-size: 16px; font-weight: bold; margin-top: 10px;">رقم الأمر: ${order.id?.slice(0, 8).toUpperCase() || '-'}</div>
      <div class="subtitle">رقم الطلب: ${requestNumber}</div>
    </div>
    
    <div class="info-box">
      <table style="border: none;">
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0; width: 50%;"><span class="info-label">المشروع:</span> ${order.project_name || '-'}</td>
          <td style="border: none; padding: 8px 0;"><span class="info-label">تاريخ الإصدار:</span> ${formatDate(order.created_at)}</td>
        </tr>
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0;"><span class="info-label">المورد:</span> <span class="badge badge-green">${order.supplier_name || '-'}</span></td>
          <td style="border: none; padding: 8px 0;"><span class="info-label">تاريخ التسليم المتوقع:</span> ${expectedDelivery}</td>
        </tr>
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0;"><span class="info-label">المشرف:</span> ${order.supervisor_name || '-'}</td>
          <td style="border: none; padding: 8px 0;"><span class="info-label">المهندس:</span> ${order.engineer_name || '-'}</td>
        </tr>
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0;"><span class="info-label">مدير المشتريات:</span> ${order.manager_name || '-'}</td>
          <td style="border: none; padding: 8px 0;"><span class="info-label">الحالة:</span> <span class="badge badge-blue">${getOrderStatusTextAr(order.status)}</span></td>
        </tr>
        ${order.category_name ? `
        <tr style="border: none;">
          <td style="border: none; padding: 8px 0;" colspan="2"><span class="info-label">تصنيف الميزانية:</span> <span style="color: #ea580c; font-weight: bold;">${order.category_name}</span></td>
        </tr>
        ` : ''}
      </table>
    </div>
    
    <div class="section-title">المواد والأسعار</div>
    <table>
      <thead>
        <tr>
          <th style="width: 40px;">#</th>
          <th>اسم المادة</th>
          <th style="width: 70px;">الكمية</th>
          <th style="width: 70px;">الوحدة</th>
          <th style="width: 90px;">سعر الوحدة</th>
          <th style="width: 100px;">الإجمالي</th>
        </tr>
      </thead>
      <tbody>${itemsRows}</tbody>
      <tfoot>
        <tr style="background: #fef3c7; font-weight: bold;">
          <td colspan="5" style="text-align: left; padding: 12px;">المجموع الكلي</td>
          <td style="text-align: center; font-size: 16px; color: #ea580c;">${totalAmount > 0 ? totalAmount.toLocaleString('ar-SA') + ' ر.س' : '-'}</td>
        </tr>
      </tfoot>
    </table>
    
    ${order.notes ? `
      <div class="notes-box" style="margin-top: 20px;">
        <strong style="color: #92400e;">ملاحظات:</strong> ${order.notes}
      </div>
    ` : ''}
    
    ${order.terms_conditions ? `
      <div class="notes-box" style="margin-top: 15px; background: #f0f9ff; border-color: #bae6fd;">
        <strong style="color: #0369a1;">الشروط والأحكام:</strong><br/>
        <div style="margin-top: 8px; white-space: pre-line;">${order.terms_conditions}</div>
      </div>
    ` : ''}
    
    <div class="signature-area">
      <div class="signature-box">
        <div class="signature-line">توقيع المورد</div>
        <p style="font-size: 10px; color: #666; margin-top: 5px;">التاريخ: _______________</p>
      </div>
      <div class="signature-box">
        <div class="signature-line">توقيع مدير المشتريات</div>
        <p style="font-size: 10px; color: #666; margin-top: 5px;">التاريخ: _______________</p>
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

// تصدير تقرير الميزانية
export const exportBudgetReportToPDF = (report, projectName = null) => {
  const categoriesRows = report.categories?.map((cat, idx) => `
    <tr style="background: ${idx % 2 === 0 ? '#f8fafc' : '#fff'};">
      <td style="font-weight: bold;">${cat.name}</td>
      <td>${cat.project_name || '-'}</td>
      <td style="text-align: center; color: #2563eb;">${cat.estimated_budget?.toLocaleString('ar-SA')} ر.س</td>
      <td style="text-align: center; color: #ea580c;">${cat.actual_spent?.toLocaleString('ar-SA')} ر.س</td>
      <td style="text-align: center; font-weight: bold; color: ${cat.remaining >= 0 ? '#16a34a' : '#dc2626'};">${cat.remaining?.toLocaleString('ar-SA')} ر.س</td>
      <td style="text-align: center;">
        <span style="padding: 4px 8px; border-radius: 4px; font-size: 10px; background: ${cat.status === 'over_budget' ? '#fef2f2' : '#f0fdf4'}; color: ${cat.status === 'over_budget' ? '#dc2626' : '#16a34a'};">
          ${cat.status === 'over_budget' ? 'تجاوز' : 'ضمن الميزانية'}
        </span>
      </td>
    </tr>
  `).join('') || '';

  const html = `
    <div class="header">
      <div class="title">تقرير الميزانية</div>
      ${projectName ? `<p style="font-size: 14px; color: #64748b; margin-top: 5px;">${projectName}</p>` : ''}
      ${report.project ? `
        <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px; margin-top: 15px; text-align: right;">
          <p style="font-weight: bold; color: #1e40af; margin: 0;">${report.project.name}</p>
          <p style="font-size: 12px; color: #3b82f6; margin: 5px 0 0 0;">المالك: ${report.project.owner_name}</p>
          ${report.project.location ? `<p style="font-size: 11px; color: #64748b; margin: 3px 0 0 0;">${report.project.location}</p>` : ''}
        </div>
      ` : ''}
    </div>
    
    <div style="display: flex; gap: 15px; margin: 20px 0; flex-wrap: wrap;">
      <div style="flex: 1; min-width: 150px; background: linear-gradient(135deg, #eff6ff, #dbeafe); border-radius: 10px; padding: 15px; text-align: center;">
        <p style="font-size: 11px; color: #64748b; margin: 0;">الميزانية التقديرية</p>
        <p style="font-size: 20px; font-weight: bold; color: #2563eb; margin: 5px 0 0 0;">${report.total_estimated?.toLocaleString('ar-SA')} ر.س</p>
      </div>
      <div style="flex: 1; min-width: 150px; background: linear-gradient(135deg, #fff7ed, #ffedd5); border-radius: 10px; padding: 15px; text-align: center;">
        <p style="font-size: 11px; color: #64748b; margin: 0;">المصروف الفعلي</p>
        <p style="font-size: 20px; font-weight: bold; color: #ea580c; margin: 5px 0 0 0;">${report.total_spent?.toLocaleString('ar-SA')} ر.س</p>
      </div>
      <div style="flex: 1; min-width: 150px; background: linear-gradient(135deg, ${report.total_remaining >= 0 ? '#f0fdf4, #dcfce7' : '#fef2f2, #fee2e2'}); border-radius: 10px; padding: 15px; text-align: center;">
        <p style="font-size: 11px; color: #64748b; margin: 0;">المتبقي</p>
        <p style="font-size: 20px; font-weight: bold; color: ${report.total_remaining >= 0 ? '#16a34a' : '#dc2626'}; margin: 5px 0 0 0;">${report.total_remaining?.toLocaleString('ar-SA')} ر.س</p>
      </div>
      <div style="flex: 1; min-width: 150px; background: linear-gradient(135deg, #f8fafc, #f1f5f9); border-radius: 10px; padding: 15px; text-align: center;">
        <p style="font-size: 11px; color: #64748b; margin: 0;">نسبة الاستهلاك</p>
        <p style="font-size: 20px; font-weight: bold; color: #334155; margin: 5px 0 0 0;">${report.total_estimated > 0 ? Math.round((report.total_spent / report.total_estimated) * 100) : 0}%</p>
      </div>
    </div>

    ${report.over_budget?.length > 0 ? `
      <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px; margin-bottom: 20px;">
        <p style="color: #dc2626; font-weight: bold; margin: 0 0 8px 0;">⚠️ تصنيفات تجاوزت الميزانية (${report.over_budget.length})</p>
        ${report.over_budget.map(cat => `
          <div style="display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px solid #fee2e2;">
            <span>${cat.name} - ${cat.project_name}</span>
            <span style="color: #dc2626; font-weight: bold;">تجاوز: ${Math.abs(cat.remaining)?.toLocaleString('ar-SA')} ر.س</span>
          </div>
        `).join('')}
      </div>
    ` : ''}
    
    <table style="width: 100%; font-size: 11px;">
      <thead>
        <tr>
          <th style="width: 20%;">التصنيف</th>
          <th style="width: 20%;">المشروع</th>
          <th style="width: 15%; text-align: center;">التقديري</th>
          <th style="width: 15%; text-align: center;">الفعلي</th>
          <th style="width: 15%; text-align: center;">المتبقي</th>
          <th style="width: 15%; text-align: center;">الحالة</th>
        </tr>
      </thead>
      <tbody>${categoriesRows}</tbody>
    </table>
    
    <div class="footer">
      <p>نظام إدارة طلبات المواد - تقرير الميزانية</p>
      <p style="margin-top: 5px;">تاريخ التصدير: ${formatDate(new Date().toISOString())}</p>
    </div>
  `;

  printHTML(html, 'تقرير الميزانية');
};

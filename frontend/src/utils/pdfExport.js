import html2pdf from 'html2pdf.js';

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

const generatePDF = async (element, filename, options = {}) => {
  // Wait for fonts to load
  await document.fonts.ready;
  
  const opt = {
    margin: [10, 10, 10, 10],
    filename: filename,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { 
      scale: 2,
      useCORS: true,
      logging: false,
      letterRendering: true,
      allowTaint: true
    },
    jsPDF: { 
      unit: 'mm', 
      format: 'a4', 
      orientation: options.landscape ? 'landscape' : 'portrait'
    }
  };

  await html2pdf().set(opt).from(element).save();
};

const createPDFElement = (html) => {
  const container = document.createElement('div');
  container.innerHTML = html;
  container.style.cssText = `
    position: fixed;
    left: -9999px;
    top: 0;
    width: 210mm;
    background: white;
    font-family: 'Noto Naskh Arabic', 'Cairo', 'Segoe UI', Tahoma, Arial, sans-serif;
    direction: rtl;
    text-align: right;
    unicode-bidi: bidi-override;
  `;
  document.body.appendChild(container);
  return container;
};

const removePDFElement = (element) => {
  if (element && element.parentNode) {
    element.parentNode.removeChild(element);
  }
};

export const exportRequestToPDF = async (request) => {
  const items = Array.isArray(request.items) ? request.items : [];
  const itemsRows = items.map((item, idx) => `
    <tr style="background: ${idx % 2 === 0 ? '#f8fafc' : '#fff'};">
      <td style="padding: 10px; border: 1px solid #e2e8f0; text-align: center; width: 40px;">${idx + 1}</td>
      <td style="padding: 10px; border: 1px solid #e2e8f0;">${item.name || '-'}</td>
      <td style="padding: 10px; border: 1px solid #e2e8f0; text-align: center; width: 80px;">${item.quantity || 0}</td>
      <td style="padding: 10px; border: 1px solid #e2e8f0; text-align: center; width: 80px;">${item.unit || 'قطعة'}</td>
    </tr>
  `).join('');

  const html = `
    <div style="padding: 20px; direction: rtl; text-align: right;">
      <div style="border-bottom: 4px solid #ea580c; padding-bottom: 15px; margin-bottom: 25px; text-align: center;">
        <h1 style="color: #ea580c; font-size: 32px; margin: 0 0 5px 0;">طلب مواد</h1>
        <p style="color: #475569; font-size: 14px; margin: 0;">رقم الطلب: ${request.id?.slice(0, 8).toUpperCase() || '-'}</p>
      </div>
      
      <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
          <tr>
            <td style="padding: 8px 0; width: 50%;"><strong style="color: #64748b;">المشروع:</strong> <span style="color: #1e293b;">${request.project_name || '-'}</span></td>
            <td style="padding: 8px 0;"><strong style="color: #64748b;">تاريخ الطلب:</strong> <span style="color: #1e293b;">${formatDate(request.created_at)}</span></td>
          </tr>
          <tr>
            <td style="padding: 8px 0;"><strong style="color: #64748b;">المشرف:</strong> <span style="color: #1e293b;">${request.supervisor_name || '-'}</span></td>
            <td style="padding: 8px 0;"><strong style="color: #64748b;">المهندس:</strong> <span style="color: #1e293b;">${request.engineer_name || '-'}</span></td>
          </tr>
          <tr>
            <td style="padding: 8px 0;"><strong style="color: #64748b;">الحالة:</strong> <span style="background: #dcfce7; color: #166534; padding: 3px 10px; border-radius: 4px; font-size: 12px;">${getStatusTextAr(request.status)}</span></td>
            <td style="padding: 8px 0;"><strong style="color: #64748b;">سبب الطلب:</strong> <span style="color: #1e293b;">${request.reason || '-'}</span></td>
          </tr>
        </table>
      </div>
      
      <div style="margin-bottom: 25px;">
        <h3 style="color: #ea580c; font-size: 16px; border-bottom: 2px solid #ea580c; padding-bottom: 8px; margin-bottom: 15px;">الأصناف المطلوبة</h3>
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr style="background: #ea580c; color: white;">
              <th style="padding: 12px; border: 1px solid #ea580c; width: 40px;">#</th>
              <th style="padding: 12px; border: 1px solid #ea580c;">اسم المادة</th>
              <th style="padding: 12px; border: 1px solid #ea580c; width: 80px;">الكمية</th>
              <th style="padding: 12px; border: 1px solid #ea580c; width: 80px;">الوحدة</th>
            </tr>
          </thead>
          <tbody>${itemsRows}</tbody>
        </table>
      </div>
      
      ${request.rejection_reason ? `
        <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
          <strong style="color: #dc2626;">سبب الرفض:</strong> <span style="color: #7f1d1d;">${request.rejection_reason}</span>
        </div>
      ` : ''}
      
      <div style="border-top: 2px solid #e2e8f0; padding-top: 20px; margin-top: 30px; text-align: center; color: #64748b; font-size: 11px;">
        <p style="margin: 0;">نظام إدارة طلبات المواد</p>
        <p style="margin: 5px 0 0 0;">تاريخ الطباعة: ${formatDate(new Date().toISOString())}</p>
      </div>
    </div>
  `;

  const element = createPDFElement(html);
  try {
    await generatePDF(element, `طلب_مواد_${request.id?.slice(0, 8) || 'request'}.pdf`);
  } finally {
    removePDFElement(element);
  }
};

export const exportPurchaseOrderToPDF = async (order) => {
  const items = Array.isArray(order.items) ? order.items : [];
  const fontStyle = "font-family: 'Noto Naskh Arabic', 'Cairo', Arial, sans-serif;";
  
  const itemsRows = items.map((item, idx) => `
    <tr style="background: ${idx % 2 === 0 ? '#f8fafc' : '#fff'};">
      <td style="padding: 10px; border: 1px solid #e2e8f0; text-align: center; width: 40px; ${fontStyle}">${idx + 1}</td>
      <td style="padding: 10px; border: 1px solid #e2e8f0; ${fontStyle}">${item.name || '-'}</td>
      <td style="padding: 10px; border: 1px solid #e2e8f0; text-align: center; width: 80px; ${fontStyle}">${item.quantity || 0}</td>
      <td style="padding: 10px; border: 1px solid #e2e8f0; text-align: center; width: 80px; ${fontStyle}">${item.unit || 'قطعة'}</td>
    </tr>
  `).join('');

  const html = `
    <div style="padding: 20px; direction: rtl; text-align: right; ${fontStyle}">
      <div style="border: 4px solid #ea580c; border-radius: 0; padding: 20px; margin-bottom: 25px; text-align: center;">
        <h1 style="color: #ea580c; font-size: 36px; margin: 0 0 10px 0; ${fontStyle}">أمر شراء</h1>
        <p style="color: #1e293b; font-size: 16px; margin: 0; font-weight: bold; ${fontStyle}">رقم الأمر: ${order.id?.slice(0, 8).toUpperCase() || '-'}</p>
        <p style="color: #64748b; font-size: 13px; margin: 5px 0 0 0; ${fontStyle}">رقم الطلب: ${order.request_id?.slice(0, 8).toUpperCase() || '-'}</p>
      </div>
      
      <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
          <tr>
            <td style="padding: 8px 0; width: 50%; ${fontStyle}"><strong style="color: #64748b;">المشروع:</strong> <span style="color: #1e293b;">${order.project_name || '-'}</span></td>
            <td style="padding: 8px 0; ${fontStyle}"><strong style="color: #64748b;">تاريخ الإصدار:</strong> <span style="color: #1e293b;">${formatDate(order.created_at)}</span></td>
          </tr>
          <tr>
            <td style="padding: 8px 0; ${fontStyle}"><strong style="color: #64748b;">المورد:</strong> <span style="background: #dcfce7; color: #166534; padding: 3px 10px; border-radius: 4px;">${order.supplier_name || '-'}</span></td>
            <td style="padding: 8px 0; ${fontStyle}"><strong style="color: #64748b;">مدير المشتريات:</strong> <span style="color: #1e293b;">${order.manager_name || '-'}</span></td>
          </tr>
          <tr>
            <td style="padding: 8px 0; ${fontStyle}"><strong style="color: #64748b;">الحالة:</strong> <span style="background: #dbeafe; color: #1e40af; padding: 3px 10px; border-radius: 4px; font-size: 12px;">${getOrderStatusTextAr(order.status)}</span></td>
            <td style="padding: 8px 0; ${fontStyle}">${order.approved_at ? `<strong style="color: #64748b;">تاريخ الاعتماد:</strong> <span style="color: #1e293b;">${formatDate(order.approved_at)}</span>` : ''}</td>
          </tr>
        </table>
      </div>
      
      <div style="margin-bottom: 25px;">
        <h3 style="color: #ea580c; font-size: 16px; border-bottom: 2px solid #ea580c; padding-bottom: 8px; margin-bottom: 15px; ${fontStyle}">المواد</h3>
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr style="background: #ea580c; color: white;">
              <th style="padding: 12px; border: 1px solid #ea580c; width: 40px; ${fontStyle}">#</th>
              <th style="padding: 12px; border: 1px solid #ea580c; ${fontStyle}">اسم المادة</th>
              <th style="padding: 12px; border: 1px solid #ea580c; width: 80px; ${fontStyle}">الكمية</th>
              <th style="padding: 12px; border: 1px solid #ea580c; width: 80px; ${fontStyle}">الوحدة</th>
            </tr>
          </thead>
          <tbody>${itemsRows}</tbody>
        </table>
      </div>
      
      ${order.notes ? `
        <div style="background: #fffbeb; border: 1px solid #fde68a; padding: 15px; border-radius: 8px; margin-bottom: 25px;">
          <strong style="color: #92400e; ${fontStyle}">ملاحظات:</strong> <span style="color: #78350f; ${fontStyle}">${order.notes}</span>
        </div>
      ` : ''}
      
      <div style="display: flex; justify-content: space-between; margin-top: 60px; padding: 0 30px;">
        <div style="text-align: center; width: 45%;">
          <div style="border-top: 2px solid #94a3b8; padding-top: 10px; margin-top: 50px;">
            <p style="margin: 0; color: #64748b; font-size: 13px; ${fontStyle}">توقيع المورد</p>
          </div>
        </div>
        <div style="text-align: center; width: 45%;">
          <div style="border-top: 2px solid #94a3b8; padding-top: 10px; margin-top: 50px;">
            <p style="margin: 0; color: #64748b; font-size: 13px; ${fontStyle}">توقيع مدير المشتريات</p>
          </div>
        </div>
      </div>
      
      <div style="border-top: 2px solid #e2e8f0; padding-top: 20px; margin-top: 40px; text-align: center; color: #64748b; font-size: 11px;">
        <p style="margin: 0; ${fontStyle}">نظام إدارة طلبات المواد</p>
        <p style="margin: 5px 0 0 0; ${fontStyle}">تاريخ الطباعة: ${formatDate(new Date().toISOString())}</p>
      </div>
    </div>
  `;

  const element = createPDFElement(html);
  try {
    await generatePDF(element, `امر_شراء_${order.id?.slice(0, 8) || 'order'}.pdf`);
  } finally {
    removePDFElement(element);
  }
};

export const exportRequestsTableToPDF = async (requests, title = 'قائمة الطلبات') => {
  const rows = requests.map((r, idx) => {
    const items = Array.isArray(r.items) ? r.items : [];
    const itemsSummary = items.length > 0 
      ? (items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`)
      : '-';
    return `
      <tr style="background: ${idx % 2 === 0 ? '#f8fafc' : '#fff'};">
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${itemsSummary}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.project_name || '-'}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.supervisor_name || '-'}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.engineer_name || '-'}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;"><span style="background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 3px; font-size: 11px;">${getStatusTextAr(r.status)}</span></td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${formatDateShort(r.created_at)}</td>
      </tr>
    `;
  }).join('');

  const html = `
    <div style="padding: 15px; direction: rtl; text-align: right;">
      <h2 style="color: #ea580c; text-align: center; border-bottom: 3px solid #ea580c; padding-bottom: 10px; margin-bottom: 20px;">${title}</h2>
      <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
        <thead>
          <tr style="background: #ea580c; color: white;">
            <th style="padding: 10px; border: 1px solid #ea580c;">الأصناف</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">المشروع</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">المشرف</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">المهندس</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">الحالة</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">التاريخ</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <p style="text-align: center; color: #64748b; font-size: 10px; margin-top: 20px;">
        نظام إدارة طلبات المواد - تاريخ التصدير: ${formatDateShort(new Date().toISOString())}
      </p>
    </div>
  `;

  const element = createPDFElement(html);
  element.style.width = '297mm';
  try {
    await generatePDF(element, `${title.replace(/\s/g, '_')}.pdf`, { landscape: true });
  } finally {
    removePDFElement(element);
  }
};

export const exportPurchaseOrdersTableToPDF = async (orders) => {
  const rows = orders.map((o, idx) => {
    const items = Array.isArray(o.items) ? o.items : [];
    const itemsSummary = items.length > 0 
      ? (items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`)
      : '-';
    return `
      <tr style="background: ${idx % 2 === 0 ? '#f8fafc' : '#fff'};">
        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">${o.id?.slice(0, 8).toUpperCase() || '-'}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${itemsSummary}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${o.project_name || '-'}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;"><span style="background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 3px;">${o.supplier_name || '-'}</span></td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${o.manager_name || '-'}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;"><span style="background: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 3px; font-size: 11px;">${getOrderStatusTextAr(o.status)}</span></td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${formatDateShort(o.created_at)}</td>
      </tr>
    `;
  }).join('');

  const html = `
    <div style="padding: 15px; direction: rtl; text-align: right;">
      <h2 style="color: #ea580c; text-align: center; border-bottom: 3px solid #ea580c; padding-bottom: 10px; margin-bottom: 20px;">قائمة أوامر الشراء</h2>
      <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
        <thead>
          <tr style="background: #ea580c; color: white;">
            <th style="padding: 10px; border: 1px solid #ea580c;">رقم الأمر</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">الأصناف</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">المشروع</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">المورد</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">مدير المشتريات</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">الحالة</th>
            <th style="padding: 10px; border: 1px solid #ea580c;">التاريخ</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <p style="text-align: center; color: #64748b; font-size: 10px; margin-top: 20px;">
        نظام إدارة طلبات المواد - تاريخ التصدير: ${formatDateShort(new Date().toISOString())}
      </p>
    </div>
  `;

  const element = createPDFElement(html);
  element.style.width = '297mm';
  try {
    await generatePDF(element, 'اوامر_الشراء.pdf', { landscape: true });
  } finally {
    removePDFElement(element);
  }
};

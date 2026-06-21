(function () {
  'use strict';

  async function render() {
    var app = window.SahBuktiApp;
    app.setPageTitle('Inventory', 'Track ingredients, supplier notes, and stock pressure.');
    app.setContent('<div class="loading-panel">Loading inventory...</div>');
    try {
      var results = await Promise.all([
        window.SahBuktiApi.get('/inventory/ingredients'),
        window.SahBuktiApi.get('/inventory/suppliers')
      ]);
      var ingredients = results[0] || [];
      var supplierSummary = (results[1] && results[1].suppliers) || [];

      var ingredientCards = ingredients.map(function (item) {
        var low = Number(item.current_stock) <= Number(item.reorder_point);
        return (
          '<article class="list-card">' +
            '<div class="list-card-head"><h4>' + app.escapeHtml(item.name) + '</h4><span class="badge badge-' + (low ? 'overdue' : 'paid') + '">' + (low ? 'low stock' : 'ok') + '</span></div>' +
            '<p>' + app.escapeHtml(item.notes || 'No notes saved') + '</p>' +
            '<div class="list-card-foot"><span>' + app.escapeHtml(String(item.current_stock)) + ' ' + app.escapeHtml(item.unit || 'pcs') + '</span><span>' + app.escapeHtml(item.supplier || 'Unassigned supplier') + '</span></div>' +
          '</article>'
        );
      }).join('') || app.emptyState('No ingredients yet', 'Add ingredients with stock, reorder points, supplier names, and notes for real buying habits.', '#/inventory', 'Add ingredient');

      var supplierCards = supplierSummary.map(function (supplier) {
        var nested = supplier.ingredients.map(function (item) {
          return '<li><strong>' + app.escapeHtml(item.name) + '</strong> · ' + app.escapeHtml(String(item.current_stock)) + ' ' + app.escapeHtml(item.unit || 'pcs') + (item.notes ? ' · ' + app.escapeHtml(item.notes) : '') + '</li>';
        }).join('');
        return (
          '<article class="panel supplier-card">' +
            '<div class="panel-header"><h3>' + app.escapeHtml(supplier.supplier) + '</h3><span class="badge badge-' + (supplier.low_stock_count ? 'overdue' : 'paid') + '">' + app.escapeHtml(String(supplier.low_stock_count)) + ' low</span></div>' +
            '<p>' + app.escapeHtml(String(supplier.ingredient_count)) + ' ingredients tracked</p>' +
            '<ul class="mini-list">' + nested + '</ul>' +
          '</article>'
        );
      }).join('') || app.emptyState('No supplier summary yet', 'Supplier summary appears after ingredients are added.');

      app.setContent(
        '<section class="hero-row">' +
          '<div class="hero-copy-block"><div class="eyebrow">Ingredient ops</div><h2>Stock, supplier notes, and reorder pressure.</h2><p>Keep supplier habits beside ingredients so daily ops is useful, not just numeric.</p></div>' +
          '<div class="metric-grid"><div class="metric-card"><span class="metric-label">Ingredients</span><strong class="metric-value">' + ingredients.length + '</strong></div><div class="metric-card"><span class="metric-label">Suppliers</span><strong class="metric-value">' + supplierSummary.length + '</strong></div><div class="metric-card"><span class="metric-label">Low stock</span><strong class="metric-value">' + ingredients.filter(function (item) { return Number(item.current_stock) <= Number(item.reorder_point); }).length + '</strong></div></div>' +
        '</section>' +
        '<section class="two-column">' +
          '<div class="panel form-panel"><div class="panel-header"><h3>Add ingredient</h3></div><form id="ingredient-form" class="form-grid">' +
            app.inputField('Name', 'name', '', 'text', true) +
            app.inputField('Unit', 'unit', 'pcs') +
            app.inputField('Current stock', 'current_stock', '', 'number', true) +
            app.inputField('Reorder point', 'reorder_point', '', 'number', true) +
            app.inputField('Supplier', 'supplier', '') +
            '<label class="field"><span>Notes</span><textarea class="input textarea" name="notes" rows="3" placeholder="Call supplier every Friday"></textarea></label>' +
            '<div class="form-actions"><button class="btn btn-primary" type="submit">Save Ingredient</button></div>' +
          '</form></div>' +
          '<div class="panel"><div class="panel-header"><h3>Supplier summary</h3></div><div class="card-stack">' + supplierCards + '</div></div>' +
        '</section>' +
        '<section class="panel"><div class="panel-header"><h3>Ingredients</h3></div><div class="card-stack">' + ingredientCards + '</div></section>'
      );

      document.getElementById('ingredient-form').addEventListener('submit', async function (event) {
        event.preventDefault();
        var fd = new FormData(event.target);
        try {
          await window.SahBuktiApi.post('/inventory/ingredients', {
            name: fd.get('name'),
            unit: fd.get('unit') || 'pcs',
            current_stock: Number(fd.get('current_stock')),
            reorder_point: Number(fd.get('reorder_point')),
            supplier: fd.get('supplier') || null,
            notes: fd.get('notes') || null
          });
          app.toast('Ingredient saved');
          render();
        } catch (error) {
          app.toast(error.message, 'danger');
        }
      });
    } catch (error) {
      app.setContent(app.errorState('Inventory unavailable', error.message));
    }
  }

  window.SahBuktiPages = window.SahBuktiPages || {};
  window.SahBuktiPages.inventory = { route: '/inventory', render: render };
})();

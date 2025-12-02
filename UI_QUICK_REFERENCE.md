# 🎨 UI Quick Reference Card

## Color Palette
```css
Primary:  #4F46E5  (Indigo)
Success:  #10B981  (Emerald Green)
Warning:  #F59E0B  (Amber)
Danger:   #EF4444  (Red)
Info:     #3B82F6  (Blue)
```

## Common Components

### Stat Card
```html
<div class="stat-card success">
    <h3>125</h3>
    <p>Total Items</p>
</div>
```
**Variants:** Default, `success`, `warning`, `danger`

### Category Card
```html
<a href="#" class="card category-card h-100">
    <div class="card-body">
        <i class="bi bi-receipt icon"></i>
        <h5>Title</h5>
        <p class="text-muted">Description</p>
    </div>
</a>
```

### Gradient Button
```html
<button class="btn btn-primary">
    <i class="bi bi-plus"></i> Action
</button>
```
**Types:** `btn-primary`, `btn-success`, `btn-warning`, `btn-danger`, `btn-info`

### Alert
```html
<div class="alert alert-success">
    <i class="bi bi-check-circle"></i>
    <strong>Success!</strong> Message here
</div>
```

### Enhanced Card
```html
<div class="card card-accent success">
    <div class="card-header">Header</div>
    <div class="card-body">Content</div>
</div>
```

## CSS Variables
```css
var(--primary-color)
var(--primary-gradient)
var(--shadow-md)
var(--radius-lg)
var(--spacing-md)
```

## Common Icons
```html
<i class="bi bi-speedometer2"></i>  <!-- Dashboard -->
<i class="bi bi-receipt"></i>       <!-- Requisitions -->
<i class="bi bi-cash-stack"></i>    <!-- Treasury -->
<i class="bi bi-clipboard-check"></i> <!-- Approvals -->
<i class="bi bi-building"></i>      <!-- Organization -->
<i class="bi bi-graph-up"></i>      <!-- Reports -->
```

## Utility Classes
- `.hover-lift` - Adds hover elevation
- `.text-gradient` - Gradient text effect
- `.glass-card` - Glassmorphism
- `.loading` - Loading state
- `.skeleton` - Skeleton loader

## Grid Layout
```html
<div class="row g-4">
    <div class="col-md-4">...</div>
    <div class="col-md-4">...</div>
    <div class="col-md-4">...</div>
</div>
```

## JavaScript Functions
```javascript
showToast('Message', 'success');
animateValue(element, 0, 100, 1000);
```

## File Locations
- CSS: `/static/styles.css`
- JS: `/static/js/animations.js`
- Base: `/templates/base.html`
- Examples: `UI_COMPONENTS_EXAMPLES.html`
- Guide: `UI_DESIGN_GUIDE.md`

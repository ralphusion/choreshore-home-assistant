
class ChoreShoreTasks extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this.config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  render() {
    if (!this._hass || !this.config) return;

    const tasks = this.getTasks();
    const maxTasks = this.config.max_tasks || 10;
    const showCompleted = this.config.show_completed || false;

    this.shadowRoot.innerHTML = `
      <style>
        .card {
          background: var(--card-background-color);
          border-radius: var(--border-radius);
          box-shadow: var(--box-shadow);
          padding: 16px;
          margin: 8px 0;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }
        .title {
          font-size: 1.2em;
          font-weight: bold;
          color: var(--primary-text-color);
        }
        .task-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid var(--divider-color);
        }
        .task-item:last-child {
          border-bottom: none;
        }
        .task-info {
          flex: 1;
        }
        .task-name {
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .task-details {
          font-size: 0.9em;
          color: var(--secondary-text-color);
        }
        .task-actions {
          display: flex;
          gap: 8px;
        }
        .action-button {
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          padding: 4px 8px;
          cursor: pointer;
          font-size: 0.8em;
        }
        .action-button:hover {
          opacity: 0.8;
        }
        .action-button.skip {
          background: var(--warning-color);
        }
        .status-overdue {
          color: var(--error-color);
        }
        .status-completed {
          color: var(--success-color);
          opacity: 0.7;
        }
        .no-tasks {
          text-align: center;
          color: var(--secondary-text-color);
          padding: 20px;
        }
      </style>
      <div class="card">
        <div class="header">
          <div class="title">ChoreShore Tasks</div>
          <div class="refresh-button">
            <button class="action-button" onclick="this.refreshData()">Refresh</button>
          </div>
        </div>
        <div class="tasks">
          ${tasks.length === 0 ? '<div class="no-tasks">No tasks available</div>' : 
            tasks.slice(0, maxTasks).map(task => this.renderTask(task)).join('')}
        </div>
      </div>
    `;
  }

  getTasks() {
    if (!this._hass) return [];
    
    const taskEntities = Object.keys(this._hass.states)
      .filter(entityId => entityId.startsWith('binary_sensor.choreshore_') && 
                         entityId.includes('_task_'))
      .map(entityId => this._hass.states[entityId])
      .filter(entity => entity && entity.attributes);

    return taskEntities.sort((a, b) => {
      const aOverdue = a.attributes.is_overdue;
      const bOverdue = b.attributes.is_overdue;
      if (aOverdue && !bOverdue) return -1;
      if (!aOverdue && bOverdue) return 1;
      return 0;
    });
  }

  renderTask(task) {
    const attrs = task.attributes;
    const isOverdue = attrs.is_overdue;
    const isCompleted = attrs.status === 'completed';
    const statusClass = isCompleted ? 'status-completed' : isOverdue ? 'status-overdue' : '';

    return `
      <div class="task-item ${statusClass}">
        <div class="task-info">
          <div class="task-name">${attrs.chore_name || 'Unknown Task'}</div>
          <div class="task-details">
            ${attrs.assigned_to || 'Unassigned'} • 
            ${attrs.due_date || 'No due date'}
            ${attrs.due_time ? ` at ${attrs.due_time}` : ''}
            ${attrs.category ? ` • ${attrs.category}` : ''}
          </div>
        </div>
        ${!isCompleted ? `
          <div class="task-actions">
            <button class="action-button" onclick="this.completeTask('${attrs.task_id}')">
              Complete
            </button>
            <button class="action-button skip" onclick="this.skipTask('${attrs.task_id}')">
              Skip
            </button>
          </div>
        ` : ''}
      </div>
    `;
  }

  completeTask(taskId) {
    this._hass.callService('choreshore', 'complete_task', { task_id: taskId });
  }

  skipTask(taskId) {
    const reason = prompt('Reason for skipping (optional):');
    const serviceData = { task_id: taskId };
    if (reason) serviceData.reason = reason;
    this._hass.callService('choreshore', 'skip_task', serviceData);
  }

  refreshData() {
    this._hass.callService('choreshore', 'refresh_data');
  }

  getCardSize() {
    return 3;
  }
}

class ChoreShoreAnalytics extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this.config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  render() {
    if (!this._hass || !this.config) return;

    const analytics = this.getAnalytics();

    this.shadowRoot.innerHTML = `
      <style>
        .card {
          background: var(--card-background-color);
          border-radius: var(--border-radius);
          box-shadow: var(--box-shadow);
          padding: 16px;
          margin: 8px 0;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }
        .title {
          font-size: 1.2em;
          font-weight: bold;
          color: var(--primary-text-color);
        }
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 16px;
        }
        .metric {
          text-align: center;
          padding: 16px;
          background: var(--secondary-background-color);
          border-radius: var(--border-radius);
        }
        .metric-value {
          font-size: 2em;
          font-weight: bold;
          color: var(--primary-color);
        }
        .metric-label {
          font-size: 0.9em;
          color: var(--secondary-text-color);
          margin-top: 4px;
        }
        .completion-rate {
          color: var(--success-color);
        }
        .overdue-count {
          color: var(--error-color);
        }
      </style>
      <div class="card">
        <div class="header">
          <div class="title">ChoreShore Analytics</div>
        </div>
        <div class="metrics-grid">
          <div class="metric">
            <div class="metric-value">${analytics.totalTasks}</div>
            <div class="metric-label">Total Tasks</div>
          </div>
          <div class="metric">
            <div class="metric-value">${analytics.completedTasks}</div>
            <div class="metric-label">Completed</div>
          </div>
          <div class="metric">
            <div class="metric-value overdue-count">${analytics.overdueTasks}</div>
            <div class="metric-label">Overdue</div>
          </div>
          <div class="metric">
            <div class="metric-value completion-rate">${analytics.completionRate}%</div>
            <div class="metric-label">Completion Rate</div>
          </div>
        </div>
      </div>
    `;
  }

  getAnalytics() {
    if (!this._hass) return { totalTasks: 0, completedTasks: 0, overdueTasks: 0, completionRate: 0 };

    const totalTasks = this._hass.states['sensor.choreshore_total_tasks']?.state || 0;
    const completedTasks = this._hass.states['sensor.choreshore_completed_tasks']?.state || 0;
    const overdueTasks = this._hass.states['sensor.choreshore_overdue_tasks']?.state || 0;
    const completionRate = this._hass.states['sensor.choreshore_completion_rate']?.state || 0;

    return {
      totalTasks: parseInt(totalTasks),
      completedTasks: parseInt(completedTasks),
      overdueTasks: parseInt(overdueTasks),
      completionRate: parseFloat(completionRate).toFixed(1)
    };
  }

  getCardSize() {
    return 2;
  }
}

// Register the custom cards
customElements.define('choreshore-tasks', ChoreShoreTasks);
customElements.define('choreshore-analytics', ChoreShoreAnalytics);

// Register cards with Home Assistant
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'choreshore-tasks',
  name: 'ChoreShore Tasks',
  description: 'Display and manage ChoreShore tasks'
});
window.customCards.push({
  type: 'choreshore-analytics',
  name: 'ChoreShore Analytics',
  description: 'Display ChoreShore analytics and metrics'
});

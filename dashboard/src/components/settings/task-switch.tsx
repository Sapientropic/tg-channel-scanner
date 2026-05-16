export type SettingsTask = "sources" | "ai" | "notifications" | "learning" | "updates" | "support";

export function SettingsTaskSwitch({
  activeTask,
  sourceCount,
  sourceDetail,
  aiCount,
  notificationCount,
  feedbackCount,
  updateCount,
  supportCount,
  onSelect,
}: {
  activeTask: SettingsTask;
  sourceCount: number;
  sourceDetail?: string;
  aiCount: number;
  notificationCount: number;
  feedbackCount: number;
  updateCount: number;
  supportCount: number;
  onSelect: (task: SettingsTask) => void;
}) {
  const primaryTasks: Array<{ id: SettingsTask; label: string; count: number; detail: string }> = [
    { id: "sources", label: "Sources", count: sourceCount, detail: sourceDetail || "Tracked channels" },
    { id: "ai", label: "AI API", count: aiCount, detail: "Matching and image reading" },
    { id: "notifications", label: "Alerts", count: notificationCount, detail: "Where alerts go" },
    {
      id: "learning",
      label: "Learning",
      count: feedbackCount,
      detail: feedbackCount > 0 ? "Use Review choices" : "Review cards to teach preferences",
    },
  ];
  const advancedTasks: Array<{ id: SettingsTask; label: string; count: number; detail: string }> = [
    { id: "updates", label: "Updates", count: updateCount, detail: updateCount > 0 ? "New app version" : "App version" },
    { id: "support", label: "Help", count: supportCount, detail: "Diagnostics and recovery" },
  ];
  return (
    <div className="settings-task-switch-wrap" aria-label="Settings task switcher">
      <div className="settings-task-switch">
        {primaryTasks.map((task) => (
          <SettingsTaskButton activeTask={activeTask} key={task.id} onSelect={onSelect} task={task} />
        ))}
      </div>
      <details className="settings-advanced-switch" open={activeTask === "updates" || activeTask === "support"}>
        <summary>
          <span>Advanced</span>
          <small>Updates and diagnostics</small>
        </summary>
        <div className="settings-task-switch advanced">
          {advancedTasks.map((task) => (
            <SettingsTaskButton activeTask={activeTask} key={task.id} onSelect={onSelect} task={task} />
          ))}
        </div>
      </details>
    </div>
  );
}

function SettingsTaskButton({
  activeTask,
  onSelect,
  task,
}: {
  activeTask: SettingsTask;
  onSelect: (task: SettingsTask) => void;
  task: { id: SettingsTask; label: string; count: number; detail: string };
}) {
  return (
    <button
      aria-pressed={activeTask === task.id}
      data-empty={task.count === 0 ? "true" : "false"}
      onClick={() => onSelect(task.id)}
      type="button"
    >
      <span>{task.label}</span>
      <strong>{task.count}</strong>
      <small>{task.detail}</small>
    </button>
  );
}

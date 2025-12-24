import { useParams } from 'react-router-dom'

export function TasksPage() {
  const { projectId } = useParams<{ projectId: string }>()

  return (
    <div className="page-content">
      <h2>Tasks</h2>
      <p>Tasks for project: {projectId}</p>
    </div>
  )
}

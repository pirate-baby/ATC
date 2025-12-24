import { useParams } from 'react-router-dom'

export function PlansPage() {
  const { projectId } = useParams<{ projectId: string }>()

  return (
    <div className="page-content">
      <h2>Plans</h2>
      <p>Plans for project: {projectId}</p>
    </div>
  )
}

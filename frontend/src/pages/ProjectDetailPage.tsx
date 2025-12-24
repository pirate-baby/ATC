import { useParams } from 'react-router-dom'

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()

  return (
    <div className="page-content">
      <h2>Project Details</h2>
      <p>Project ID: {projectId}</p>
    </div>
  )
}

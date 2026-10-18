import Head from "next/head"
import { useEffect, useState } from "react"
import axios from "axios"

interface Recommendation {
  item_id: string
  title: string
  score: number
  reasons: string[]
  metadata: any
}

interface RecommendationsResponse {
  recommendations: Recommendation[]
  explanation: any
  request_id: string
}

export default function Home() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [userContext, setUserContext] = useState({ user_id: 12345 })

  useEffect(() => {
    fetchRecommendations()
  }, [])

  const fetchRecommendations = async () => {
    try {
      setLoading(true)
      const response = await axios.post<RecommendationsResponse>(
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/v1/recommend",
        {
          user_id: userContext.user_id,
          num_results: 20,
          context: {
            device_type: "web",
            time_of_day: "evening"
          }
        }
      )
      setRecommendations(response.data.recommendations)
    } catch (error) {
      console.error("Error fetching recommendations:", error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <Head>
        <title>Recommendation Engine Dashboard</title>
        <meta name="description" content="Netflix-Scale Recommendation Platform" />
      </Head>

      <nav className="bg-purple-600 p-4">
        <div className="container mx-auto flex justify-between items-center text-white">
          <h1 className="text-xl font-bold">🎬 Recommendation Engine</h1>
          <div className="space-x-4">
            <span className="text-sm">User: {userContext.user_id}</span>
            <button
              onClick={fetchRecommendations}
              disabled={loading}
              className="bg-white text-purple-600 px-4 py-2 rounded hover:bg-gray-100 disabled:opacity-50"
            >
              {loading ? "Loading..." : "Refresh"}
            </button>
          </div>
        </div>
      </nav>

      <main className="container mx-auto p-6">
        <h2 className="text-2xl font-bold text-white mb-6">Personalized Recommendations</h2>
        
        {loading && (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-purple-600"></div>
          </div>
        )}

        {!loading && recommendations.length === 0 && (
          <div className="text-center text-gray-400 py-20">
            <p className="text-xl">No recommendations available</p>
            <button
              onClick={fetchRecommendations}
              className="mt-4 bg-purple-600 text-white px-6 py-2 rounded hover:bg-purple-700"
            >
              Generate Recommendations
            </button>
          </div>
        )}

        {!loading && recommendations.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {recommendations.map((rec, index) => (
              <div key={rec.item_id} className="bg-gray-800 rounded-lg overflow-hidden shadow-lg hover:shadow-xl transition-shadow duration-300">
                <div className="p-6">
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="text-xl font-semibold text-white">{rec.title}</h3>
                    <span className="bg-purple-600 text-white px-3 py-1 rounded-full text-sm">
                      {(rec.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  
                  <div className="mb-4">
                    <p className="text-sm text-gray-400 mb-2">Reasons:</p>
                    <ul className="space-y-1">
                      {rec.reasons.map((reason, idx) => (
                        <li key={idx} className="text-sm text-gray-300">
                          • {reason}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-700">
                    <span className="text-xs text-gray-400">
                      {rec.metadata?.genre?.join(", ") || "Unknown genre"}
                    </span>
                    <button className="text-purple-400 hover:text-purple-300 text-sm">
                      View Details →
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

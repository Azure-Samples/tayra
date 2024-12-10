"use client";
import React, { useState, useEffect } from 'react';
import Modal from 'react-modal';
import { BACK_URL, evaluateApi } from '@/utils/api';
import { useHumanEvaluation } from '@/utils/humanEvalContext';
import { Transcription as TranscriptionType } from '@/types/transcription';

interface TranscriptionFileProps {
  transcription: TranscriptionType;
}

interface EvalApiResponse {
  evaluations: {
    classification: string;
    overallScore: number;
    improvementSuggestion: string;
    criteria: {
      name: string;
      score: number;
      rationale: string;
      sub_criteria: {
        name: string;
        score: number;
        rationale: string;
      }[];
    }[];
  }[];
}

const promptData = [
  {
    label: 'Closing',
    value: 'closing',
    defaultPrompt: `Did the investment advisor properly close the call by asking the client if they needed any additional assistance or had further questions?
If the advisor ended the call informally but courteously and attentively, consider it as if they asked the client. Assign a score of 1 if all recommendations were followed and 0 otherwise.
In the JSON structure, consider the item as "Closing" and the sub-item as "Asked if client needed any further assistance or had questions."`,
  },
];

const Transcription: React.FC<TranscriptionFileProps> = ({ transcription }) => {
  const { filename, successfulCall, classification, content } = transcription;
  const { humanEvaluation, updateHumanEvaluation } = useHumanEvaluation();

  const [isEvaluationModalOpen, setIsEvaluationModalOpen] = useState(false);
  const [isTranscriptionModalOpen, setIsTranscriptionModalOpen] = useState(false);
  const [evalApiResponse, setEvalApiResponse] = useState<EvalApiResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true); // Track loading state
  const [selectedPrompt, setSelectedPrompt] = useState(promptData[0].defaultPrompt);
  const [selectedTopic, setSelectedTopic] = useState(promptData[0].value);
  const [improvedTranscription, setImprovedTranscription] = useState<string>(content);

  useEffect(() => {
    const fetchEvaluationData = async () => {
      setIsLoading(true);
      try {
        const response = await evaluateApi.get(`/specialist-evaluation?transcription_id=${transcription.id}`);
        if (response?.data?.result?.length > 0) {
          const evaluations = response.data.result.map((result: any) => ({
            classification: result.evaluation.evaluation.classification,
            overallScore: result.evaluation.evaluation.overall_score,
            improvementSuggestion: result.evaluation.evaluation.improvement_suggestion,
            criteria: result.evaluation.evaluation.criteria,
          }));
          setEvalApiResponse({ evaluations });
        }
      } catch (error) {
        console.error("Failed to fetch evaluation data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchEvaluationData();
  }, [transcription.id]);

  const handlePromptChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = promptData.find((item) => item.value === e.target.value);
    if (selected) {
      setSelectedTopic(selected.value);
      setSelectedPrompt(selected.defaultPrompt);
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setSelectedPrompt(e.target.value);
  };

  const handleEvaluationSubmit = async () => {
    try {
      const res = await fetch(`${BACK_URL}/unitary-evaluation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tipo: selectedTopic,
          prompt: selectedPrompt,
          transcription: content,
        }),
      });

      if (!res.ok) {
        throw new Error('Erro ao enviar a avaliação');
      }

      const data = await res.json();
      console.log(data)
  
      setEvalApiResponse(data);

      alert('Análise feita com sucesso!');
  
    } catch (error) {
      console.error('Erro ao submeter o prompt:', error);
      alert('Erro ao submeter o prompt :(');
    }
  };

  const handleImprovement = async () => {
    try {
      const res = await fetch(`${BACK_URL}/transcription-improvement`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transcription_data: content, // The transcription content
        }),
      });

      if (!res.ok) {
        throw new Error('Erro ao enviar a avaliação');
      }

      const data = await res.json();
      console.log(data)
  
      setImprovedTranscription(data);
  
    } catch (error) {
      console.error('Erro ao submeter o prompt:', error);
      alert('Erro ao submeter o prompt :(');
    }
  };

  const closeEvaluationModal = () => setIsEvaluationModalOpen(false);
  const closeTranscriptionModal = () => {
    setImprovedTranscription(content); // Reset to original content
    setIsTranscriptionModalOpen(false);
  };

  const downloadAudio = async () => {
    try {
      const response = await fetch(`${BACK_URL}/stream-audio?audio_name=${encodeURIComponent(filename)}`);

      if (!response.ok) {
        throw new Error('Failed to fetch audio');
      }

      const blob = await response.blob();

      const downloadLink = document.createElement('a');
      const url = URL.createObjectURL(blob);
      downloadLink.href = url;
      downloadLink.download = filename.replace('.txt', blob.type === 'audio/mpeg' ? '.mp3' : '.wav');
      downloadLink.click();
      URL.revokeObjectURL(url); // Clean up URL after the download
    } catch (error) {
      console.error('Error downloading audio:', error);
    }
  };

  const renderEvaluationTable = () => (
    <div className="mt-8">
      <h4 className="text-lg font-bold mb-2 text-black dark:text-white">Evaluation Results</h4>
      {evalApiResponse?.evaluations.map((evaluation, evalIndex) => (
        <div key={evalIndex} className="mb-8">
          <h5 className="text-md font-semibold mb-2 text-blue-600 dark:text-blue-300">
            Evaluation {evalIndex + 1}: {evaluation.classification}
          </h5>
          <table className="table-auto w-full text-left text-gray-800 dark:text-gray-300 border-collapse">
            <thead>
              <tr>
                <th className="border-b-2 p-2">Criteria</th>
                <th className="border-b-2 p-2">Score</th>
                <th className="border-b-2 p-2">Rationale</th>
              </tr>
            </thead>
            <tbody>
              {evaluation.criteria.map((criterion, index) => (
                <React.Fragment key={index}>
                  <tr className="bg-gray-100 dark:bg-gray-700">
                    <td className="border-b p-2 font-bold">{criterion.name}</td>
                    <td className="border-b p-2 font-bold">{criterion.score}</td>
                    <td className="border-b p-2 font-bold">{criterion.rationale}</td>
                  </tr>
                  {criterion.sub_criteria.map((subCriterion, subIndex) => (
                    <tr key={`${index}-${subIndex}`}>
                      <td className="border-b p-2 pl-6">{subCriterion.name}</td>
                      <td className="border-b p-2">{subCriterion.score}</td>
                      <td className="border-b p-2">{subCriterion.rationale}</td>
                    </tr>
                  ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
          <p className="mt-4 text-gray-700 dark:text-gray-400">
            <strong>Improvement Suggestion:</strong> {evaluation.improvementSuggestion}
          </p>
        </div>
      ))}
    </div>
  );

  // Render a loading message while data is being fetched
  if (isLoading) {
    return <p className="text-gray-500 dark:text-gray-400">Loading transcription data...</p>;
  }

  return (
    <div className="p-8 bg-white dark:bg-gray-900 w-full mx-auto mt-16">
      <h4 className="text-xl font-bold mb-4 text-black dark:text-white">Transcription Details - {transcription.id}</h4>
      <div className="mb-4 text-gray-800 dark:text-gray-300">
        <p>Successful Call: {successfulCall ? "Yes" : "No"}</p>
        <p>Classification: {classification}</p>
        <p>Filename: {filename}</p>
      </div>
      <div className="mt-8">
      {evalApiResponse && renderEvaluationTable()}
    </div>
      <button onClick={downloadAudio} className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">Download Audio</button>
      <button onClick={() => setIsEvaluationModalOpen(true)} className="mt-4 ml-4 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600">Prompt Evaluation</button>
      <button onClick={() => setIsTranscriptionModalOpen(true)} className="mt-4 ml-4 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600">Optimize Transcription</button>

      <Modal
        isOpen={isEvaluationModalOpen}
        onRequestClose={closeEvaluationModal}
        ariaHideApp={false}
        className="p-8 bg-white dark:bg-gray-900 rounded-lg shadow-lg w-150 mx-auto mt-16 max-h-[80vh] overflow-y-auto"
        overlayClassName="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center"
      >
        <h4 className="text-xl font-bold">Prompt Evaluation</h4>
        <select value={selectedTopic} onChange={handlePromptChange} className="w-full p-2 mt-4">
          {promptData.map((item) => (
            <option key={item.value} value={item.value}>{item.label}</option>
          ))}
        </select>
        <textarea value={selectedPrompt} onChange={handleTextareaChange} className="w-full h-40 mt-4 p-2" />
        <button onClick={handleEvaluationSubmit} className="mt-4 bg-green-500 px-4 py-2 text-white rounded">Evaluate</button>
        {evalApiResponse && renderEvaluationTable()}
      </Modal>

      <Modal
        isOpen={isTranscriptionModalOpen}
        onRequestClose={closeTranscriptionModal}
        ariaHideApp={false}
        contentLabel="Otimização de Transcrições"
        className="p-8 bg-white dark:bg-gray-900 rounded-lg shadow-lg w-150 mx-auto mt-16 max-h-[80vh] overflow-y-auto"
        overlayClassName="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center"
      >
        <h4 className="text-xl font-bold">Optimize Transcription</h4>
        <textarea value={improvedTranscription} readOnly className="w-full h-40 mt-4 p-2" />
        <button onClick={handleImprovement} className="mt-4 bg-green-500 px-4 py-2 text-white rounded">Optimize</button>
      </Modal>
    </div>
  );
};

export default Transcription;

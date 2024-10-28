"use client";
import React, { useState } from 'react';
import { Transcription as TranscriptionType } from '@/types/transcription';
import Modal from 'react-modal';
import { BACK_URL } from '@/utils/api';
import { useHumanEvaluation } from '@/utils/humanEvalContext';

interface TranscriptionFileProps {
  transcription: TranscriptionType;
}

const Transcription: React.FC<TranscriptionFileProps> = ({ transcription }) => {

  interface EvalApiResponse {
    item: string;
    descricao: string;
    score: number;
    justificativa: string;
    'sub-item'?: {
      'sub-item': string;
      descricao: string;
      score: number;
      justificativa: string;
    }[];
  }

  const promptData = [
    { 
      label: 'Encerramento',
      value: 'closing',
      defaultPrompt: 'O assessor de investimentos encerrou adequadamente a chamada questionando o cliente se ajuda com algo mais ou se ficou alguma dúvida? \n\
Caso o assessor tenha encerrado informalmente a chamada mas sendo cordial e educado e atento caso o cliente ainda tenha dúvidas, considere como se o assessor tivesse questionado o cliente. \n\
Atribua score 1 caso tenha seguido todas as recomendações e zero caso não. \n\
Na estrutura JSON. Considere o item como "Encerramento" e o sub-item como "Questionou o cliente se ajuda com algo mais ou se ficou alguma dúvida"'
    }
  ];

  const { filename, successfulCall, identifiedClient, classification, summaryData, improvementSugestion, content } = transcription;
  
  const { humanEvaluation, updateHumanEvaluation } = useHumanEvaluation();

  const [isEvaluationModalOpen, setEvaluationIsModalOpen] = useState(false);
  const [isTranscriptionModalOpen, setTranscriptionIsModalOpen] = useState(false);
  
  const [evalApiResponse, setEvalApiResponse] = useState<EvalApiResponse>();

  const [selectedPrompt, setSelectedPrompt] = useState(promptData[0].defaultPrompt);
  const [selectedTopic, setSelectedTopic] = useState(promptData[0].value);
  const [improvedTranscrption, setImprovedTranscription] = useState<string>(content);

  const handlePromptChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedTopic(e.target.value);
    const selected = promptData.find((item) => item.value === selectedTopic);
    if (selected) {
      setSelectedPrompt(selected.defaultPrompt); // Set the selected prompt's default prompt text
    }
  };

  // Handle form input changes
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setSelectedPrompt(e.target.value); // Update the textarea as user types
  };

  // Handle form submission
  const handleEvaluationSubmit = async () => {
    try {
      // Prepare the data for submission
      const res = await fetch(`${BACK_URL}/unitary-evaluation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tipo: selectedTopic,   // Use the selected topic from the select dropdown
          prompt: selectedPrompt,  // Use the current prompt in the textarea
          transcription: content, // The transcription content
        }),
      });

      if (!res.ok) {
        throw new Error('Erro ao enviar a avaliação');
      }

      const data = await res.json();
      console.log(data)
  
      setEvalApiResponse(data);
  
      // Show success message
      alert('Análise feita com sucesso!');
  
    } catch (error) {
      console.error('Erro ao submeter o prompt:', error);
      alert('Erro ao submeter o prompt :(');
    }
  };

  // Handle form submission
  const handleImprovement = async () => {
    try {
      // Prepare the data for submission
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

  // Close evaluation modal
  const closeEvaluationModal = () => setEvaluationIsModalOpen(false);
  const closeTranscriptionModal = () => {
    setImprovedTranscription(content);
    setTranscriptionIsModalOpen(false);
  }

  // Function to download the audio file
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

  return (
    <div className="p-8 bg-white dark:bg-gray-900 w-full mx-auto mt-16">

      <h4 className="text-xl font-bold mb-4 text-black dark:text-white">Detalhes da Transcrição - {transcription.id}</h4>
      <div className="mb-4">
      <h4 className="text-lg font-bold mb-2 text-black dark:text-white">Dados da Ligação</h4>
      <p className="text-gray-800 dark:text-gray-300">Ligação Válida: {successfulCall}</p>
      <p className="text-gray-800 dark:text-gray-300">Cliente Identificado: {identifiedClient}</p>
      <p className="text-gray-800 dark:text-gray-300">Classificação: {classification}</p>
      </div>

      <div className="mb-4">
      <h4 className="text-lg font-bold mb-2 text-black dark:text-white">Metadados da Ligação</h4>
      <p className="text-gray-800 dark:text-gray-300">Nome do Arquivo de Transcrição: {filename}</p>
      <p className="text-gray-800 dark:text-gray-300">Nome do Arquivo de Audio: {filename}</p>
      </div>

      <div className="mt-4">
      <h4 className="text-lg font-bold mb-2 text-black dark:text-white">Performance Avaliada</h4>
      <table className="table-auto w-full text-left text-gray-800 dark:text-gray-300 border-collapse">
        <thead>
        <tr>
          <th className="border-b-2 p-2">Item</th>
          <th className="border-b-2 p-2">Sub-Item</th>
          <th className="border-b-2 p-2">Avaliação IA</th>
          <th className="border-b-2 p-2">Justificativa</th>
          <th className="border-b-2 p-2">Avaliação Humana</th>
        </tr>
        </thead>
        <tbody>
        {Object.entries(summaryData).map(([item, data], index) => (
          <tr key={index}>
          <td className="border-b p-2">{data["item"]}</td>
          <td className="border-b p-2">{data["sub-item"]}</td>
          <td className="border-b p-2">{data.peso}</td>
          <td className="border-b p-2">{data.justificativa}</td>
          <td className="border-b p-2">
            <input
            type="number"
            min="0"
            max="10"
            value={humanEvaluation[item] || ''}
            onChange={(e) => updateHumanEvaluation(item, Number(e.target.value))}
            className="p-1 border border-gray-300 rounded w-full"
            />
          </td>
          </tr>
        ))}
        </tbody>
      </table>
      </div>

      <div className="my-4">
      <h4 className="text-lg font-bold mb-2 text-black dark:text-white">Sugestões de Melhoria</h4>
      <p className="text-gray-800 dark:text-gray-300">{improvementSugestion}</p>
      </div>

      <div className="mt-4">
      <h4 className="text-lg font-bold mb-2 text-black dark:text-white">Conteúdo da Transcrição</h4>
      <div className="h-64 overflow-y-auto border border-gray-300 p-2 text-gray-800 dark:text-gray-300">
        <p>{content}</p>
      </div>
      </div>

      <button
      onClick={downloadAudio}
      className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
      >
      Baixar Áudio
      </button>

      <button
      onClick={() => setEvaluationIsModalOpen(true)}
      className="mt-4 ml-4 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
      >
      Avaliação de Prompts
      </button>

      <button
      onClick={() => setTranscriptionIsModalOpen(true)}
      className="mt-4 ml-4 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
      >
      Melhoria da Transcrição
      </button>

      <Modal
      isOpen={isEvaluationModalOpen}
      onRequestClose={closeEvaluationModal}
      ariaHideApp={false}
      contentLabel="Avaliação de Prompts"
      className="p-8 bg-white dark:bg-gray-900 rounded-lg shadow-lg w-150 mx-auto mt-16 max-h-[80vh] overflow-y-auto"
      overlayClassName="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center"
      >
      <h4 className="text-xl font-bold mt-4 mb-2 text-black">Avaliação de Prompts</h4>
      <div className="overflow-y-auto max-h-[70vh]">
        <div className="mb-4">
        <label className="block text-black dark:text-white mb-2" htmlFor="prompts">Tarefa para Avaliar</label>
        <select
          id="questionType"
          value={selectedTopic}
          onChange={(e) => handlePromptChange(e as any)}
          className="w-full p-2 bg-gray-800 border border-gray-600 rounded-lg text-black dark:text-white"
        >
          {promptData.map((item, index) => (
          <option key={index} value={item.value}>
            {item.label}
          </option>
          ))}
        </select>
        <label className="block text-black dark:text-white mt-4 mb-2" htmlFor="prompts">Prompt de Avaliação</label>
        <textarea
          id="questionPrompt"
          value={selectedPrompt}
          onChange={(e) => handleTextareaChange(e as any)}
          className="w-full h-50 p-2 bg-gray-800 border border-gray-600 rounded-lg text-black dark:text-white"
        >
        </textarea>
        </div>
      </div>

      <div className="mt-4 flex justify-between">
        <button
        onClick={handleEvaluationSubmit}
        className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
        Avaliar
        </button>
        <button
        onClick={closeEvaluationModal}
        className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
        >
        Fechar
        </button>
      </div>
      <div>
      {/* Exibição da tabela de resultados após a resposta da API */}
      {evalApiResponse && (
        <div className="mt-8">
        <h4 className="text-lg font-bold mb-2 text-black dark:text-white">Resultados da Avaliação</h4>
        <table className="table-auto w-full text-left text-gray-800 dark:text-gray-300 border-collapse">
          <thead>
          <tr>
            <th className="border-b-2 p-2">Item</th>
            <th className="border-b-2 p-2">Descrição</th>
            <th className="border-b-2 p-2">Pontuação</th>
            <th className="border-b-2 p-2">Justificativa</th>
          </tr>
          </thead>
          <tbody>
          {/* Exibir o item principal */}
          <tr>
            <td className="border-b p-2"><strong>{evalApiResponse.item}</strong></td>
            <td className="border-b p-2">{evalApiResponse.descricao}</td>
            <td className="border-b p-2">{evalApiResponse.score}</td>
            <td className="border-b p-2">{evalApiResponse.justificativa}</td>
          </tr>

          {Array.isArray(evalApiResponse['sub-item']) && evalApiResponse['sub-item'].map((subItem, subIndex) => (
            <tr key={subIndex}>
            <td className="border-b p-2 pl-8">{subItem['sub-item']}</td>
            <td className="border-b p-2">{subItem.descricao}</td>
            <td className="border-b p-2">{subItem.score}</td>
            <td className="border-b p-2">{subItem.justificativa}</td>
            </tr>
          ))}
          </tbody>
        </table>
        </div>
      )}
      </div>
      </Modal>
      <Modal
      isOpen={isTranscriptionModalOpen}
      onRequestClose={closeTranscriptionModal}
      ariaHideApp={false}
      contentLabel="Otimização de Transcrições"
      className="p-8 bg-white dark:bg-gray-900 rounded-lg shadow-lg w-150 mx-auto mt-16 max-h-[80vh] overflow-y-auto"
      overlayClassName="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center"
      >
      <h4 className="text-xl font-bold mt-4 mb-2 text-black">Otimização de Transcrições</h4>
      <div className="overflow-y-auto max-h-[70vh]">
        <div className="mb-4">
        <textarea
          id="questionPrompt"
          value={improvedTranscrption}
          className="w-full h-50 p-2 bg-gray-800 border border-gray-600 rounded-lg text-black dark:text-white"
          contentEditable={false}
        >
        </textarea>
        </div>
      </div>

      <div className="mt-4 flex justify-between">
        <button
        onClick={handleImprovement}
        className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
        Otimizar
        </button>
        <button
        onClick={closeTranscriptionModal}
        className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
        >
        Fechar
        </button>
      </div>
      </Modal>
    </div>
    );
};

export default Transcription;

"use client";
import { useState } from "react";
import api from "@/utils/api"; // Import the configured axios instance

const UploadFile: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [destinationContainer, setDestinationContainer] = useState<string>("audio-files");
  const [runTranscription, setRunTranscription] = useState<boolean>(true);
  const [runEvaluationFlow, setRunEvaluationFlow] = useState<boolean>(true);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile) {
      setUploadStatus("Por favor, selecione um arquivo primeiro.");
      return;
    }

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      // Add parameters for UploadJobParams
      const params = {
        destination_container: destinationContainer,
        run_transcription: runTranscription,
        run_evaluation_flow: runEvaluationFlow,
      };

      // Append params as a JSON string
      formData.append("params", JSON.stringify(params));

      setUploadStatus("Enviando arquivo...");

      const response = await api.post("/audio-upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      if (response.status === 200) {
        setUploadStatus("Arquivo enviado com sucesso!");
      } else {
        setUploadStatus(`Ocorreu um erro ao enviar o arquivo: ${response?.data?.detail}`);
      }
    } catch (error) {
      const errorMessage = (error as any)?.response?.data?.detail || (error as any)?.message || "Erro desconhecido";
      console.error("Erro durante o upload do arquivo:", error);
      setUploadStatus(`Erro ao enviar o arquivo: ${errorMessage}`);
    }
  };

  return (
    <div className="flex flex-col items-center justify-start min-h-full h-full bg-gray-100 dark:bg-gray-900">
      <div className="w-full max-w-lg rounded-sm border border-stroke bg-white shadow-default dark:border-strokedark dark:bg-boxdark mt-12">
        <div className="border-b border-stroke px-6.5 py-4 dark:border-strokedark flex items-center justify-between">
          <h3 className="font-medium text-black dark:text-white">
            Envie arquivos para transcrição e análise
          </h3>
          <div className="relative group">
            <svg
              className="w-5 h-5 text-gray-500 cursor-pointer hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
            >
              <path
                d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20ZM13 11V16H11V11H8L12 7L16 11H13Z"
                fill="currentColor"
              />
            </svg>
            <div className="absolute hidden group-hover:block w-max bg-black text-white text-xs rounded py-1 px-2 left-1/2 transform -translate-x-1/2 -translate-y-full mt-2">
              São aceitos apenas arquivos .zip, .wav e .mp3
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-5.5 p-6.5">
          <div>
            <label className="block text-sm font-medium text-black dark:text-white mb-2">
              Selecione o arquivo
            </label>
            <input
              type="file"
              onChange={handleFileChange}
              className="w-full cursor-pointer rounded-lg border-[1.5px] border-stroke bg-transparent outline-none transition file:mr-5 file:border-collapse file:cursor-pointer file:border-0 file:border-r file:border-solid file:border-stroke file:bg-whiter file:px-5 file:py-3 file:hover:bg-primary file:hover:bg-opacity-10 focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:file:border-form-strokedark dark:file:bg-white/30 dark:file:text-white dark:focus:border-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-black dark:text-white mb-2">
              Container de Destino
            </label>
            <input
              type="text"
              value={destinationContainer}
              onChange={(e) => setDestinationContainer(e.target.value)}
              className="w-full cursor-pointer rounded-lg border-[1.5px] border-stroke bg-transparent outline-none transition focus:border-primary active:border-primary disabled:cursor-default disabled:bg-whiter dark:border-form-strokedark dark:bg-form-input dark:focus:border-primary"
            />
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={runTranscription}
              onChange={() => setRunTranscription(!runTranscription)}
              className="cursor-pointer rounded-sm border-stroke focus:border-primary dark:border-form-strokedark dark:bg-form-input"
            />
            <label className="ml-2 block text-sm font-medium text-black dark:text-white">
              Executar Transcrição
            </label>
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={runEvaluationFlow}
              onChange={() => setRunEvaluationFlow(!runEvaluationFlow)}
              disabled={!runTranscription}  // Disable if transcription is not selected
              className="cursor-pointer rounded-sm border-stroke focus:border-primary dark:border-form-strokedark dark:bg-form-input"
            />
            <label className="ml-2 block text-sm font-medium text-black dark:text-white">
              Executar Fluxo de Avaliação
            </label>
          </div>
          <button
            onClick={handleFileUpload}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Enviar Arquivo
          </button>
          {uploadStatus && (
            <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">
              {uploadStatus}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default UploadFile;

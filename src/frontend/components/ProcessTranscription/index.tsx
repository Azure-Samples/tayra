"use client";
import { useState } from "react";
import api from "@/utils/api"; // Import the configured axios instance

const TranscriptionJob: React.FC = () => {
  const [originContainer, setOriginContainer] = useState<string>("audio-files");
  const [destinationContainer, setDestinationContainer] = useState<string>("transcripts");
  const [managerName, setManagerName] = useState<string>("");
  const [specialistName, setSpecialistName] = useState<string>("");
  const [limit, setLimit] = useState<number>(-1);
  const [onlyFailed, setOnlyFailed] = useState<boolean>(true);
  const [useCache, setUseCache] = useState<boolean>(false);
  const [runEvaluationFlow, setRunEvaluationFlow] = useState<boolean>(true);
  const [status, setStatus] = useState<string>("");

  const handleJobSubmission = async () => {
    try {
      const payload = {
        origin_container: originContainer,
        destination_container: destinationContainer,
        manager_name: managerName,
        specialist_name: specialistName,
        limit: limit,
        only_failed: onlyFailed,
        use_cache: useCache,
        run_evaluation_flow: runEvaluationFlow,
      };

      setStatus("Enviando requisição...");

      const response = await api.post("/transcription", payload);

      if (response.status === 200) {
        setStatus("Job iniciado com sucesso!");
      } else {
        setStatus("Ocorreu um erro ao iniciar o job.");
      }
    } catch (error) {
      console.error("Erro ao iniciar o job:", error);
      setStatus("Erro ao iniciar o job.");
    }
  };

  return (
    <div className="flex flex-col items-center justify-start min-h-full h-full bg-gray-100 dark:bg-gray-900">
      <div className="w-full max-w-lg rounded-sm border border-stroke bg-white shadow-default dark:border-strokedark dark:bg-boxdark mt-12">
        <div className="border-b border-stroke px-6.5 py-4 dark:border-strokedark flex items-center justify-between">
          <h3 className="font-medium text-black dark:text-white">
            Iniciar Job de Transcrição
          </h3>
        </div>
        <div className="flex flex-col gap-5.5 p-6.5">
          <div>
            <label className="flex text-sm font-medium text-black dark:text-white mb-2">
              <p className="pr-4">Container de Origem</p>
            </label>
            <input
              type="text"
              value={originContainer}
              onChange={(e) => setOriginContainer(e.target.value)}
              className="w-full rounded-lg border-[1.5px] border-stroke bg-transparent outline-none transition focus:border-primary active:border-primary dark:border-form-strokedark dark:bg-form-input dark:text-white dark:focus:border-primary"
              placeholder="Digite o nome do container de origem"
            />
          </div>
          <div>
            <label className="flex text-sm font-medium text-black dark:text-white mb-2">
              <p className="pr-4">Container de Destino</p>
            </label>
            <input
              type="text"
              value={destinationContainer}
              onChange={(e) => setDestinationContainer(e.target.value)}
              className="w-full rounded-lg border-[1.5px] border-stroke bg-transparent outline-none transition focus:border-primary active:border-primary dark:border-form-strokedark dark:bg-form-input dark:text-white dark:focus:border-primary"
              placeholder="Digite o nome do container de destino"
            />
          </div>
          <div>
            <label className="flex text-sm font-medium text-black dark:text-white mb-2">
              <p className="pr-4">Nome do Gerente</p>
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
                  Deixe vazio para processar todos
                </div>
              </div>
            </label>
            <input
              type="text"
              value={managerName}
              onChange={(e) => setManagerName(e.target.value)}
              className="w-full rounded-lg border-[1.5px] border-stroke bg-transparent outline-none transition focus:border-primary active:border-primary dark:border-form-strokedark dark:bg-form-input dark:text-white dark:focus:border-primary"
              placeholder="Inclua um gerente caso queira processar parcialmente"
            />
          </div>
          <div>
            <label className="flex text-sm font-medium text-black dark:text-white mb-2">
              <p className="pr-4">Nome do Especialista</p>
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
                  Deixe vazio para processar todos
                </div>
              </div>
            </label>
            <input
              type="text"
              value={specialistName}
              onChange={(e) => setSpecialistName(e.target.value)}
              className="w-full rounded-lg border-[1.5px] border-stroke bg-transparent outline-none transition focus:border-primary active:border-primary dark:border-form-strokedark dark:bg-form-input dark:text-white dark:focus:border-primary"
              placeholder="Inclua um especialista caso queira processar parcialmente"
            />
          </div>
          <div>
            <label className="flex text-sm font-medium text-black dark:text-white mb-2">
              <p className="pr-4">Limite de Processamento</p>
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
                  Um valor de -1 processa todos. Um valor positivo processa até o limite.
                </div>
              </div>
            </label>
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              className="w-full rounded-lg border-[1.5px] border-stroke bg-transparent outline-none transition focus:border-primary active:border-primary dark:border-form-strokedark dark:bg-form-input dark:text-white dark:focus:border-primary"
              placeholder="Digite o limite de processamento"
            />
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={onlyFailed}
              onChange={(e) => setOnlyFailed(e.target.checked)}
              className="mr-2 cursor-pointer"
            />
            <label className="text-sm font-medium text-black dark:text-white">
              Processar Apenas Falhas
            </label>
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={useCache}
              onChange={(e) => setUseCache(e.target.checked)}
              className="mr-2 cursor-pointer"
            />
            <label className="text-sm font-medium text-black dark:text-white">
              Usar Cache
            </label>
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={runEvaluationFlow}
              onChange={(e) => setRunEvaluationFlow(e.target.checked)}
              className="mr-2 cursor-pointer"
            />
            <label className="text-sm font-medium text-black dark:text-white">
              Executar Fluxo de Avaliação
            </label>
          </div>
          <button
            onClick={handleJobSubmission}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Iniciar Job
          </button>
          {status && (
            <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">
              {status}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default TranscriptionJob;

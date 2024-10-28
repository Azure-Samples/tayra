"use client";
import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Transcription } from "@/types/transcription";
import api from "@/utils/api";
import { useTranscriptionContext } from "@/utils/transcriptionContext";

const ListLayout: React.FC = () => {
  const { id } = useParams();
  const router = useRouter();
  const { transcriptions, setTranscriptions, setSelectedTranscription } = useTranscriptionContext(); // Obtendo o contexto
  const [isLoading, setIsLoading] = useState(false);
  
  const decodedId = Array.isArray(id) ? decodeURIComponent(id[0]) : decodeURIComponent(id || "");
  const cachedTranscriptions = transcriptions[decodedId] || [];

  const fetchTranscriptions = useCallback(async (specialistId: string) => {
    setIsLoading(true);
    try {
      const response = await api.get(`/transcription-data?specialist=${encodeURIComponent(specialistId)}`);
      console.log(response.data);
      setTranscriptions(specialistId, response.data?.result);
    } catch (error) {
      console.error("Failed to fetch transcriptions:", error);
    } finally {
      setIsLoading(false);
    }
  }, [setTranscriptions]);

  useEffect(() => {
    if (cachedTranscriptions.length > 0) {
      setIsLoading(false);
    } else {
      fetchTranscriptions(decodedId);
    }
  }, [decodedId, cachedTranscriptions.length, fetchTranscriptions]);

  const handleTranscriptionClick = (transcription: Transcription) => {
    setSelectedTranscription(transcription);
    console.log(transcription);
    router.push(`/transcriptions/${transcription.id}`);
  };

  const extractDateFromFilename = (filename: string) => {
    const regexPattern1 = /C\d{4}(\d{4})(\d{2})(\d{2})\d{6}\./;
    const regexPattern2 = /\/\d{5}(\d{4})(\d{2})(\d{2})\d{9}\./;

    let match = filename.match(regexPattern1);
    if (!match) {
        match = filename.match(regexPattern2);
    }

    if (match) {
      const [_, year, month, day] = match;
      return `${day}/${month}/${year}`;
    }

    return filename;
  };

  return (
    <div className="p-6 bg-white dark:bg-gray-800 min-h-screen">
      <h1 className="text-2xl font-bold mb-4 text-black dark:text-white">
        Transcrições de {decodedId}
      </h1>
      {isLoading ? (
        <p className="text-gray-500 dark:text-gray-400">Carregando...</p>
      ) : (
        <>
          <h3 className="font-bold my-4 text-black dark:text-white">
            Transcrições
          </h3>
          {cachedTranscriptions.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {cachedTranscriptions.map((transcription) => (
                <div 
                  key={transcription.id} 
                  className="border p-4 rounded-lg shadow cursor-pointer"
                  onClick={() => handleTranscriptionClick(transcription)}
                >
                  <p className="font-medium text-lg">{transcription.id}</p>
                  <p className="text-gray-600">Processado em: {extractDateFromFilename(transcription.filename)}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400">
              Nenhuma transcrição encontrada para este especialista.
            </p>
          )}
        </>
      )}
    </div>
  );
};

export default ListLayout;

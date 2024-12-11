"use client";
import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Transcription } from "@/types/transcription";
import { transcriptionApi } from "@/utils/api";
import { useTranscriptionContext } from "@/utils/transcriptionContext";

const ListLayout: React.FC = () => {
  const { id } = useParams();
  const router = useRouter();
  const { transcriptions, setTranscriptions, setSelectedTranscription } = useTranscriptionContext();
  const [isLoading, setIsLoading] = useState(false);

  // Ensure id is a string
  const decodedId = Array.isArray(id) ? decodeURIComponent(id[0]) : decodeURIComponent(id);
  const cachedTranscriptions = transcriptions[decodedId] || [];

  const fetchTranscriptions = useCallback(async (specialistId: string) => {
    setIsLoading(true);
    try {
      // Fetch logic here
    } catch (error) {
      // Error handling here
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div>
      {/* JSX content here */}
    </div>
  );
};

export default ListLayout;
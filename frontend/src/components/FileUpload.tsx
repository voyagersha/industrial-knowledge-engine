import React from 'react';
import { Box, Button, Typography, Paper } from '@mui/material';
import { Upload as UploadIcon } from '@mui/icons-material';
import { uploadFile } from '../services/api';

interface FileUploadProps {
  onProcessed: (result: any) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onProcessed }) => {
  const [isDragging, setIsDragging] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file.type !== 'text/csv') {
      setError('Please upload a CSV file');
      return;
    }
    
    try {
      const result = await uploadFile(file);
      onProcessed(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error processing file');
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    try {
      const result = await uploadFile(file);
      onProcessed(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error processing file');
    }
  };

  return (
    <Paper
      sx={{
        p: 3,
        textAlign: 'center',
        border: '2px dashed',
        borderColor: isDragging ? 'primary.main' : 'grey.500',
        bgcolor: 'background.paper',
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <UploadIcon sx={{ fontSize: 48, color: 'primary.main' }} />
      <Typography variant="h6" gutterBottom>
        Drop your work orders CSV file here
      </Typography>
      <Typography variant="body2" color="textSecondary" gutterBottom>
        or
      </Typography>
      <Button
        variant="contained"
        component="label"
      >
        Select File
        <input
          type="file"
          hidden
          accept=".csv"
          onChange={handleFileSelect}
        />
      </Button>
      {error && (
        <Typography color="error" sx={{ mt: 2 }}>
          {error}
        </Typography>
      )}
    </Paper>
  );
};

export default FileUpload;

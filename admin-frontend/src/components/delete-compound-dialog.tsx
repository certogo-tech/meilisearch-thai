'use client';

import React from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { CompoundWord } from '@/types';

interface DeleteCompoundDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  compound: CompoundWord | null;
  onConfirm: () => Promise<void>;
  isLoading?: boolean;
}

export function DeleteCompoundDialog({
  open,
  onOpenChange,
  compound,
  onConfirm,
  isLoading = false,
}: DeleteCompoundDialogProps) {
  const handleConfirm = async () => {
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (error) {
      console.error('Error deleting compound:', error);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Compound Word</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete the compound word{' '}
            <span className="font-semibold font-thai">"{compound?.word}"</span>?
            This action cannot be undone and will remove the word from the tokenizer dictionary.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={isLoading}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isLoading ? 'Deleting...' : 'Delete'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
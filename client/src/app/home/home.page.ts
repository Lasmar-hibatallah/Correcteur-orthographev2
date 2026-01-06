import { Component } from '@angular/core';
import { finalize } from 'rxjs/operators';
import { CorrectionService } from '../services/correction.service';
import { LTMatch } from '../models/languagetool.model';

@Component({
  selector: 'app-home',
  templateUrl: 'home.page.html',
  styleUrls: ['home.page.scss'],
  standalone: false
})
export class HomePage {
  text: string = '';
  isLoading = false;
  hasAnalyzed = false;
  matches: LTMatch[] = [];
  errorMessage = '';

  constructor(private correctionService: CorrectionService) {}

  analyze(): void {
  this.errorMessage = '';

  const trimmed = (this.text ?? '').trim();

  // L’utilisateur a déclenché l’action "Analyser"
  this.hasAnalyzed = true;

  if (!trimmed) {
    this.matches = [];
    return;
  }

  this.isLoading = true;
  this.matches = [];

  this.correctionService
    .checkText(trimmed)
    .pipe(finalize(() => (this.isLoading = false)))
    .subscribe({
      next: (res) => {
        this.matches = res?.matches ?? [];
      },
      error: () => {
        this.errorMessage =
          "Impossible d’analyser le texte (connexion Internet ou API indisponible).";
        this.matches = [];
      },
    });
}


 clear(): void {
  this.text = '';
  this.matches = [];
  this.errorMessage = '';
  this.hasAnalyzed = false;
}
}

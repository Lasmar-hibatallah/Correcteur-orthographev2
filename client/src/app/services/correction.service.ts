import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { LTResponse } from '../models/languagetool.model';

@Injectable({
  providedIn: 'root',
})
export class CorrectionService {
  // Endpoint officiel (pas de backend personnel)
  private readonly endpoint = '/languagetool/v2/check';

  constructor(private http: HttpClient) {}

  /**
   * Analyse un texte en français via LanguageTool.
   * Retourne la liste des erreurs (matches) + suggestions.
   */
  checkText(text: string): Observable<LTResponse> {
    const body = new HttpParams()
      .set('text', text)
      .set('language', 'fr')
      .set('enabledOnly', 'false');

    return this.http.post<LTResponse>(this.endpoint, body.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  }
}

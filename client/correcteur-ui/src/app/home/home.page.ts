import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { IonicModule } from '@ionic/angular';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-home',
  templateUrl: 'home.page.html',
  styleUrls: ['home.page.scss'],
  standalone: true,
  imports: [IonicModule, FormsModule] // HttpClientModule n’est pas nécessaire ici
})
export class HomePage {
  text = '';
  result: any = null;

  constructor(private http: HttpClient) {}

  correctText() {
    this.http.post('http://localhost:5050/correct', { text: this.text })
      .subscribe(res => this.result = res);
  }
}

import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { addIcons } from 'ionicons';
import { arrowForwardOutline } from 'ionicons/icons';

@Component({
  selector: 'app-welcome',
  templateUrl: './welcome.page.html',
  styleUrls: ['./welcome.page.scss'],
  standalone: true,
  imports: [IonicModule]
})
export class WelcomePage {

  constructor(private router: Router) {
    addIcons({ arrowForwardOutline });
  }

  goToHome() {
    this.router.navigate(['/home']);
  }
}
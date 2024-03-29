# -*- coding: utf-8 -*-
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as image
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable
from models import *
from hyperparameters import *
import os

import torchvision.datasets as dset
import torchvision.transforms as transforms


#Training
class Trainer():
    def __init__(self, save_path = "results/", output_results = True):
        self.cuda = torch.cuda.is_available()

        # Models
        self.D = D_conv()
        if self.cuda:
            self.D.cuda()
        self.G = G_conv()
        if self.cuda:
            self.G.cuda()

        # Optimizers
        self.D_optimiser = optim.Adam(self.D.parameters(), lr = lr, betas = (beta1, beta2))
        self.G_optimiser = optim.Adam(self.G.parameters(), lr = lr, betas = (beta1, beta2))

        # Variables to create plots and images
        self.save_path = save_path
        self.output_results = output_results
        self.nb_image_to_generate = 5
        self.predictions = []
        self.g_losses = []
        self.d_losses = []
        self.z_saved = Variable(torch.randn((self.nb_image_to_generate, G_inputs)))
        if isinstance(self.G, G_conv):
            self.z_saved = self.z_saved.view(-1, G_inputs, 1, 1)
        if self.cuda:
            self.z_saved = self.z_saved.cuda()

    def train(self):
        
        # Start loop for each epoch
        for e in range(0, nb_epoch):
            print("Epoch: " + str(e))
            g_loss = []
            d_loss = []
            pred = []

            # Start loop for each minibatch
            for batch_idx, (x, target) in enumerate(self.train_loader):
                
                current_batch_size = x.shape[0]

                #if batch_idx > 20:
                #    break

                # Useful variables for training
                x = Variable(x)
                if isinstance(self.G, G):
                    x = x.view(-1, image_x * image_y)
                if self.cuda:
                    x = x.cuda()

                y_almost_ones = Variable(torch.ones(current_batch_size))
                if self.cuda:
                    y_almost_ones = y_almost_ones.cuda()

                y_almost_zeros = Variable(torch.zeros(current_batch_size))
                if self.cuda:
                    y_almost_zeros = y_almost_zeros.cuda()

                temp_loss = []

                for k in range(0, D_steps):
                    # Train discrimator
                    self.D.zero_grad()

                    # Generate noise
                    z = Variable(torch.randn((current_batch_size, G_inputs)))
                    if isinstance(self.G, G_conv):
                        z = z.view(-1, G_inputs, 1, 1)
                    if self.cuda:
                        z = z.cuda()
                    # Train on real data
                    real_prediction = self.D(x).squeeze() # 1x1
                    loss_d_r = self.D.loss(real_prediction, y_almost_ones)

                    # Train on generated data
                    generated_batch = self.G(z)
                    generated_prediction = self.D(generated_batch).squeeze() # 1x1
                    loss_d_f = self.D.loss(generated_prediction, y_almost_zeros)

                    # Add losses
                    loss_d_total = loss_d_r + loss_d_f

                    # Backprop
                    loss_d_total.backward()
                    self.D_optimiser.step()

                    # Keep track of loss
                    temp_loss.append(loss_d_r.data + loss_d_f.data)

                d_loss.append(np.mean(temp_loss))
                temp_loss = []
                temp_prediction = []

                for k in range(0, G_steps):
                    # Train generator
                    self.G.zero_grad()

                    # Generate noise
                    z = Variable(torch.randn((current_batch_size, G_inputs)))
                    if isinstance(self.G, G_conv):
                        z = z.view(-1, G_inputs, 1, 1)
                    if self.cuda:
                        z = z.cuda()

                    generated_batch = self.G(z)

                    # Train generator with predictions from the discrimator
                    D_prediction = self.D(generated_batch).squeeze() # 1x1
                    loss_G = self.G.loss(D_prediction, y_almost_ones)

                    # Backprop
                    loss_G.backward()
                    self.G_optimiser.step()
                    
                    # Keep track of loss and prediction
                    temp_loss.append(loss_G.data)
                    temp_prediction.append(D_prediction.mean().data)
    
                pred.append(np.mean(temp_prediction))
                g_loss.append(np.mean(temp_loss))
            
            self.predictions.append(np.mean(pred))
            self.d_losses.append(np.mean(d_loss))
            self.g_losses.append(np.mean(g_loss))

            self.write_image(e)
            self.create_plots()
            self.save_models()

    def write_image(self, e):
        # Write generated image
        image_temp = self.G(self.z_saved).view(1, image_x * self.nb_image_to_generate, image_y)
        image.imsave(self.save_path + "gen_epoch_" + str(e) + ".png", image_temp[0].data, cmap='gray')


    def create_plots(self):
        # Different name for conv nets
        prefix = ""
        if isinstance(self.G, G_conv):
            prefix = "conv_"

        # Save predictions
        plt.plot(self.predictions)
        plt.xlabel("Epoch")
        plt.ylabel("Discriminator prediction")
        plt.savefig(self.save_path + "" + prefix + "predictions.png")

        plt.clf()

        # Save losses
        plt.plot(self.g_losses, label="G loss")
        plt.plot(self.d_losses, label="D loss")
        plt.legend(loc="best")
        plt.xlabel("Epoch")
        plt.ylabel("Loss")
        plt.savefig(self.save_path + "" + prefix + "losses.png")

        plt.clf()


    def load_mnist(self, root="./dataMnist"):
        # Create transform
        trans = transforms.Compose([
                transforms.Resize(image_x),
                transforms.ToTensor(),
                transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))])

        # Load MNIST dataset
        train_set = dset.MNIST(root=root, train=True, transform=trans, download=True)

        self.train_loader = torch.utils.data.DataLoader(
                            dataset=train_set,
                            batch_size=minibatch_size,
                            shuffle=True)

    def save_models(self):
        # Save trained models to disk
        torch.save(self.G.state_dict(), self.save_path + "g_saved.pt")
        torch.save(self.D.state_dict(), self.save_path + "d_saved.pt")


def main():
    # Create trainer and load data
    T = Trainer(save_path="results/")
    T.load_mnist()
    # Save hyperparameter config
    from shutil import copyfile
    os.makedirs(T.save_path, exist_ok = True)
    copyfile("hyperparameters.py", T.save_path + "hyperparameters.py")
    # Start training
    T.train()
    # Save trained models
    T.save_models()

if __name__ == "__main__":
    main()


import torchvision.models as models
import torch
from torch.utils.data import DataLoader
from torchvision import datasets
import os
import torchvision
import torchvision.transforms as transforms
import torch.optim as optim
import torch.nn as nn
import copy
from torch.optim import lr_scheduler
import matplotlib.pyplot as plt
import time


#hardware is 'cpu' or 'gpu'
#conv_layer_count is 0,1,2 or 3. Selects the number of conv.
#layers to be trained(starting from bottom)
def create_model(hardware,conv_layer_count):
    #load model vgg16
    model_vgg16 = models.vgg16(pretrained=True) 
    
    
    #freeze layers
    for param in model_vgg16.parameters():
        param.require_grad = False
        
        
    #add fc layers back so that their gradients will be calculated
    classifiers=nn.Sequential(
        #extra dropout layer
        #nn.Dropout(0.5),
        nn.Linear(25088,4096,True),
        nn.ReLU(True),
        nn.Dropout(0.5),
        nn.Linear(4096,4096,True),
        nn.ReLU(True),
        nn.Dropout(0.5),
        nn.Linear(4096,24,True),
        
    )
  
    #update classifiers of the model
    model_vgg16.classifier=classifiers
    
    
    use_gpu=torch.cuda.is_available()
    
    if hardware=='gpu':
        if use_gpu:
            device = torch.device('cuda')
            model_vgg16=model_vgg16.cuda()
        else:
            device = torch.device('cpu')
    if hardware=='cpu':
        device = torch.device('cpu')
        
    print('Created model for '+str(hardware))
    model_vgg16 = model_vgg16.to(device)
    return model_vgg16,device













def load_data(dir,normalize,batch):
    image_datasets = {x: datasets.ImageFolder(os.path.join(dir, x),normalize[x])for x in ['train', 'val','test']}
    
    
    dataloaders = {x: DataLoader(image_datasets[x], batch_size=batch,shuffle=True, num_workers=0)for x in ['train', 'val','test']}
    dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'val','test']}
    for phase in ['train', 'val','test']:
        print(str(dataset_sizes[phase]) +' images loaded for '+str(phase))
    return dataloaders,dataset_sizes
  
  
def draw(lst_iter, lst_loss, lst_acc, title,save):
  
    #draw loss or accuracy graph
    plt.plot(lst_iter, lst_loss, '-b', label='loss')
    plt.plot(lst_iter, lst_acc, '-r', label='accuracy')
    plt.xlabel("epochs")
    plt.legend(loc='upper left')
    plt.title(title)

    if save==True:
        plt.savefig(title+".png")  # should before show method

    # show
    plt.show()          
    
    
def train(model,optimizer,criterion,scheduler,number_of_epochs,dataloaders,dataset_sizes,batch_size,device,learning_params):
    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0
    
    epoch_losses_val=[]
    epoch_losses_train=[]
    epoch_acc_train=[]
    epoch_acc_val=[]
    stop_threshold=6
    no_improve=0
    min_loss=1000.0
    print('Initial learning rate is :'+str(learning_params['lr']))
    updated_learningRate=learning_params['lr']   
    for epoch in range(number_of_epochs):
        print('Epoch {}/{}'.format(epoch+1, number_of_epochs))
#         if epoch%learning_params['ss']==0 and epoch!=0:
#             updated_learningRate=updated_learningRate-updated_learningRate*learning_params['gamma']
#             print('New learning rate is :'+str(updated_learningRate))
        print('-' * 10)
        for phase in ['train','val']:
            if phase=='train':
                scheduler.step()
                model.train()
            if phase=='val':
                model.eval()
                
            running_loss = 0.0
            running_corrects = 0
            for i,data in enumerate(dataloaders[phase]):
              
               
                inputs, labels = data
                inputs = inputs.to(device)
                labels = labels.to(device)
                optimizer.zero_grad()
                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                   
                    loss = criterion(outputs, labels)
                    if phase == 'train':
                        loss.backward()
                        optimizer.step()
                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)
                
                
            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]
            
            if phase=='train':
                epoch_losses_train.append(epoch_loss)
                epoch_acc_train.append(epoch_acc)
            else:
                epoch_losses_val.append(epoch_loss)
                epoch_acc_val.append(epoch_acc)
            print('{} Loss: {:.4f} Acc: {:.4f}'.format(
                phase, epoch_loss, epoch_acc))
            
            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())
                
                
            """--------EARLY STOPPING--------"""
            """--------EARLY STOPPING--------"""
            if phase == 'val' and epoch_loss<min_loss:
                no_improve=0
                min_loss=epoch_loss
            elif phase == 'val' and epoch_loss>=min_loss:
                no_improve+=1
                if stop_threshold==no_improve:
                    print('Stop early at epoch:'+str(epoch+1))
                    print('Best val Acc: {:4f}'.format(best_acc))
                    epoch_arr=[]
                    for i in range(epoch+1):
                       epoch_arr.append(i+1) 
                    draw(epoch_arr,epoch_losses_train,epoch_acc_train,'Adam Optimizer Train',True)
                    draw(epoch_arr,epoch_losses_val,epoch_acc_val,'Adam Optimizer Validation',True)
                    model.load_state_dict(best_model_wts)
                    return model
            """--------EARLY STOPPING--------"""
            """--------EARLY STOPPING--------"""
                    
               
    print('Best val Acc: {:4f}'.format(best_acc))
    
    epoch_arr=[]
    for i in range(number_of_epochs):
       epoch_arr.append(i+1) 
    
    draw(epoch_arr,epoch_losses_train,epoch_acc_train,'Adam Optimizer Train',True)
    draw(epoch_arr,epoch_losses_val,epoch_acc_val,'Adam Optimizer Validation',True)
    model.load_state_dict(best_model_wts)
    return model
                
          
def process_test_data(model,device,dataloaders,dataset_sizes):
    running_corrects=0
    top_five=0
    model.eval()
    for i,data in enumerate(dataloaders['test']):
        inputs, labels = data
        inputs = inputs.to(device)
        labels = labels.to(device)
        with torch.no_grad():
             outputs = model(inputs)
             _, preds = torch.max(outputs, 1)
        running_corrects += torch.sum(preds == labels.data)
        probs,classes=outputs.topk(5,dim=1)
        size=labels.size(0)
        for i in range(size):
             if labels[i] in classes[i]:
                  top_five+=1
        
    acc = running_corrects.double() / dataset_sizes['test']
    five_acc=top_five/ dataset_sizes['test']
    print('Test Model Acc: {:4f}'.format(acc))
    print('Test Model Top-5 Acc: {:4f}'.format(five_acc))
    
    
    
def main(optim_name):
    start=time.time()
    
    
    data_transforms = {
    'train': transforms.Compose([
        transforms.RandomResizedCrop(224),
        transforms.CenterCrop(224),
        torchvision.transforms.ColorJitter(brightness=.05, contrast=.05),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
#         
    ]),
    'val': transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        torchvision.transforms.ColorJitter(brightness=.05, contrast=.05),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
#         torchvision.transforms.ColorJitter(brightness=.05, contrast=.05)
    ]),
    'test': transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        torchvision.transforms.ColorJitter(brightness=.05, contrast=.05),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
#         torchvision.transforms.ColorJitter(brightness=.05, contrast=.05)
    ])
}
    
    """---------PARAMETERS-----------"""
    #wd:weight decay, lr:leaerning rate,ss:step size, gamma:scheduler coefficients
    learning_params={'lr':0.0001 ,'wd':0.01,'ss':7,'gamma':0.1}
    batch_size=32
    direction='Dataset/dataset'
    number_of_epochs=25
    """---------PARAMETERS-----------"""
    
    
    #create model, set second param to zero to only train fc layers
    
    model,device=create_model('gpu',3)
    criterion=nn.CrossEntropyLoss()
    
    #use other optimizers
    if   optim_name=='sgd':
        optimizer=optim.SGD(model.parameters(),lr=learning_params['lr'],momentum=0.9)
    elif optim_name=='rms':
        optimizer=optim.RMSprop(model.parameters(),lr=learning_params['lr'],alpha=0.9)
    else:
        optimizer=optim.Adam(model.parameters(),lr=learning_params['lr'],weight_decay=learning_params['wd'])
    scheduler = lr_scheduler.StepLR(optimizer, step_size=learning_params['ss'], gamma=learning_params['gamma'])
    
    
    
    
    
    dataloaders,dataset_sizes=load_data(direction,data_transforms,batch_size)
    
    
    
    
    
    trained_model=train(model,optimizer,criterion,scheduler,
                                        number_of_epochs,dataloaders,dataset_sizes,batch_size,device,learning_params)
    
    
    process_test_data(trained_model,device,dataloaders,dataset_sizes)
    torch.save(trained_model,'trained_vggModel.pth')
    print('Total time is: {:2f}'.format((time.time()-start)/60)+' minutes')
          
#'adam', 'sgd' or 'rms'     
main('adam')

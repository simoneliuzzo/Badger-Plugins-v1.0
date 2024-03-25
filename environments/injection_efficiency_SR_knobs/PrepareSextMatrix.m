% HOR DA

% SEXT
i=1;
sknob(i,:)=KnobCreator('SEXT',6)*0.1; i = i+1; % 0.05
sknob(i,:)=KnobCreator('SEXT',6,'cos')*0.1; i = i+1;  % 0.05

%eigenvectors
load('MatrixForNicola.mat');
sknob(i,:)=v(:,69);i = i+1;  
sknob(i,:)=v(:,70);i = i+1;  
sknob(i,:)=v(:,79);i = i+1;  
sknob(i,:)=v(:,80);i = i+1;  

% VER DA
sknob(i,:)=v(:,41);i = i+1;  
sknob(i,:)=v(:,42);i = i+1;  
sknob(i,:)=v(:,57);i = i+1;  
sknob(i,:)=v(:,58);i = i+1;  
sknob(i,:)=v(:,61);i = i+1;  
sknob(i,:)=v(:,62);i = i+1;  
sknob(i,:)=v(:,81);i = i+1;  
sknob(i,:)=v(:,82);i = i+1;  
sknob(i,:)=v(:,94);i = i+1;  
sknob(i,:)=v(:,95);i = i+1;  


csvwrite('./data/SextKnob.csv',sknob)

% ver DA
oknob(1,:)=KnobCreator('OCT',15)*1; % 0.05
oknob(2,:)=KnobCreator('OCT',17)*1; % 0.05

csvwrite('./data/OctKnob.csv',oknob)


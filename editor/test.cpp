#include<iostream>
#include<math.h> 
#include<bits/stdc++.h>
using namespace std;
long long pan[40][40];
int main(){
	int n,m,a,b;
	cin>>n>>m>>a>>b;
	n++;
	m++;
	memset(pan,0,sizeof(pan));
	pan[0][0]=1;
	for(int i=0;i<n;i++){
		for(int j=0;j<m;j++){
			if((abs(i-a)==2&&abs(j-b)==1)||(abs(i-a)==1&&abs(j-b)==2)||(i==a&&j==b)){
				;
			}
			else{
				if((i==0&&j==0)){
					;
				}
				else if(i==0){
					pan[i][j]=pan[0][j-1];
				}
				else if(j==0){
					pan[i][j]=pan[i-1][0];
				}
				else{
					pan[i][j]=pan[i][j-1]+pan[i-1][j];
				}
			}
		}
	}
	cout<<pan[n-1][m-1];
	return 0;
}
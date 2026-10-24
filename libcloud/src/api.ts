



interface libCloudParams {

    username:string,
    max_icons:number,
    order_by:string,
    preset:string,
    color:string,
    include_forks:boolean,
    include_private:boolean,
    token:string,

    

}



const API_URL = "http://localhost:8000";

export async function generateLogo(librequest:libCloudParams) {


    const headers:Record<string,string> = {
        "Content-Type":"application/json"
    }



    const res = await fetch(`${API_URL}/framecloud?username=${librequest.username}`,{

     headers,
     credentials:"include",
     method:"POST",
     body:JSON.stringify(librequest)
     
    })
    

    if(!res.ok){
       throw new Error(await res.text()); 
    }

    const data = await res.json();
    return data;



}

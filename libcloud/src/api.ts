

import * as z from "zod";




const libCloudParams  = z.object({

    username:z.string(),
    max_icons:z.int().default(100),
    order_by:z.string().default("max-freq"),
    preset:z.string().optional().default("white"),
    color:z.string().optional().default("white"),
    include_forks:z.boolean().default(false),
    include_private:z.boolean().default(false),
    token:z.string(),

})



const libCloudParamsType = typeof libCloudParams;


const API_URL = "http://localhost:8000";

export async function generateLogo(librequest:libCloudParamsType) {


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

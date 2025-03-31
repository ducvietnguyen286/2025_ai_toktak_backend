# 2025_AI_Toktak_BE
py -m venv env
python -m venv venv  # Tạo môi trường ảo
venv\Scripts\activate
flask run --port=5001
flask run --port=6001 --host=0.0.0.0


git pull origin main && sudo systemctl restart toktak.service


http://118.70.171.129:9955/
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=99553)



 
rm -rf /var/www/logs/*
rm -rf /var/www/toktak/logs/*
sudo systemctl restart nginx 
pm2 reload all

sudo systemctl restart consumer_toktak
sudo systemctl restart consumer_toktak_tiktok
sudo systemctl restart consumer_toktak_twitter
sudo systemctl restart consumer_toktak_youtube
sudo systemctl restart consumer_toktak_thread
sudo systemctl restart consumer_toktak_instagram
sudo systemctl restart toktak.service



journalctl -u toktak.service -f


journalctl -u toktak.service

# 2025_AI_Toktak_BE
py -m venv env
python -m venv venv  # Tạo môi trường ảo

venv\Scripts\activate 
flask run --port=6001 --host=0.0.0.0


git pull origin main && sudo systemctl restart toktak.service

/// Ubunut 
python3.9 -m venv venv
source venv/bin/activate



http://118.70.171.129:9955/
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=99553)



rm -rf /var/www/logs/*
rm -rf /var/www/toktak/logs/*

 
rm -rf /var/www/logs/*
rm -rf /var/www/2025_ai_toktak_be/logs/*
sudo systemctl restart nginx 
pm2 reload all


sudo systemctl restart toktak
sudo systemctl restart create_content_1
sudo systemctl restart create_content_2


sudo systemctl restart consumer-facebook
sudo systemctl restart consumer-tiktok
sudo systemctl restart consumer-twitter
sudo systemctl restart consumer-youtube
sudo systemctl restart consumer-thread
sudo systemctl restart consumer-instagram

sudo systemctl restart nginx 



journalctl -u toktak.service -f


journalctl -u toktak.service


Do server SNS là khác server lên cần mount folder 



rm -rf /var/www/logs/* && rm -rf /var/www/2025_ai_toktak_be/logs/* && sudo systemctl restart nginx && sudo systemctl restart toktak.service && sudo systemctl restart toktak_watchdog.service


Server 82
rm -rf /var/www/logs_toktak/* && rm -rf /var/www/2025_ai_toktak_be/logs/* && sudo systemctl restart nginx && sudo systemctl restart toktak.service && sudo systemctl restart toktak_watchdog.service && sudo systemctl restart toktak_consumer_content.service




sudo systemctl restart toktak_watchdog.service

sudo systemctl status toktak_watchdog.service

sudo systemctl status toktak.service


/etc/systemd/system


journalctl -u toktak_watchdog.service -f


Server 82

rm -rf /var/www/logs/* && rm -rf /var/www/toktak/logs/* && sudo systemctl restart nginx && sudo systemctl restart toktak.service && sudo systemctl restart toktak_watchdog.service

sudo systemctl restart consumer_toktak_instagram.service
sudo systemctl restart consumer_toktak_thread.service
sudo systemctl restart consumer_toktak_tiktok.service
sudo systemctl restart consumer_toktak_twitter.service
sudo systemctl restart consumer_toktak_youtube.service

sudo systemctl restart nginx 


chmod +x /var/www/toktak/entry-point.sh


git update-index --no-assume-unchanged run_with_watchdog.sh
git update-index --no-assume-unchanged entry-point.sh




-----------LIVE SERVER
sudo systemctl status toktak.service
sudo systemctl status toktak_watchdog.service
sudo systemctl status create_content_1.service
sudo systemctl status create_content_2.service


rm -rf /var/www/logs/* && rm -rf /var/www/2025_ai_toktak_be/logs/* && sudo systemctl restart nginx && sudo systemctl restart toktak.service && sudo systemctl restart toktak_watchdog.service && sudo systemctl status create_content_1.service && sudo systemctl status create_content_2.service



sudo systemctl status rabbitmq-serve


양훈탁

780109 - 1 

01029020640

----------------------------------

rm -rf /var/www/logs/* && rm -rf /var/www/logs_toktak/* && rm -rf /var/www/toktak/logs/* && rm -rf /var/www/staging/main_toktak_fe/2025_ai_toktak_be/logs/* && sudo systemctl restart nginx && sudo systemctl restart toktak.service && sudo systemctl restart toktak_watchdog.service && sudo systemctl restart consumer_toktak.service  && sudo systemctl restart consumer_toktak_instagram.service && sudo systemctl restart consumer_toktak_thread.service && sudo systemctl restart consumer_toktak_tiktok.service && sudo systemctl restart consumer_toktak_twitter.service && sudo systemctl restart consumer_toktak_youtube.service && sudo systemctl restart main_toktak.service  && sudo systemctl restart main_consumer_toktak_instagram.service  && sudo systemctl restart main_consumer_toktak_thread.service  && sudo systemctl restart main_consumer_toktak_tiktok.service  && sudo systemctl restart main_consumer_toktak_twitter.service  && sudo systemctl restart main_consumer_toktak_youtube.service  && sudo systemctl restart main_toktak_consumer_content.service  && sudo systemctl restart main_toktak_watchdog.service 


sudo systemctl restart main_consumer_toktak_instagram.service
sudo systemctl restart main_consumer_toktak_thread.service
sudo systemctl restart main_consumer_toktak_tiktok.service
sudo systemctl restart main_consumer_toktak_twitter.service
sudo systemctl restart main_consumer_toktak_youtube.service
sudo systemctl restart main_toktak.service
sudo systemctl restart main_toktak_consumer_content.service
sudo systemctl restart main_toktak_watchdog.service


sudo systemctl status main_consumer_toktak_youtube.service
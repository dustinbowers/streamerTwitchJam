package main

import (
	"context"
	"fmt"
	"github.com/andreykaipov/goobs"
	"github.com/andreykaipov/goobs/api/requests/general"
	"github.com/andreykaipov/goobs/api/requests/sceneitems"
	"github.com/andreykaipov/goobs/api/requests/sources"
	"log"
	"streamerAppConfig/types"
)

// App struct
type App struct {
	ctx       context.Context
	ObsClient *goobs.Client

	WindowConfig *types.WindowConfig
}

// NewApp creates a new App application struct
func NewApp() *App {
	return &App{}
}

// startup is called at application startup
func (a *App) startup(ctx context.Context) {
	// Perform your setup here
	a.ctx = ctx
}

// domReady is called after the front-end dom has been loaded
func (a *App) domReady(ctx context.Context) {
	// Add your action here
}

// beforeClose is called when the application is about to quit,
// either by clicking the window close button or calling runtime.Quit.
// Returning true will cause the application to continue,
// false will continue shutdown as normal.
func (a *App) beforeClose(ctx context.Context) (prevent bool) {
	return false
}

// shutdown is called at application termination
func (a *App) shutdown(ctx context.Context) {
	// Perform your teardown here
}

func (a *App) LoadSecretPy() *types.SecretPy {
	log.Printf("LoadSecretPy")
	secret, err := LoadSecretPy("secret.py")
	if err != nil {
		log.Printf("LoadSecretPy error: %v", err)
		return &types.SecretPy{
			Username: "",
			Password: "",
		}
	}
	return secret
}

func (a *App) SaveSecretPy(secret *types.SecretPy) types.StatusMessage {
	log.Printf("SaveSecretPy")
	err := SaveSecretPy("secret.py", secret)
	if err != nil {
		log.Printf("SaveSecretPy error: %v", err.Error())
		return types.NewStatusMessage("error", err.Error(), nil)
	}
	return types.NewStatusMessage("success", "Saved Successfully!", nil)
}

func (a *App) ConnectOBS() types.StatusMessage {
	log.Printf("ConnectOBS")
	if a.ObsClient != nil {
		log.Printf("Disconnecting from existing OBS connection...")
		a.ObsClient.Disconnect()
		a.ObsClient = nil
	}

	secrets := a.LoadSecretPy()
	host := "localhost"
	port := "4455"
	password := secrets.Password

	obsHost := fmt.Sprintf("%s:%s", host, port)
	obsClient, err := goobs.New(obsHost, goobs.WithPassword(password))
	if err != nil {
		log.Printf("Error connecting to OBS: %v", err)
		return types.NewStatusMessage("error", err.Error(), nil)
	}
	a.ObsClient = obsClient

	videoOutputSettings, err := a.GetVideoOutputSettings()
	if err != nil {
		msg := fmt.Sprintf("error getting video output settings: %v", err)
		log.Printf(msg)
		return types.NewStatusMessage("error", msg, nil)
	}
	return types.NewStatusMessage("success", "Connected!", videoOutputSettings)
}

func (a *App) GetWindowConfig() types.StatusMessage {
	// Load WindowConfig
	windowConfig, err := ReadWindowConfig("windowConfig.json")
	log.Printf("GetWindowConfig")
	if err != nil {
		msg := fmt.Sprintf("ReadWindowConfig error: %v", err)
		log.Printf(msg)

		newWindowConfig := types.NewWindowConfig()
		return types.NewStatusMessage("success", "Couldn't find window config file. We'll create one later", newWindowConfig)
	}
	a.WindowConfig = windowConfig
	return types.NewStatusMessage("success", "Loaded windowConfig successfully!", windowConfig)
}

func (a *App) WriteWindowConfig(data types.WindowConfig) types.StatusMessage {
	log.Printf("WriteWindowConfig, got %#v", data)
	err := SaveWindowConfig("windowConfig.json", &data)
	if err != nil {
		msg := fmt.Sprintf("error saving window config: %v", err)
		log.Printf(msg)
		return types.NewStatusMessage("error", msg, nil)
	}
	return types.NewStatusMessage("success", "Saved Window Config", nil)
}

func (a *App) GetInfoWindowConfig() types.StatusMessage {
	infoWindowData, err := ReadInfoWindowData("infoWindowDataConfig.json")
	if err != nil {
		msg := fmt.Sprintf("ReadInfoWindowData error: %v", err)
		log.Printf(msg)

		newInfoWindowConfig := types.NewInfoWindowData()
		return types.NewStatusMessage("success", "Couldn't find infoWindowConfig file. We'll create one later", newInfoWindowConfig)
	}
	return types.NewStatusMessage("success", "Loaded infoWindowData successfully!", infoWindowData)
}

func (a *App) WriteInfoWindowConfig(data types.InfoWindowData) types.StatusMessage {
	log.Printf("WriteInfoWindowConfig")
	err := SaveInfoWindowData("infoWindowDataConfig.json", &data)
	if err != nil {
		msg := fmt.Sprintf("error writing infoWindowConfig: %s", err.Error())
		log.Printf(msg)
		return types.NewStatusMessage("error", msg, nil)
	}
	return types.NewStatusMessage("success", "Saved Info Window Config", nil)
}

func (a *App) GetSceneItems() types.StatusMessage {
	log.Printf("GetSceneItems")
	if a.ObsClient == nil {
		log.Printf("GetSceneItems: OBS not connected.")
		return types.NewStatusMessage("error", "OBS not connected...", nil)
	}

	// Get SceneItems
	sceneName := "Scene"
	params := sceneitems.NewGetSceneItemListParams().WithSceneName(sceneName)
	sceneItemList, err := a.ObsClient.SceneItems.GetSceneItemList(params)
	if err != nil {
		return types.NewStatusMessage("error", err.Error(), nil)
	}
	return types.NewStatusMessage("success", "Fetched OBS SceneItems successfully!", sceneItemList)
}

func (a *App) GetVideoOutputScreenshot(sourceName string) types.StatusMessage {
	log.Printf("GetVideoOutputScreenshot")

	version, err := a.ObsClient.General.GetVersion(&general.GetVersionParams{})
	log.Printf("GetVideoOutputScreenshot supported img formats: %v", version.SupportedImageFormats)
	if err != nil {
		log.Printf("GetVerion error: %v", err)
		return types.NewStatusMessage("error", err.Error(), nil)
	}

	params := sources.NewGetSourceScreenshotParams().
		WithSourceName(sourceName).
		WithImageFormat("png")
	sourceScreenshot, err := a.ObsClient.Sources.GetSourceScreenshot(params)
	if err != nil {
		log.Printf("GetSourceScreenshot error: %v", err)
		return types.NewStatusMessage("error", err.Error(), nil)
	}

	return types.NewStatusMessage("success", "Successfully loaded source screenshot", sourceScreenshot)
}

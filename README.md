# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）

この README はコードベースから抽出した情報をもとに作成した概要・導入手順・使い方・ディレクトリ構成です。

## プロジェクト概要
KabuSys は以下の主要機能を備えた自動売買プラットフォームの基盤実装です。

- シグナルに基づく発注エンジン（ExecutionEngine）
- kabuステーション向け REST / WebSocket クライアント（KabuStationClient）
- テスト用の Mock ブローカー（MockBrokerClient）を用いた paper_trading モード
- 注文状態の永続化（SQLite）とトランザクション設計
- 発注の三段階リスクガード（Gate1〜3：シグナル検査、実行レベル、約定後監視）
- 起動時のリコンシリエーション（Reconciler）でクラッシュ後の復旧を支援
- 監視ループ（SystemMonitor を想定）と監視 DB へのログ出力
- 環境設定ウィザード（.env 生成）と設定検証 CLI

## 主な機能一覧
- .env ウィザード（kabusys.config_setup）で初期設定を対話式に生成
- 設定検証ツール（kabusys.validate_config）で .env と config/*.yaml の検査
- ExecutionEngine：シグナル処理（発注）と WebSocket push ドレイン
- Broker クライアント群：
  - KabuStationClient（実運用想定、httpx + websocket）
  - MockBrokerClient（テスト・paper_trading 用、fill_mode 切替可能）
- OrderRecord / OrderRepository / OrderManager による注文ライフサイクル管理
- RiskManager によるレート制限・サーキットブレーカー・ドローダウン監視
- Reconciler による OrderSent の突合せとポジション差分検出
- データ処理モジュール（calendar_management, news_collector 等）

## 要件（目安）
- Python 3.9+
- 必須外部ライブラリ（一部は optional）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証で必要）
- 標準ライブラリ：sqlite3, logging, threading, pathlib 等

（実プロジェクトでは requirements.txt を用意して pip install -r で依存解決してください）

## セットアップ手順（ローカル開発向け・簡易）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML
     - （必要に応じて他パッケージも追加）
4. 環境変数ファイルを生成（対話ウィザード）
   - python -m kabusys.config_setup
   - 生成された .env を編集して実運用向けに値をセット
   - .env は Git にコミットしないでください（README にもウィザードが警告を出します）
5. 設定を検証
   - python -m kabusys.validate_config
   - 警告もFAIL扱いにする場合: python -m kabusys.validate_config --strict

## 設定（.env / 環境変数）
自動ロード順序（デフォルト）: OS 環境変数 > .env.local > .env  
プロジェクトルートは .git または pyproject.toml を基準に検出します。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

主要な環境変数（要点）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD : kabuステーション API パスワード
- 任意 / 推奨
  - KABUSYS_ENV : 実行環境（development / paper_trading / live）デフォルト: development
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : paper_trading 用 sqlite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
  - KILL_FLAG_CLEAR_ON_START : 起動時 kill.flag を自動クリアするか（0/1、デフォルト 0）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : 本番での通知設定
  - MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）

注意点
- KABUSYS_ENV=live 設定時は本番扱いになるため、LINE 通知等の設定や kill flag の取り扱いを慎重に確認してください（validate_config は live 時の追加チェックを行います）。
- .env にプレースホルダ（your_value や *_here）が残っていると警告になります。

.env の一例（ウィザードで生成される形式）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

## 使い方（主要 CLI / スクリプト）
- 設定ウィザード（.env の生成・更新）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict オプションで警告も FAIL 扱い（exit code 1）
- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - paper_trading / development 環境では MockBrokerClient が利用され、paper_trading 用 sqlite（PAPER_TRADING_SQLITE_PATH）に分離されます
- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定（デフォルト 60 秒）
- 開発 / テスト向けの操作
  - MockBrokerClient を直接用いたユニットテストが可能（fill_mode: instant/partial/never/reject）
  - ExecutionEngine の run_session を利用して制御したセッションテストが可能

プロセス制御関連ファイル
- PID ファイル（デフォルト）: data/execution.pid
- 停止フラグファイル: data/stop_requested.flag
- Kill flag: data/kill.flag（存在する場合の起動挙動は KILL_FLAG_CLEAR_ON_START によって変わる）

## 内部設計（簡易メモ）
- 注文ライフサイクル
  - OrderRecord（OrderState）で状態遷移を厳格に管理。無効な遷移は例外を投げる。
  - OrderManager は DB（OrderRepository）を介して OrderRecord を永続化し、ブローカー API 呼び出しの前後で一貫性を保つための二相永続化パターンを採用。
- リスク管理
  - Gate1: シグナルレベル（余力、重複、ポジション上限）
  - Gate2: 実行レベル（レート制限・サーキットブレーカー）
  - Gate3: 約定後のメトリクス（ドローダウン）チェック
- リコンシリエーション
  - 起動時に OrderSent の未確定注文を broker と突合して状態を回復
  - ブローカーポジションとの差分を検出して警告出力
- calendar_management: DuckDB を利用した営業日判定・JPX カレンダーの更新ロジック
- news_collector: RSS 収集（defusedxml や SSRF 対策を実装）

## ディレクトリ構成
（src/kabusys をルートとした主要ファイル／モジュール構成）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / 設定読み込み・Settings
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 起動前設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — SystemMonitor 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py            — Broker API データモデル・Protocol・ファクトリ
      - broker_factory.py        — Settings に応じたブローカ生成
      - kabu_client.py           — kabuステーション REST/WebSocket クライアント
      - mock_client.py           — MockBrokerClient（テスト用）
      - order_record.py          — 注文状態モデル・遷移ロジック
      - order_repository.py      — SQLite 永続化層
      - order_manager.py         — 注文管理（作成・送信・同期・取消）
      - execution_engine.py      — 発注エンジン（シグナル処理 + push ドレイン）
      - reconciler.py            — 起動時リコンシリエーション
      - risk_manager.py          — リスク制御ロジック
    - data/
      - calendar_management.py   — マーケットカレンダー処理（DuckDB）
      - news_collector.py        — RSS 収集・前処理
    - monitoring/
      - (monitoring_db / SystemMonitor 等は別ファイルとして実装想定)
    - utils/
      - logging_setup.py         — ロギング初期化ユーティリティ
      - process_priority.py      — プロセス優先度設定ユーティリティ
  - config/
    - *.yaml                     — 各種設定（system_config.yaml, data_config.yaml, etc.）
  - data/
    - kabusys.duckdb (デフォルト)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - *.pid / *.flag

validate_config では以下の config/*.yaml を想定して存在チェック・パース検証を行います:
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml

（config/*.yaml の雛形はプロジェクトに付属するスクリプト（例: scripts/generate_config.py）で生成する想定）

## 運用上の注意
- .env は秘密情報を含むため絶対にリポジトリへコミットしないでください。
- KABUSYS_ENV=live を設定する場合は LINE 等のアラート設定や Kill Switch の挙動を事前確認してください。
- 実運用ではプロセスマネージャ（systemd / supervisor / container 等）で実行・監視することを推奨します。
- run_execution/run_monitoring はファイルベースの stop フラグ（data/stop_requested.flag）や kill.flag を使って制御します。これらファイルによる制御を運用ルールとして整備してください。

---

必要であれば、README にサンプル .env.example、requirements.txt、起動用 systemd ユニットのサンプル、或いは config/*.yaml のテンプレート例を追加で作成します。どれが必要か教えてください。
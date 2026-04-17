# KabuSys

日本株自動売買システムの内部ライブラリ群（README）。  
このREADMEはリポジトリ内の主要スクリプト／モジュールの使い方・セットアップ手順・ディレクトリ構成をまとめたものです。

> 注意: 実行には外部パッケージ（duckdb, psutil, openai など）が必要です。requirements.txt がある場合はそれを使用してください。存在しない場合は下記手順を参照して個別にインストールしてください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 設定（環境変数と .env）
- 実行時の挙動メモ（paper_trading / live）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を組み合わせたシステムです。  
主な機能は次の通りです：

- 価格データ・財務データを用いたファクター計算（research）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ExecutionEngine による発注ロジック（本番／ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk モニタリング、Kill Switch）
- AI を用いたニュースセンチメント評価・レジーム検出（OpenAI）
- ペーパートレード検証レポート生成ツール

---

## 機能一覧（抜粋）

- research
  - calc_momentum, calc_volatility, calc_value：DuckDB の prices_daily/raw_financials を使ったファクター計算
  - calc_forward_returns, calc_ic：将来リターン・IC（情報係数）計算、特徴量解析
- portfolio
  - select_candidates、等重・スコア重み算出
  - セクター上限適用、レジームに応じた乗数計算
  - ポジションサイズ決定（risk_based / equal / score）
- execution
  - ExecutionEngine（発注エンジン）／OrderManager／RiskManager／Reconciler（実コードは別ファイルに実装）
  - BrokerClientFactory により KABUSYS_ENV=paper_trading 時は MockBroker を使用し、専用 DB に記録
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視 DB（monitoring_db）
  - KillSwitch によるフラグファイルで ExecutionEngine を停止可能
- ai
  - news_nlp: OpenAI を用いたニュースごとのセンチメントスコア化（ai_scores テーブルへ書込）
  - regime_detector: ETF とマクロニュースから市場レジームを判定して market_regime テーブルに永続化
- tools
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## セットアップ手順（簡略）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 可能なら requirements.txt を利用:
     - python -m pip install -r requirements.txt
   - 主要な依存例（個別インストール）:
     - python -m pip install duckdb psutil openai

   - 追加（任意）
     - PyYAML（config 検証で YAML をパースする場合）:
       - python -m pip install pyyaml

4. 初期設定（.env の作成）
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトでは data/*.db にファイルを作成します（例: data/kabusys.duckdb, data/monitoring.db）。必要に応じて .env でパスを上書きしてください。

---

## 使い方（主要コマンド）

以下はパッケージとして実行する例です（パッケージルートで実行してください）。

- 環境設定ウィザード（.env を生成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) で失敗扱いになります

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い、データは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）に分離
    - 実行前に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中は data/execution.pid に PID を書きます（Settings.pid_file_path で変更可）
    - 停止は data/stop_requested.flag を作成することで受付（run_execution はフラグを監視）

- Monitoring の起動（監視ループ）
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可（デフォルト 60 秒）
  - 挙動:
    - 監視は本番 sqlite_path を常に使用（KABUSYS_ENV に依存しない）
    - data/stop_requested.flag が存在するとループ終了

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能（--db が優先）

- AI 機能（一例）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼ぶ
  - OpenAI API を使うために環境変数 OPENAI_API_KEY を設定してください（または各関数の api_key 引数で指定）

---

## 設定（環境変数）

主な必須・重要な環境変数：

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 動作モード
  - KABUSYS_ENV — 実行環境（development, paper_trading, live）。デフォルト: development

- DB パス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用、デフォルト: data/paper_trading.db）

- ロギング
  - LOG_LEVEL — DEBUG/INFO/...

- AI
  - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時に必須）

- モニタリング/キルスイッチ
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
  - PID_FILE_PATH — 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

- その他
  - PAPER_FILL_MODE — Paper Trading 時の fill 動作（instant|partial|never|reject）

.env の自動読み込みについて:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）が検出される場合、起動時に .env → .env.local の順で自動ロードされます（OS 環境変数は上書きされません）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 実行時の挙動メモ

- paper_trading モード
  - 発注はモック（MockBroker）で擬似的に記録され、本番の監視 DB と分離して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。
  - Paper 検証レポートはこの DB を参照します。

- Kill Switch / 停止フラグ
  - KillSwitch は Monitoring の評価結果に基づき data/kill.flag を作成し、ExecutionEngine 側で検出して安全に停止させる仕組みです。
  - 管理者が手動で停止させるには data/stop_requested.flag を作成してください（run_execution / run_monitoring の両方がこれを監視します）。

- PID ファイル
  - ExecutionEngine 起動時に PID をファイルに書きます。SystemMonitor はこの PID ファイルの存在とプロセスの存否から Execution プロセスの健全性を判断します。スタレ PID を検出するとファイルを削除しログに記録します。

- ログレベル
  - Settings.log_level に従います。環境変数 LOG_LEVEL で調整可能です。

---

## ディレクトリ構成（抜粋）

以下はソース内の主要ファイル・モジュール構成の概略です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 関連ユーティリティ
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI 経由）
    - regime_detector.py     — 市場レジーム判定（LLM + ETF MA）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py       — （実装ファイルあり）
    - kill_switch.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py
  - execution/
    - （ExecutionEngine / BrokerFactory / OrderManager 等の実装ファイル — 実装は別ファイル群）
  - data/
    - （データベースファイルや PID/flag を置く想定ディレクトリ、例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）

（実際のファイル一覧はリポジトリの tree コマンド等で確認してください）

---

## 開発・運用上の注意

- production（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config は live 時に追加警告を出します。
- .env は機密情報（API トークン、パスワード）を含むため、決して Git にコミットしないでください。
- OpenAI を使用する機能は API コストがかかります。API キーの管理とコール頻度に注意してください。
- DuckDB / SQLite はローカルファイルベースの DB です。並列書込み時の制約やバージョン互換性（特に executemany の空リスト等）に留意しています（コード内に互換処理あり）。
- process priority / cpu affinity の設定は OS により権限が必要な場合があります。設定に失敗してもスキップされます。

---

この README はリポジトリ内のコードから抽出した情報に基づき作成しています。詳細な実装や追加オプションは各モジュールの docstring / 関数ドキュメントを参照してください。必要であれば README にサンプルコマンドやより詳細な運用手順を追記しますのでお知らせください。
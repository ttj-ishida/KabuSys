# KabuSys — README

本リポジトリは日本株の自動売買・リサーチ・監視を目的とした軽量フレームワークです。  
この README ではプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成された自動売買システムのプロトタイプです。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカーとの同期・リコンシリエーション（Reconciler）
- 注文管理（OrderManager / OrderRepository）
- リスク管理（RiskManager / Risk 関連ユーティリティ）
- 監視（MonitoringEngine）とダッシュボード（Streamlit ベース）
- DuckDB を用いたリサーチ（ファクター計算・特徴量解析）
- OpenAI を使ったニュース NLP（センチメントスコアリング）および市場レジーム判定
- プロセス優先度・CPU affinity のユーティリティ、各種ヘルパー

設計方針としては、DB の読み書きとビジネスロジックを分離し、外部 API 呼び出しは必要最小限に抑え、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- Execution（発注）
  - Signal Queue Pull 型の発注ループ（シグナル処理時間帯の Gate チェック、push drain）
  - 発注状態の永続化（クラッシュ耐性を考慮した2相的永続化）
  - Reconciler による起動時の自動復旧（OrderSent 等の同期、ポジション差分検出）
- Monitoring（監視）
  - SystemMonitor：CPU/Mem/Disk、プロセス死活、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格チェック
  - RiskMonitor：ドローダウン・ポジション上限の継続監視と alert ログ化
  - KillSwitch：条件に応じて kill.flag を書き込み ExecutionEngine 停止シグナル送出
  - AlertManager：LINE Push を用いたアラート通知（クールダウン管理）
  - Streamlit ダッシュボード（data/monitoring.db を参照）
- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリー
- AI（OpenAI）
  - ニュースのセンチメント集約と ai_scores 書き込み（news_nlp）
  - マクロニュース + ETF MA200 による市場レジーム判定（regime_detector）
- ユーティリティ
  - 環境設定の自動ロード（.env / .env.local）
  - process priority / CPU affinity 設定ユーティリティ
  - SQLite（monitoring DB）初期化ユーティリティ

---

## 必要条件（主な依存ライブラリ）

- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
-（その他、実行環境に応じたドライバ等）

※ requirements.txt が無ければ下記を個別にインストールしてください。
例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（例）。
   - pip install duckdb psutil requests openai streamlit

3. 環境変数の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須 / J-Quants API 用）
     - KABU_API_PASSWORD: （必須 / kabuステーション API 用）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（任意）
     - SQLITE_PATH: monitoring DB path（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB path（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite path（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 動作指定、デフォルト: instant）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）

   - 例 .env（最小）
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development

4. DB 初期化
   - Monitoring 用 SQLite と DuckDB のファイルは実行時に自動作成・テーブル初期化されます（init_monitoring_db を使用）。

---

## 使い方 / 実行方法

※ ソースが `src/` 配下にある想定のコマンド例を示します。プロジェクトルートで `PYTHONPATH=src` を指定するか、パッケージとしてインストールしてください。

- ExecutionEngine（発注エンジン）を起動する
  - 環境: 本番は KABUSYS_ENV=live、テスト/検証は KABUSYS_ENV=paper_trading（この場合は MockBroker を使用し、paper DB に記録され本番 DB と分離されます）
  - コマンド例:
    PYTHONPATH=src python -m kabusys.run_execution
  - 補足:
    - 起動時に PID ファイル（Settings.pid_file_path、デフォルト data/execution.pid）を書きます。
    - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を削除できます（ExecutionEngine 側で処理されています）。
    - Reconciler による起動時復旧やリスクチェックが実行されます。

- MonitoringEngine（監視ループ）を起動する
  - 環境変数でポーリング間隔を変更可能: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - コマンド例:
    PYTHONPATH=src python -m kabusys.run_monitoring
  - 補足:
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
    - SystemMonitor が PID ファイルの stale 判定やデータ鮮度チェックを行い、RiskMonitor / TradeMonitor と連携して kill.flag 書き込みや LINE 通知を行います。

- Streamlit ダッシュボード（監視 UI）
  - 起動例（プロジェクトルートから）:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、最近のポジション・注文・システムステータス・リスクログを表示します。

- AI / リサーチ バッチ
  - news_nlp.score_news(conn, target_date, api_key=None) を呼び、raw_news→ai_scores にスコアを書き込む（OpenAI API キーが必要）。
  - regime_detector.score_regime(conn, target_date, api_key=None) で市場レジームを計算して market_regime に書き込む。

---

## 主な設定（環境変数一覧・説明）

- KABUSYS_ENV: development | paper_trading | live（必須ではないが値が不正だと例外）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp/regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（空なら送信せずログのみ）
- DUCKDB_PATH（例: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、例: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定シミュレーション）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒）

---

## 開発・運用上の注意点

- .env 自動ロード
  - プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数優先）。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper trading
  - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient を使用し、専用の SQLite（デフォルト data/paper_trading.db）へ記録されます。本番 DB と完全に分離されます。
- Kill switch
  - RiskMonitor 等が条件を満たすと kill.flag に理由を書き込みます。ExecutionEngine は起動時やループ中に kill.flag を検出すると安全終了を行います。
- OpenAI
  - OpenAI 呼び出しは再試行やフェイルセーフの実装があるものの、API キーは必須です（スコア処理はキー無しだと例外）。
- DB 初期化・マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成します。軽微なスキーマ追加（例: dashboard.peak_value）についてはランタイムで ALTER を試みます。

---

## 主要モジュール・ファイル一覧（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py, broker_api.py（ブローカー抽象）
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py, alert_manager.py, kill_switch.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- utils/
  - process_priority.py

（実際のプロジェクトではさらに data/, docs/, scripts/ 等が存在する可能性があります）

---

## よくある操作・コマンド例

- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- ExecutionEngine を起動（paper_trading で起動する例）
  - export KABUSYS_ENV=paper_trading
  - export OPENAI_API_KEY=...
  - PYTHONPATH=src python -m kabusys.run_execution

- MonitoringEngine をバックグラウンドで起動
  - export MONITOR_POLL_INTERVAL=30
  - PYTHONPATH=src python -m kabusys.run_monitoring &

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- kill.flag を手動で解除（ローカル運用時）
  - rm data/kill.flag
  - ※ 実運用では KillSwitch の clear() を利用するか、必要に応じて起動オプションでクリアさせてください（KILL_FLAG_CLEAR_ON_START）。

---

もし README に追加してほしい内容（例: CLI オプション詳細、サンプル .env.example、単体テストの実行方法、デプロイ手順など）があれば教えてください。必要に応じて追記します。
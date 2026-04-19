# KabuSys

日本株向け自動売買システムの一部をまとめたリポジトリ用 README。  
このドキュメントは、提供されたコードベース（src/kabusys 以下）を基に日本語で作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視機能を備えたシステムの集合体です。主な機能は以下です。

- 自動発注を行う ExecutionEngine（実運用 / ペーパートレード対応）
- システム稼働状況、データ鮮度、発注ログ等を記録・監視する Monitoring コンポーネント
- ポートフォリオ構築（候補選定、重み付け、株数計算、セクター制限 等）
- リサーチ（ファクター計算、将来リターン、特徴量解析）
- AI を使ったニュースセンチメント解析・市場レジーム判定（OpenAI API）
- 補助ツール（.env ウィザード、設定検証、Paper Trading の検証レポート生成 等）

設計上のポイント:
- .env ベースの設定管理（Settings クラス）
- DuckDB（分析用）と SQLite（監視・発注ログ）を併用
- 本番／ペーパートレードは DB を分離して運用可能
- OpenAI API を用いた NLP 機能（API キー必須）
- プロセス優先度やログ設定のユーティリティを提供

---

## 機能一覧（主要コンポーネント）

- 実行・発注
  - run_execution.py — ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用し `data/paper_trading.db` に記録
    - PID ファイル、停止フラグによる制御
- 監視
  - run_monitoring.py — SystemMonitor のポーリングループ
    - MONITOR_POLL_INTERVAL でポーリング間隔を調整（デフォルト 60 秒）
    - System / Trade / Risk モニタリング、kill.flag 生成による停止シグナル
- 設定管理
  - config_setup.py — 対話式 .env ウィザード（.env の初期作成・更新）
  - validate_config.py — 起動前の設定検証 CLI（--strict オプションあり）
  - config.Settings — 環境変数読み取り・検証（KABUSYS_ENV、DB パス、しきい値等）
- ツール
  - tools/paper_verification_report.py — ペーパートレードの検証レポート生成
- ポートフォリオ構築
  - portfolio/*.py — 候補選定、重み計算、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ
  - research/*.py — ファクター計算（モメンタム、バリュー、ボラティリティ）、特徴量解析（IC 等）
- AI
  - ai/news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に保存
  - ai/regime_detector.py — マクロニュース + ETF MA を使った市場レジーム判定
- 永続化（監視）
  - monitoring/monitoring_db.py — SQLite を用いた監視ログ CRUD（マイグレーション含む）
  - monitoring/* — RiskMonitor、SystemMonitor、TradeMonitor、MonitoringEngine、KillSwitch、AlertManager（概要に準拠）

ユーティリティ:
- utils/logging_setup.py — 共通ログ設定（コンソール + 日次ローテートファイル）
- utils/process_priority.py — プラットフォーム非依存の優先度設定（psutil 使用）

---

## セットアップ手順

前提
- Python 3.10 以上（型記法に | を使用）
- SQLite は標準ライブラリで利用可能
- 必要な外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
  - （必要に応じて）その他のランタイム依存

1. リポジトリをクローン
   - git clone <repository-url>
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があれば `pip install -r requirements.txt`）
4. データ / ログ ディレクトリを作成（任意）
   - mkdir -p data logs
   - デフォルト SQLite/DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading DB: data/paper_trading.db
   - ログディレクトリ: logs/
5. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を環境変数に設定（または別途渡す）
6. 設定確認
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL として扱います

注意:
- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか
- paper_trading モードは本番発注を行わず専用 DB（PAPER_TRADING_SQLITE_PATH）に記録

---

## 使い方（起動・代表的なコマンド）

基本的にモジュールは Python の -m を使って起動します。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存（paper_trading では MockBroker を使用）
  - 起動時に data/execution.pid（デフォルト）が作成されます。停止は data/stop_requested.flag または kill.flag による制御

- Monitoring（システム監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能の利用
  - news_nlp.score_news(conn, target_date, api_key=None)
    - OpenAI API キーが必要（引数か環境変数 OPENAI_API_KEY）
  - regime_detector.score_regime(conn, target_date, api_key=None)

ログ:
- デフォルトではコンソール出力（stdout）と logs/<app_name>.log 日次ローテーションに出力
- ログレベルは LOG_LEVEL 環境変数で指定（デフォルト INFO）

停止・Kill Switch：
- KillSwitch は設定により特定条件（ドローダウン超過等）で data/kill.flag を書き込み、ExecutionEngine に停止を指示します。
- 手動停止フラグ: data/stop_requested.flag を作成すると起動中のスクリプトが検知して終了します。

---

## 主要環境変数（抜粋・デフォルト）

- KABUSYS_ENV: execution モード（development / paper_trading / live） — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API base URL — default: http://localhost:18080/kabusapi
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時、必須）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject — default: instant
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL — default: INFO
- MONITOR_POLL_INTERVAL: 監視ループの秒数 — default: 60
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など

詳しくは `src/kabusys/config.py` を参照してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイル・パッケージと役割の一覧です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/設定管理（Settings）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — 優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（監視ログ）
    - monitoring_engine.py — 監視エンジン（各 Monitor の統合）
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション制限監視
    - kill_switch.py — kill.flag の生成/管理
    - （trade_monitor, alert_manager 等のファイルが想定される）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数・資金配分計算
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計要約
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - data/（実行時に使用するディレクトリ）
    - monitoring.db（SQLite）
    - paper_trading.db（ペーパートレード用 SQLite）
    - kabusys.duckdb（DuckDB）
    - stop_requested.flag / kill.flag / execution.pid 等

---

## 開発上の注意点・運用メモ

- 環境変数の自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動でロードします。
  - テスト等で自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 本番運用（KABUSYS_ENV=live）
  - LINE 通知や Kill Switch の設定等、本番向けのガードがあります。validate_config で注意喚起が行われます。
- OpenAI 連携
  - API 呼び出しはリトライ・エラーハンドリングを実装していますが、API 使用料やレート制限に注意してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は既存 DB に対して必要なカラム追加を行う簡易マイグレーションを備えています。
- ログ
  - logs/<app_name>.log に日次ローテーションで出力。ログディレクトリの作成に失敗した場合はコンソールのみの出力になります。

---

必要に応じて README に追加したい具体項目（例: 実行例ログ、設定ファイルのテンプレート、より詳細な API 使用例）があれば教えてください。README の拡張や英語版作成も対応できます。
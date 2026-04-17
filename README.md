# KabuSys

KabuSys は日本株向けの自動売買／研究プラットフォームの一部です。本リポジトリには、ポートフォリオ構築・ポジションサイズ計算、リサーチ用ファクター計算、AI ベースのニュースセンチメント/R egime 判定、実行エンジン起動スクリプト、監視エンジンなどの主要コンポーネントが含まれています。

注意: 本 README はリポジトリ内の主要モジュールに基づいて作成しています。実際の運用では各種 API キーや本番設定の取り扱いに十分ご注意ください。

## 概要（Project Overview）
- 名称: KabuSys
- 目的: 日本株の自動売買を支援するライブラリ／実行環境。戦略のリサーチ（DuckDB ベースのファクター計算）、ポートフォリオ構築、発注ロジック、ペーパートレード機能、監視・アラート、AI を用いたニュース解析などを提供します。
- 実行形態:
  - 実取引 (KABUSYS_ENV=live)
  - ペーパートレード (KABUSYS_ENV=paper_trading) — MockBroker を用い、本番 DB とは分離して data/paper_trading.db を使用
  - 開発（KABUSYS_ENV=development） — ローカル検証向け

## 主な機能一覧（Features）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 環境に応じて実ブローカまたは MockBroker を選択
  - paper_trading 時は専用 SQLite DB を使用
  - プロセス優先度設定、PID 管理、停止フラグ検知
- Monitoring 起動スクリプト（run_monitoring.py）
  - System/Trade/Risk の監視コンポーネントをポーリング
  - 監視結果を SQLite（monitoring.db）へ永続化
  - 簡易 Kill Switch（kill.flag）で ExecutionEngine 停止指示を発行
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視 DB 層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard 等のテーブル作成・ラッパー
- RiskMonitor / TradeMonitor / SystemMonitor
  - ドローダウン監視・ポジション上限・滞留注文・約定異常などを検出しログ／アラートを生成
- AlertManager
  - LINE Messaging API によるプッシュ通知（トークン未設定時はログ出力のみ）
- Portfolio モジュール
  - 候補銘柄選定、等配分／スコア配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research モジュール
  - DuckDB を用いたファクター計算 (momentum / volatility / value) や特徴量解析（IC, forward returns など）
- AI モジュール
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメントスコアリング（ai_scores テーブルへ書き込み）
  - regime_detector: ETF マーケット指標 + マクロニュースを組み合わせた市場レジーム判定（market_regime へ書き込み）
- 補助ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境変数 / config/*.yaml の事前検証 CLI
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成

## セットアップ手順（Setup）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要な依存パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - requests
     - openai
     - PyYAML（config の検証をフルに行う場合に必要）
   - 例:
     - pip install duckdb psutil requests openai PyYAML
   - ※ requirements.txt がある場合は pip install -r requirements.txt を利用してください。
4. .env の作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - もしくはリポジトリ直下の .env.example を参考に手動作成
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH（必要に応じて）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラートを有効化する場合）
   - 自動 .env ロードはデフォルトで有効。テスト等で無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証（オプション）
   - python -m kabusys.validate_config
   - 警告も FAIL として扱う場合:
     - python -m kabusys.validate_config --strict

## 使い方（Usage）
- 実行エンジン（ExecutionEngine）を起動
  - デフォルト: python -m kabusys.run_execution
  - 動作概要:
    - KABUSYS_ENV に応じて broker クライアントを作成
    - paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - data/stop_requested.flag が存在すると起動を中止または停止
    - data/execution.pid に PID を書き出してプロセスの存在を監視
- 監視ループ（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（KABUSYS_ENV に依存しない）
  - 監視により条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）を作成し、ExecutionEngine に停止指示を与える
- 停止／強制停止
  - run_execution / run_monitoring のループ停止にはプロセス終了（Ctrl+C）または data/stop_requested.flag の作成で制御
  - ExecutionEngine の安全停止シグナル（実行側が kill.flag を見て停止する設計）
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
- AI 機能（プログラム API）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を受け取り、DB 内のテーブル（raw_news, prices_daily など）を参照／更新します。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

## ディレクトリ構成（Directory Structure）
以下は本リポジトリの主要ファイル／ディレクトリ（src/kabusys 以下）の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数の読み込み・Settings 定義（.env 自動読込含む）
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・スケールダウンロジック
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py  — forward returns / IC / summary 等
  - ai/
    - news_nlp.py             — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py      — マクロ + ma200 によるレジーム判定（OpenAI 補助）
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 初期化・CRUD ラッパー
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム稼働・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の書き込み（Execution 停止）
    - alert_manager.py        — LINE Push 通知ユーティリティ
  - execution/                — 発注関連（OrderManager/ExecutionEngine 等） — 実装の詳細に依存
  - utils/
    - process_priority.py     — プラットフォーム横断のプロセス優先度設定ユーティリティ
  - data/                     — 実行時生成データ（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）

（注）上記は主要ファイルの抜粋です。細かいモジュールや補助スクリプトはリポジトリ内をご参照ください。

## 運用上の注意
- 本番運用（KABUSYS_ENV=live）の前に必ず validate_config.py で設定を検証してください。
- .env は絶対にバージョン管理にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- OpenAI キーや API パスワード等の機密情報は安全に管理してください。
- run_execution/run_monitoring の停止は stop_requested.flag を使うかプロセスの終了で行えます。kill.flag は監視が生成する「発注エンジン停止」用のフラグです。KILL_FLAG_CLEAR_ON_START=1 は便利ですが本番では推奨されません。
- DuckDB / SQLite ファイルのパス（デフォルト data 以下）は validate_config.py で親ディレクトリ存在の警告が出ます。必要に応じて事前に作成してください。

---

問題や追加のドキュメント（API 使用例、設定項目の詳細、運用手順書など）が必要であればお知らせください。README の補助的な章（例: CLI 引数詳細、サンプル .env、よくあるトラブルシュート）を追加できます。
KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買システム（KabuSys）の主要モジュール群を含みます。
設計は本番運用を意識しており、発注・監視・リスク管理・ポートフォリオ構築・リサーチ・AI（ニュースNLP/レジーム判定）などの機能が分離されたモジュールで実装されています。

主な特徴
--------
- Execution: 注文作成／送信／同期（再起動時のリコンシリエーションを含む）
- Monitoring: システム状態・データ鮮度・注文滞留・リスクイベントのポーリング監視とログ永続化（SQLite）
- Risk: ドローダウン / ポジション上限の検出とアラート連携（LINE push）
- Portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター制限・レジーム乗数
- Research: DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）と特徴量分析
- AI: OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
- Tools: Paper Trading の検証レポート生成スクリプト、Streamlit ベースの監視ダッシュボード

準備 / セットアップ
-------------------
1. Python 環境
   - Python 3.9+ を推奨（duckdb / psutil / openai 等に依存）
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（推奨パッケージ）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit (ダッシュボードを使う場合)
   - （必要に応じて）pytest など
   例:
     pip install duckdb psutil requests openai streamlit

   ※ requirements.txt は付属していません。上記を参考に環境へインストールしてください。

3. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数より低優先、.env.local は上書き）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用
     - KABU_API_PASSWORD: kabuステーション API 用
     - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時必須）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
     - SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading 動作（instant | partial | never | reject）
     - PID_FILE_PATH: ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: kill.flag ファイルパス（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト 60）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方
------
1. 監視プロセス起動（Monitoring）
   - 監視専用スクリプト:
     - python -m kabusys.run_monitoring
   - 概要:
     - Settings から設定を読み、SQLite（monitoring DB）と DuckDB に接続。
     - SystemMonitor を中心に定期ポーリング（MONITOR_POLL_INTERVAL 環境変数で秒数上書き可、デフォルト 60 秒）。
     - 起動時にプロセス優先度を "high" に設定しようとします（プラットフォーム依存）。

2. ExecutionEngine 起動（取引エンジン）
   - 実行スクリプト:
     - python -m kabusys.run_execution
   - Paper Trading モード:
     - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に完全分離して記録します。
   - 動作:
     - Broker クライアントを生成 → OrderRepository / OrderManager / RiskManager / Reconciler を組み立て → ExecutionEngine を起動し run_session を実行します。
     - 起動時に PID ファイルを書き、終了時に削除する想定。

3. Paper Trading 検証レポート
   - スクリプト:
     - python -m kabusys.tools.paper_verification_report
     - オプション:
       --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - 説明:
     - paper_trading DB（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL を判定し出力します。

4. 監視ダッシュボード（Streamlit）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードでは positions / recent orders / system status / risk logs / dashboard メトリクスを表示します（読み取り専用で DB を開きます）。

注意点・特徴
-------------
- Settings（kabusys.config）:
  - .env 自動読み込み（.git または pyproject.toml を基準にプロジェクトルートを探します）。
  - KABUSYS_ENV は development / paper_trading / live のいずれかで検証されます。
  - paper_trading 環境では本番 DB と分離して paper_trading 用 SQLite を使用します。
- DB 初期化:
  - monitoring_db.init_monitoring_db() は冪等にテーブルと必要なマイグレーション（カラム追加）を行います。
- プロセス優先度 / CPU affinity:
  - utils/process_priority.py がプラットフォーム差を吸収して優先度や CPU affinity を設定します（権限不足時は警告を出してスキップ）。
- Kill Switch:
  - リスク条件（ドローダウン等）で data/kill.flag を書き込み、ExecutionEngine に停止を促す仕組みがあります（KillSwitch クラス）。
- AI モジュール:
  - OpenAI を利用します。API 呼び出しはエラー時にリトライやフォールバック（例: macro_sentiment=0）を行い、部分失敗でも他データを保護する実装です。
  - OPENAI_API_KEY が未設定だと関連機能は例外を投げます。テスト時は API 呼び出しをモック可能です。

主要スクリプト（エントリーポイント）
-----------------------------------
- python -m kabusys.run_monitoring   — 監視ポーリングループ起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）
- python -m kabusys.run_execution    — ExecutionEngine 起動（KABUSYS_ENV により paper_trading での分離動作）
- python -m kabusys.tools.paper_verification_report  — Paper Trading 検証レポート（オプションで期間指定）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db PATH  — 監視ダッシュボード

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / .env ローディング・Settings
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                   — ニュースセンチメント / OpenAI 呼び出し
  - regime_detector.py            — 市場レジーム判定（ma200 + macro_sentiment）

- execution/
  - order_manager.py
  - order_repository.py           — (参照されるがソース省略)
  - reconciler.py                 — 起動時リコンシリエーション
  - ...                           — broker_factory 等（実装に依存）

- monitoring/
  - __init__.py
  - monitoring_db.py              — SQLite テーブル作成・CRUD ヘルパ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py              — LINE 通知
  - monitoring_engine.py          — 各 Monitor を束ねる
  - streamlit_dashboard.py        — Streamlit ダッシュボード

- portfolio/
  - __init__.py
  - portfolio_builder.py          — 候補抽出・重み計算
  - position_sizing.py            — 株数計算・集約キャップ
  - risk_adjustment.py            — セクターキャップ・レジーム乗数

- research/
  - __init__.py
  - factor_research.py            — ファクター計算（momentum/value/volatility）
  - feature_exploration.py        — IC / 将来リターン / 統計サマリー

- tools/
  - __init__.py
  - paper_verification_report.py  — Paper Trading レポート生成

- utils/
  - __init__.py
  - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ

補足・運用メモ
--------------
- Paper Trading モードは本番 DB と完全分離することを意図しています。必ず KABUSYS_ENV=paper_trading を指定してください。
- monitoring_db.init_monitoring_db() は既存 DB の互換性を保つために簡単なマイグレーション（カラム追加）を行います。
- OpenAI 呼び出し部分は API のレート制限やエラーに対する耐性（リトライ・バックオフ）を持たせていますが、実運用では API 利用コスト・キー管理に注意してください。
- LINE 通知はトークン / ユーザID 未設定時は送信をスキップします。大量アラートを防ぐため内部でクールダウンを持っています。

ライセンス / 貢献
-----------------
- 本リポジトリにライセンス表記がない場合は、利用前にライセンス方針をプロジェクト管理者に確認してください。
- バグ修正や機能追加の際はモジュール分離に留意して PR を作成してください。

以上。README に記載してほしい追加項目（例: より詳細な実行例、環境変数テンプレート、requirements.txt など）があれば教えてください。必要に応じて .env.example の雛形も作成します。
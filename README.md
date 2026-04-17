# KabuSys

日本株自動売買システム（ライブラリ + 実行コンポーネント）のリポジトリ。  
この README はソースツリーから取得できる情報に基づき作成しています。

## プロジェクト概要
KabuSys は自動売買のための以下の主要機能を持つ Python プロジェクトです。

- シグナル → 発注までの Execution Engine（ブローカークライアント抽象化）
- 監視（System / Trade / Risk）とアラート（LINE Push）
- Paper Trading 用の完全分離された DB とモックブローカー動作
- ポートフォリオ構築（候補選定、重み計算、株数算出）
- リサーチ用ファクター計算（DuckDB を利用した時系列処理）
- ニュース NLP / レジーム判定（OpenAI を利用した LLM スコアリング）
- 検証用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主要な設計方針の一例：
- DuckDB / SQLite をデータ層に利用（ローカルでの解析・永続化）
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- LLM 呼び出しは堅牢（リトライ・バリデーション・部分書き込み）に実装

## 機能一覧
- Execution
  - ブローカー抽象化（実ブローカー / MockBroker）
  - OrderManager / ExecutionEngine / Reconciler（自動リコンシリエーション）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク・プロセス・データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件で ExecutionEngine 停止フラグを書き込み）
  - AlertManager（LINE プッシュ通知）
  - Streamlit ダッシュボード（監視 DB を可視化）
- Portfolio
  - 候補選定、等配分 / スコア重み、リスク調整、株数決定（単元丸め、集約キャップ）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースセンチメントスコアリング（OpenAI を利用）
  - 市場レジーム判定（MA + マクロニュースセンチメント合成）
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成

## セットアップ手順（ローカル開発）
1. Python バージョン  
   - Python 3.10 以上を推奨（型ヒントで | が使われています）。

2. 必要なパッケージ（例）
   - duckdb, psutil, openai, requests, streamlit
   - インストール例:
     pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt がない場合は上記を手動でインストールしてください）

3. 環境変数の設定  
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既存の OS 環境変数は上書きされません）。  
   - 自動読み込みを無効にする場合:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI API を使う機能（ニュース NLP / レジーム判定）
   - その他（任意/デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定モード
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH, KILL_FLAG_PATH など

5. データディレクトリ  
   - data/ 以下に DB・フラグファイル・PID ファイルを配置することを想定しています。必要に応じてディレクトリを作成してください。

## 使い方（主要な実行方法）
各スクリプトはパッケージモードで実行できます。

- 監視ループを起動（Monitoring）
  - 実行:
    python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
    - 監視は KABUSYS_ENV に関わらず常に production の sqlite_path（Settings.sqlite_path）を使用します。
    - プロセス優先度を上げて実行します（可能な範囲で）。

- Execution Engine を起動
  - 実行:
    python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
    - 起動時に data/execution.pid が書かれ、停止指示は data/stop_requested.flag または data/kill.flag で受け付けます。
    - プロセス優先度を上げて実行します。

- Streamlit ダッシュボード（監視 DB の可視化）
  - 実行:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 補足:
    - 読み取り専用モードで DB を開きます。MonitoringEngine が DB を書き込んでいることが前提です。

- Paper Trading 検証レポート生成
  - 実行:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 補足:
    - デフォルト DB: data/paper_trading.db。--db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI 関連関数（プログラムから呼び出す）
  - ニュース NLP スコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 補足:
    - DuckDB 接続（duckdb.connect(...).cursor/connection）を渡して使用します。
    - OpenAI API キーは引数で与えるか環境変数 OPENAI_API_KEY を利用します。
    - LLM 呼び出しはリトライやバリデーション処理を行い、部分的失敗時でも既存データを破壊しない設計になっています。

## フラグ / 停止制御
- data/stop_requested.flag
  - run_monitoring と run_execution が参照している停止フラグファイル。存在するとループを終了します（順次停止）。
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine に対する停止要求を表します。KillSwitch.clear() で削除可能です。
- data/execution.pid
  - ExecutionEngine の PID を記録。SystemMonitor は PID の有無および生存チェックを行います（stale PID の除去・アラート）。

## データベース・マイグレーション
- monitoring_db.init_monitoring_db(conn) により監視用テーブル群を冪等で作成します。既存テーブルへのカラム追加（例: peak_value, latency_ms）も自動で行う簡単なマイグレーションを含みます。

## 主要な環境変数（まとめ）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API
- KABU_API_PASSWORD: kabuステーション API
- OPENAI_API_KEY: OpenAI API key（AI 機能で使用）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（Paper Trading 用 DB）
- SQLITE_PATH: data/monitoring.db（監視用 DB）
- DUCKDB_PATH: data/kabusys.duckdb
- PID_FILE_PATH, KILL_FLAG_PATH, MONITOR_POLL_INTERVAL, LOG_LEVEL, など

## ディレクトリ構成
（主要ファイルの抜粋と説明）

- src/kabusys/
  - __init__.py — パッケージ情報（__version__ 等）
  - config.py — 環境変数 / 設定の解決ロジック（.env 自動読み込み含む）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite レイヤ（永続化）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセスチェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — LINE Push 送信・クールダウン管理
    - kill_switch.py — 停止フラグの書き込み
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ... — 発注・注文状態管理・リコンシリエーション
    - broker_factory / broker_api — ブローカークライアント抽象化
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数算出・集約 cap
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースの LLM によるセンチメントスコアリング
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他、execution や data 周りに多数の補助モジュールが含まれます。上記は主要なものの抜粋です。

## 注意事項 / 運用メモ
- Paper Trading は本番 DB と分離しています。KABUSYS_ENV=paper_trading を利用してください。
- monitoring は常に Settings.sqlite_path（本番パス）を参照します。意図して paper DB を監視しないため注意してください。
- OpenAI 等の外部 API を呼ぶ機能は API キーとネットワーク接続が必要です。エラー時はフェールセーフ（ゼロ埋め・スキップ）動作を多く取り入れていますが、設定は慎重に行ってください。
- .env のパースは .env ファイルの一般的な記法（エクスポート形式・クォート・コメント）をサポートします。OS 環境変数は優先されます。
- プロセス優先度 / CPU affinity の設定は psutil を介して行います。権限不足で失敗することがありますが、その場合はログに警告が出力され動作は継続します。

---

不明点や README に追加したい内容（例: 各コマンドの詳細オプション、CI/デプロイ手順、サンプル .env）などがあれば教えてください。必要に応じてサンプル .env や運用手順書を追加で作成します。
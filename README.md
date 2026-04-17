KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買システム「KabuSys」のコードベースの一部です。取引エンジン（ExecutionEngine）、監視（Monitoring）機能、ポートフォリオ構築ユーティリティ、ファクター計算・リサーチ、AI（ニュース NLP / レジーム検出）などを含む設計になっています。

主な特徴
--------
- ExecutionEngine
  - ブローカー API 経由での発注管理、オーダー状態遷移、再起動時のリコンシリエーション（Reconciler）
  - paper_trading モード（本番 DB と分離した MockBroker による検証）
- Monitoring
  - システム状態（CPU/メモリ/ディスク・プロセス生存）の定期記録
  - 注文滞留・約定異常やリスク（ドローダウン・ポジション上限）の監視
  - KillSwitch（フラグファイルで ExecutionEngine を停止）
  - LINE 通知によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（監視画面）
- Portfolio コンポーネント（候補選定、重み計算、位置サイズ算出、セクター制限、レジーム乗数）
- Research（DuckDB を使ったファクター算出、将来リターン、IC 計算、統計サマリー）
- AI モジュール
  - ニュース記事のセンチメント評価（OpenAI API を利用、スコアを ai_scores に保存）
  - レジーム判定（ETF MA とマクロセンチメントを合成）
  - 冪等性・リトライ・パース耐性などフェイルセーフ設計
- ユーティリティ
  - Settings（.env 自動読み込み / 環境変数管理）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

セットアップ手順
--------------
以下は一般的なセットアップ手順です（環境に応じて調整してください）。

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - requirements.txt が用意されている想定のため:
     - pip install -r requirements.txt
   - 本プロジェクトで典型的に必要なライブラリ:
     - duckdb, psutil, requests, openai, streamlit

4. 環境変数設定 (.env)
   - プロジェクトルートの .env または .env.local に設定を追加します。
   - 自動読み込みのルール: OS 環境 > .env.local > .env
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 重要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - OPENAI_API_KEY — OpenAI（ニュース NLP / レジーム検出）
     - KABUSYS_ENV — 起動環境 (development | paper_trading | live)
     - PAPER_FILL_MODE — paper_trading の約定モード (instant | partial | never | reject)
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH など

5. データディレクトリ作成
   - data フォルダを作る（例: mkdir -p data）
   - run スクリプトが DB ファイルやフラグファイルを作成します。

使い方（主要コマンド・呼び出し例）
-----------------

- 監視ループを起動（run_monitoring）
  - 実行: python src/kabusys/run_monitoring.py
  - 動作:
    - プロセス優先度を "high" に設定
    - Settings から sqlite_path（監視 DB）を取得して接続、init_monitoring_db を実行してテーブルを作成
    - SystemMonitor を初期化してポーリングを開始
  - 環境変数:
    - MONITOR_POLL_INTERVAL — ポーリング間隔（秒、デフォルト 60 秒）
  - 停止:
    - data/stop_requested.flag を作成するとループが検出して終了します

- ExecutionEngine を起動（取引エンジン）
  - 実行: python src/kabusys/run_execution.py
  - 動作:
    - Settings を読み取り、KABUSYS_ENV により paper_trading モードでは paperDB を使用
    - ブローカークライアント生成（実ブローカー or Mock）
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を開始
    - data/stop_requested.flag を監視し、フラグが立てばエンジンを停止
  - 注意:
    - paper_trading 環境では MockBrokerClient を使用し DB は data/paper_trading.db に記録され、本番 DB と完全分離されます。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from / --to — レポート期間（YYYY-MM-DD）
    - --db — SQLite DB ファイルパス（PAPER_TRADING_SQLITE_PATH を上書き）
  - 出力:
    - 稼働率、注文成功率、送信率、レイテンシ指標（P95）などのサマリと PASS/FAIL 判定

- Streamlit 監視ダッシュボード
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 機能:
    - ダッシュボード集計、ポジション一覧、直近の発注ログ、最新のシステムステータス、最近のリスクログを表示

- AI モジュールの利用（コード呼び出し例）
  - ニュース NLP（スコア付与）
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=date(2026,4,10), api_key="YOUR_OPENAI_KEY")
  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date=date(2026,4,10), api_key="YOUR_OPENAI_KEY")
  - 実行には OPENAI_API_KEY（引数でも可）と DuckDB に必要なテーブル（raw_news / prices_daily 等）が必要です。

動作上のフラグ / ファイル
---------------------
- data/stop_requested.flag
  - run_monitoring / run_execution が存在を検知すると安全に終了・停止します（外部からの停止指示に使用）。
- data/kill.flag
  - KillSwitch によって書き込まれ、ExecutionEngine に停止命令を出す用途（手動・自動）。
- data/execution.pid
  - ExecutionEngine が起動中の PID を書き込む。SystemMonitor は PID ファイルの stale を検知してログを残すことがあります。

設定の読み込み挙動
-----------------
- Settings モジュールは自動で .env / .env.local を読み込みます（ただし OS 環境変数が優先）。
- 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 必須環境変数が未設定のときは Settings が ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

ディレクトリ構成（src/kabusys）
------------------------------
ここで README に含まれる主要ファイルとサブパッケージを簡単に説明します。

- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - 環境変数 / .env の読み込みと Settings クラス
- run_monitoring.py
  - SystemMonitor をポーリングするプロセス起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替あり）
- ai/
  - news_nlp.py — ニュース記事の LLM によるセンチメント評価（ai_scores への書き込み）
  - regime_detector.py — マーケットレジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py — 監視用 SQLite テーブル初期化と永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID 生存をチェック
  - trade_monitor.py — 注文滞留・約定異常をチェック
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE API を使った通知
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py, reconciler.py, order_repository.py（発注/同期関連）
  - broker_factory / broker_api（ブローカー抽象）
  - risk_manager.py（リスク管理）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算、ロット丸め、aggregate cap
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

注意事項 / 運用上の補足
--------------------
- DuckDB / SQLite のスキーマはコード内で自動作成・マイグレーションを行う箇所があります（init_monitoring_db 等）。
- AI 呼び出し（OpenAI）はネットワークエラーやレート制限を考慮したリトライ実装がありますが、API キーは安全に管理してください。
- paper_trading モードは本番 DB と分離して動作するように設計されています。検証時は必ず KABUSYS_ENV=paper_trading に設定してください。
- 本 README はコードベースの一部（抜粋）に基づいて作成しています。実運用時はプロジェクトルートのドキュメント（.env.example、requirements.txt、運用手順書）を参照してください。

ライセンス / 貢献
----------------
リポジトリに含まれるライセンスや貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

以上。必要であれば .env.example のサンプルや起動スクリプトのユースケース（systemd ユニット、docker-compose など）も追記します。どの情報を追加しますか？
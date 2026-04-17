# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行コンポーネント群）

このリポジトリは、取引実行エンジン、監視・アラート機構、ポートフォリオ構築ロジック、リサーチ用ファクター計算、LLM を用いたニュース解析などを含むモジュール群で構成されています。設計方針としては「本番系 API を直接叩かない研究/検証用コードと、実際にブローカー経由で発注する実行系を分離」「DB による永続化」「フェイルセーフ（API失敗時のフォールバック）」などが採用されています。

以下はコードベースに基づく README.md（日本語）です。

## プロジェクト概要

- 名称: KabuSys
- 目的: 日本株自動売買のための実行エンジン、監視、ポートフォリオ構築、リサーチ、ニュース NLP 等を提供する。
- 設計特徴:
  - ExecutionEngine（発注・注文管理・リスク管理・再整合）と、Monitoring（稼働監視・アラート・キルスイッチ）を分離。
  - Paper Trading 環境は本番 DB と完全分離される（専用 SQLite を使用）。
  - DuckDB を用いて市場データやファクター計算を高速に実行。
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント、レジーム判定機能を提供（APIキー必須）。
  - .env / 環境変数から設定を読み込む `kabusys.config.Settings` を中心に設定管理。

## 主な機能一覧

- execution
  - 発注管理（OrderManager）
  - リコンシリエーション（再起動時の注文/ポジション同期）
  - リスク管理・送信レート制御等
  - Broker クライアントの切替（本番 / モック）
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセスの存在、データ鮮度監視
  - TradeMonitor: 滞留注文（stale orders）、約定異常価格検出
  - RiskMonitor: ドローダウン監視・ポジション上限監視、ダッシュボード集計の永続化
  - KillSwitch: 条件に基づく停止フラグ（data/kill.flag）作成
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- portfolio
  - 銘柄選定・重み計算（等配分 / スコア加重）
  - セクター上限適用・レジーム乗数
  - 単元株丸め・投下資金のスケーリング
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- ai
  - news_nlp: raw_news から銘柄ごとのセンチメントを LLM で評価し ai_scores に書き込み
  - regime_detector: マクロニュース + ETF MA200 を組合せて市場レジーム判定（bull/neutral/bear）
- tools
  - paper_verification_report: Paper Trading DB から運用検証レポート生成

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意する。仮想環境推奨。
2. 依存パッケージをインストール（例: pip）
   - 主な依存:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード使用時)
   - 例:
     ```bash
     pip install duckdb psutil requests openai streamlit
     ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml があればそちらを使用してください。
3. プロジェクトルートに `.env`（および必要なら `.env.local`）を配置する。
   - Settings は自動的にプロジェクトルート（.git または pyproject.toml を探索）から `.env` を読み込みます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必要な環境変数（代表例）
   - J-Quants / ブローカー / LINE / OpenAI など:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合に必須)
     - LINE_CHANNEL_ACCESS_TOKEN (監視アラート送信に使用)
     - LINE_USER_ID (監視アラート送信に使用)
     - KABUSYS_ENV: one of development|paper_trading|live （デフォルト: development）
     - SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時に使用。デフォルト: data/paper_trading.db）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で利用。デフォルト: 60）
     - PAPER_FILL_MODE: paper_trading のモック約定挙動（instant|partial|never|reject。デフォルト: instant）

   - サンプル .env（最低限の例）
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jq_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     ```

5. データディレクトリを作る（`data/`）
   ```bash
   mkdir -p data
   ```

## 使い方（実行例）

- ExecutionEngine（発注エンジン）を起動
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 動作:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録し、本番 DB と分離されます。
    - PID ファイル: デフォルト `data/execution.pid`
    - `data/stop_requested.flag` が存在すると自動で起動を中止 / 停止します。

- Monitoring（監視）を起動
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - オプション:
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - 動作:
    - Monitoring は Settings の環境にかかわらず本番 sqlite_path を使用して監視ログを記録します（monitoring は production DB を参照する設計）。
    - `data/stop_requested.flag` が存在すると監視ループを終了します。

- Streamlit ダッシュボード（監視結果の可視化）
  - 実行:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 説明:
    - Read-only モードで SQLite を開くため、監視中の DB を安全に参照可能。
    - Overview / Positions / Orders / System タブを提供。

- Paper Trading 検証レポート生成（ツール）
  - 実行:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション:
    - `--db PATH` で DB ファイルを指定（環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可能）。
  - 出力: 標準出力にレポート（稼働率、注文成功率、レイテンシなど）を表示。

- AI 系関数（プログラムから呼び出し）
  - `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)` — raw_news を解析して ai_scores に書き込む。
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` — レジーム判定を market_regime テーブルに書き込む。
  - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を使用。

- 強制停止 / キル
  - Monitoring 側の KillSwitch により `data/kill.flag` が作成されると ExecutionEngine に停止指示を与えます。
  - 手動で停止を要求する場合は `data/kill.flag` に理由を書き込むか `data/stop_requested.flag` を作成して監視/実行ループを終了させます。

## 設定・運用上の注意

- Settings は自動で `.env` / `.env.local` を読み込みます。OS 環境変数が優先され、`.env.local` は `.env` の上書きとして読み込まれます。
- `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれかでなければなりません。
- Paper Trading モードは本番 API 呼び出しを行わず、専用の SQLite にすべて記録する設計です（安全に検証できます）。
- OpenAI 呼び出しは外部 API で課金対象です。テスト時はモック化してください（コード内でもテスト用に差し替えやすい設計）。
- Monitoring は本番 DB を参照するため、監視部の権限や DB パス設定に注意してください。
- `MONITOR_POLL_INTERVAL` に無効な値（<=0 や非整数）を設定するとデフォルト 60 秒にフォールバックします。

## ディレクトリ構成（主要ファイル）

（リポジトリ内の `src/kabusys` を基準に抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込みと Settings 定義
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - data/  (実行時に使用する SQLite / DuckDB のデフォルトパス: data/*.db, data/kabusys.duckdb)
  - execution/
    - execution_engine.py (エンジン本体; 起動・セッション管理)
    - order_manager.py (OrderManager)
    - order_repository.py (OrderRepository, SQLite)
    - reconciler.py (再整合)
    - broker_factory.py (ブローカークライアント生成)
    - ...（order_record, broker_api 等）
  - monitoring/
    - monitoring_db.py (監視用DBスキーマ + 永続化層)
    - system_monitor.py (CPU/メモリ/プロセス/データ鮮度監視)
    - trade_monitor.py (滞留注文 / 約定異常)
    - risk_monitor.py (ドローダウン・ポジション数監視)
    - kill_switch.py (停止フラグ生成)
    - alert_manager.py (LINE通知)
    - monitoring_engine.py (各モニタを束ねる)
    - streamlit_dashboard.py (簡易ダッシュボード)
  - portfolio/
    - portfolio_builder.py (候補選定・重み)
    - position_sizing.py (発注株数計算・スケーリング)
    - risk_adjustment.py (セクター制限・レジーム乗数)
  - research/
    - factor_research.py (momentum/value/volatility)
    - feature_exploration.py (forward returns, IC, factor summary)
  - ai/
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity 設定)
  - その他: data/stop_requested.flag, data/kill.flag, data/execution.pid（実行時に使うフラグファイル）

（注）上記は主要なファイル群の抜粋です。実際のリポジトリにはさらにサブモジュールや実装ファイルが存在します。

## 開発時のヒント / テスト

- OpenAI・外部 API 呼び出しはユニットテスト時にはモック化（patch）してください。コード中でも _call_openai_api を個別に差し替えることを想定しています。
- DuckDB / SQLite のクエリは単体で動作確認できます。price データや raw_financials/raw_news 等のテーブルが必要です。
- MonitoringDB.init_monitoring_db(conn) は冪等にテーブルを作成・マイグレーションします。初回起動時に呼び出してください（エンジンスクリプトで実行されます）。

## 付録 — よく使うコマンド一覧

- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 環境変数無効化（.env 自動読み込み停止）:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

この README はコードベース（src/kabusys 以下）から主要機能と設定項目を抽出して作成しています。詳しい API や内部実装、追加の運用手順（データ取得パイプライン、ブローカー接続設定など）は各モジュールのドキュメントやコードコメントを参照してください。必要であれば、特定モジュール（例: execution_engine の起動フロー、AI モジュールのテスト方法）に関する詳細ドキュメントも作成できます。
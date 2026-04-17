# KabuSys

日本株自動売買システムのリファクタリングされたモジュール群。戦略の研究・ファクター計算、ポートフォリオ構築、発注実行、監視、AIベースのニュース解析などを含みます。

この README はリポジトリ内の主要スクリプト／モジュールの使い方、セットアップ、ディレクトリ構成をまとめたものです。

## プロジェクト概要
- 目的：日本株自動売買システム（KabuSys）のコアロジック群を提供する。研究（research）、ポートフォリオ構築（portfolio）、発注実行（execution）、監視（monitoring）、AI解析（ai）などの機能を持つ。
- 設計方針：
  - DuckDB / SQLite をデータレイヤに使用（時系列・財務データは DuckDB、監視ログは SQLite）。
  - 環境変数 / .env による設定管理（Settings クラス）。
  - Paper Trading（モックブローカー）と Live を分離。Paper Trading は別 SQLite ファイルに記録。
  - AI（OpenAI）呼び出しはフェイルセーフなリトライやバリデーションを備える。

## 主な機能一覧
- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- portfolio
  - 候補選定、等重/スコア加重、セクター制限、ポジションサイジング（ロット丸め・リスク制限）
- execution
  - 注文作成・管理（OrderManager）
  - Broker クライアントファクトリ（本番 / モック切替）
  - 起動時のリコンシリエーション（Reconciler）
  - 実行エンジン起動スクリプト（run_execution.py）
- monitoring
  - System / Trade / Risk の監視モジュール
  - 監視ログ永続化（SQLite）と DB 初期化ユーティリティ
  - KillSwitch（停止フラグ）、AlertManager（LINE プッシュ通知）
  - MonitoringEngine（ポーリング）と起動スクリプト（run_monitoring.py）
  - Streamlit ダッシュボード（監視 DB の可視化）
- ai
  - ニュースのセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（ma200 + マクロニュースの LLM スコア合成）
- tools
  - Paper Trading 検証レポート生成ツール（paper_verification_report）

## セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 主に以下のパッケージが必要です（プロジェクトに requirements.txt がない場合の参考）。
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

3. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data

4. 環境変数 / .env の準備
   - ルートに `.env`（や `.env.local`）を置けば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数（例・説明）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI機能使用時必須）
     - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading 時のモック約定モード（instant/partial/never/reject, デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（空だと通知はスキップ）
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で上書き可）

5. DB 初期化
   - 監視 DB（monitoring.db）は起動スクリプト実行時に自動で初期化されます（init_monitoring_db）。
   - DuckDB (kabusys.duckdb) は research / ai モジュールが参照するテーブル（prices_daily, raw_financials, raw_news など）を用意する必要があります。データ準備は別途スクリプトや ETL によって行ってください。

## 使い方（主要コマンド・起動例）
- 監視ループ起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数をオーバーライド可（デフォルト 60s）。
  - 実行:
    - python src/kabusys/run_monitoring.py
  - 停止:
    - data/stop_requested.flag を作成するとループが終了します（フラグファイル経由の停止）。

- 実行エンジン起動（ExecutionEngine）
  - Paper Trading モードで起動する例:
    - export KABUSYS_ENV=paper_trading
    - python src/kabusys/run_execution.py
    - paper_trading の場合、Broker は MockBrokerClient が使われ、Paper DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
  - Live モード:
    - export KABUSYS_ENV=live
    - 実際のブローカークライアントが使用されます（KABU_API_PASSWORD 等の設定必須）。
  - 停止:
    - data/stop_requested.flag を作成 → 実行中のエンジンが検知して停止します。
    - 実行中は data/execution.pid（デフォルト）に PID を書きます。

- Paper Trading 検証レポート（ツール）
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db /path/to/paper_trading.db
  - レポート内容: 稼働率、注文成功率、送信率、レイテンシ（P95）などを出力。閾値はスクリプト内に定義。

- Streamlit ダッシュボード（監視可視化）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ダッシュボード表示します。

- AI（ニューススコア / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime を直接 Python から呼ぶか、独自ラッパーで実行。
  - OpenAI API キー（OPENAI_API_KEY）が必要。
  - DuckDB 接続を渡して実行。例（概念）:
    - import duckdb; from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb"); score_news(conn, target_date, api_key="...")

## 設定の注意点
- .env の自動読み込み
  - デフォルトでプロジェクトルート（.git または pyproject.toml を検出）から `.env` / `.env.local` を読み込む。
  - テスト等で自動読み込みを無効化する場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 環境（KABUSYS_ENV）
  - 有効値: development, paper_trading, live
  - Paper Trading は production DB と明確に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視関連フラグ
  - data/stop_requested.flag — スクリプト（実行・監視）が定期チェックして停止処理を行うためのフラグファイル。
  - data/kill.flag — KillSwitch が条件を満たした場合に書き込まれ、ExecutionEngine を停止するトリガーとして使用（KillSwitch を使う場合）。
  - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）。

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン）
  - config.py — Settings（環境変数 / .env の読み込み・検証）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・リスク制限・ロット丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py — 将来リターン／IC／統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py — 監視ログの DB 初期化・クラス
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常価格監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグ管理
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各モニタの束ね（ポーリング）
    - streamlit_dashboard.py — Streamlit ベースのダッシュボード
  - execution/
    - order_manager.py — 注文作成・状態遷移管理
    - reconciler.py — 起動時の自動復旧・リコンシリエーション
    - （その他 broker_factory 等、ブローカー関連）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

## 開発・運用上の留意点
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等に複数カラムの追加マイグレーション処理も行います。実稼働 DB を扱う場合はバックアップを取ってください。
- ロギング
  - 起動スクリプトは標準 logging を使用。必要に応じて設定を上書きしてください。
- フェイルセーフ
  - AI 呼び出しや外部 API 呼び出しはリトライやフォールバック（0.0 スコアなど）を行い、致命的な例外でサービス全体を停止しない設計です。
- テスト
  - OpenAI 呼び出し部分などはテスト時にモック化することを想定して設計されています（内部の _call_openai_api をパッチ）。

## よく使うコマンドのまとめ（例）
- 監視開始:
  - MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py
- 実行エンジン開始（Paper Trading）:
  - KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースの主要点をまとめたものです。さらに詳細な API や内部仕様（StrategyModel.md、PortfolioConstruction.md 等）がリポジトリにある想定で、それらのドキュメントに従って運用・拡張してください。必要なら各モジュールの使い方（関数シグネチャや例）を追記します。どの部分を詳しく書くか指示してください。
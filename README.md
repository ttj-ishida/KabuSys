# KabuSys

日本株向け自動売買システムの内部ライブラリ群と運用ユーティリティ群です。  
この README はコードベース（src/kabusys 以下）をもとに、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、戦略計算（ファクター計算・特徴量解析）、ポートフォリオ構築、発注実行、監視・アラート、Paper Trading 検証、AI を使ったニュースセンチメント評価などを備えた日本株向け自動売買基盤のコンポーネント群です。  
主要な設計方針として以下があります。

- DuckDB（履歴データ・リサーチ）と SQLite（監視・注文ログ）を併用
- 設定は環境変数 / .env ファイルで管理（自動ロード機能あり）
- Paper Trading モードで本番 DB と分離可能
- OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム判定機能を搭載（API キー必須）
- プロセス優先度や kill flag による運用安全機構あり

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアントの抽象化（paper_trading 時は MockBrokerClient を使用）
  - OrderManager / OrderRepository / Reconciler による注文管理と再同期
  - RiskManager（ポジション上限や利用率等の制限）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文、約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringEngine（上記を束ねてポーリング）
  - AlertManager（LINE push による通知）
  - Streamlit ダッシュボード（read-only 接続で監視 UI を表示）
  - monitoring DB 層（SQLite 用の永続化層・マイグレーションロジック）
  - kill.flag による ExecutionEngine 停止シグナル
- Portfolio construction
  - 候補選定、等重・スコア加重、セクターキャップ、リスクベースの株数算出
- Research / Features
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI
  - ニュースを OpenAI でスコア化して ai_scores テーブルへ書き込む（news_nlp）
  - レジーム判定（ETF MA200 とマクロニュースの LLM センチメントを合成）
  - 再試行・バッチ処理・レスポンス検証などフェイルセーフな実装
- ユーティリティ
  - .env 自動読込（プロジェクトルート検出）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順

前提
- Python 3.10+（typing の | 記法や動的型注釈を使用）
- Git リポジトリルートにプロジェクトがあること（.env 自動ロードに用いる）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必要なライブラリ（代表）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がない場合は上記を参考に追加してください）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くことで自動ロードされます（既存 OS 環境変数は保護）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB; デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（LINE 通知）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - MONITOR_POLL_INTERVAL（監視ループ間隔秒、デフォルト 60）
   - .env.example がある想定でそれを参考に .env を作成してください。

6. DB 初期化
   - monitoring 側は run_* スクリプトが起動時に init_monitoring_db を実行してくれます。
   - research 向けの DuckDB テーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）は別途データ投入が必要です。

---

## 使い方（主要コマンド）

プロジェクトルートで、仮想環境を有効にした状態で実行してください。

- ExecutionEngine を起動（本番 or paper_trading）
  - 本番想定:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - Paper Trading（MockBrokerClient を使用し data/paper_trading.db に記録）
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

- Monitoring（System / Trade / Risk のポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔秒を変更（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 注意: Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path（Settings.sqlite_path）を使用します（監視は現行運用 DB を見るため）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only URI で SQLite を開いて表示します（Monitoring が書き込むデータを参照）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/paper_trading.db

- AI 機能（プログラム内呼び出し）
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を渡して使用します。OpenAI API キーが無い場合は例外またはフェイルフォールバック動作になります（詳細は各実装参照）。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動。default: instant）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- PID_FILE_PATH: ExecutionEngine の PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH: kill flag ファイル（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を消すか（"1" にするとクリア）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。default: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" で .env の自動ロードを無効化

---

## 運用上のポイント（注意事項）

- Monitoring は監視対象の実プロセスや DB を参照するため、監視 DB と実行 DB の切り分けは注意してください。Paper Trading の発注ログは専用の paper_trading DB に分離されますが、Monitoring は常に Settings.sqlite_path を参照します（意図的）。
- OpenAI API を用いる機能は外部コスト・レート制限に注意してください。モジュール側でリトライやバッチ処理、レスポンス検証を行っていますが、運用上の監視・クールダウン制御が必要です。
- kill.flag による停止シグナルは冪等に書き込まれ、ExecutionEngine 側で検出して安全に停止することを想定しています。
- プロセス優先度の設定（set_process_priority）は可能な範囲で実行されますが、権限不足や未対応 OS の場合はスキップされます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / .env 自動ロード / Settings クラス
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

src/kabusys/execution/
- order_manager.py — 発注ロジック（OrderManager）
- reconciler.py — 起動時リコンシリエーション（注文・ポジション突合）
- ...（broker_factory 等、ブローカー抽象層・リポジトリ）

src/kabusys/monitoring/
- monitoring_db.py — SQLite テーブル生成・永続化 API（MonitoringDB）
- system_monitor.py — システム / データ鮮度の監視
- trade_monitor.py — 注文滞留・約定異常監視
- risk_monitor.py — ドローダウン・ポジション数監視
- kill_switch.py — kill.flag 関連
- alert_manager.py — LINE 通知
- monitoring_engine.py — 各 Monitor を束ねる
- streamlit_dashboard.py — 監視 UI（Streamlit）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数算出・丸め・スケールダウンロジック
- risk_adjustment.py — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
- feature_exploration.py — 将来リターン / IC / 統計サマリ

src/kabusys/ai/
- news_nlp.py — ニュースを LLM でスコア化して ai_scores に書き込み
- regime_detector.py — マクロセンチメント + ETF MA200 を合成して market_regime に書き込み

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポートの CLI スクリプト

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 開発・拡張のヒント

- DuckDB のテーブル（prices_daily / raw_financials / raw_news など）は外部 ETL によって準備する想定です。Research モジュールは DuckDB 接続を受け取り SQL + Python で処理します。
- monitoring_db.init_monitoring_db() は冪等でテーブルを作成し、一部カラムのマイグレーションも自動化されています。運用中にスキーマ変更が必要な場合はこの関数を拡張してください。
- AI 関連の外部呼び出しはテスト時に差し替え可能（_call_openai_api をモックする想定）。
- 設定管理は Settings クラスを経由する形なので、追加設定は config.py にまとめると追従しやすいです。

---

必要であれば、README に含める具体的な .env.example のテンプレートや、よく使うコマンドをまとめた運用手順（systemd / supervisor 用のサービス定義例）も作成できます。どの情報を追加したいか教えてください。
# KabuSys

日本株向けの自動売買システムのモジュール群です。ポートフォリオ構築、シグナル・リスク管理、発注実行、監視、リサーチ、LLM を用いたニュースセンチメント評価などの機能を含みます。

以下はコードベース（src/kabusys）を対象にした README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したコンポーネント群です。設計方針として以下を重視しています。

- 監視（Monitoring）と実行（Execution）を明確に分離
- 本番・ペーパー（paper_trading）環境の分離（Paper Trading は専用 SQLite DB を使用）
- DuckDB をデータ分析（prices_daily / raw_financials 等）用途に利用
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価・レジーム判定の補助機能
- 冪等・クラッシュ耐性を考慮した DB 書き込みとリコンシリエーション

主な実行スクリプト：
- run_monitoring.py — SystemMonitor のポーリングループを起動
- run_execution.py — ExecutionEngine（発注エンジン）を起動
- tools.paper_verification_report — Paper Trading の検証レポート出力
- monitoring/streamlit_dashboard.py — Streamlit を用いた監視ダッシュボード

---

## 機能一覧

- 監視（monitoring）
  - システム状態（CPU/メモリ/ディスク）とプロセス生存確認
  - データ鮮度チェック（DuckDB の prices_daily 参照）
  - 注文滞留（stale orders）や約定価格の異常検出
  - ドローダウン / ポジション上限監視とリスクログ記録
  - LINE へのアラート通知（AlertManager）
  - kill.flag による Execution エンジン停止シグナル
  - Streamlit ダッシュボード（read-only）で監視情報表示

- 発注 / 実行（execution）
  - OrderManager, OrderRepository による注文ライフサイクル管理
  - ブローカー抽象化（BrokerClientFactory）により本番/モックを切替
  - Reconciler による起動時の自動同期（OrderSent の再照合、ポジション差分検出）
  - リスク管理（RiskManager）や取引ログの永続化

- ポートフォリオ構築（portfolio）
  - 候補選定、等金額/スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap のスケーリング）

- リサーチ（research）
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を使用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI（ai）
  - news_nlp.score_news: raw_news → OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離 + マクロニュースセンチメントを合成して市場レジーム判定

- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity の設定（Windows / POSIX 対応）
  - config: .env 自動読み込み（プロジェクトルート検出）と Settings 抽象化

---

## セットアップ手順（ローカル）

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必要な依存の抜粋:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

3. 環境変数（.env）を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` / `.env.local` が自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主に必要な環境変数（代表）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須な箇所で使用）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI を使う機能で必要
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
     - PAPER_FILL_MODE — paper_trading の約定モード（instant / partial / never / reject）
     - PID_FILE_PATH / KILL_FLAG_PATH — PID / kill flag のパス
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - サンプル .env（例）
     - KABUSYS_ENV=development
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=your_password
     - JQUANTS_REFRESH_TOKEN=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

4. データディレクトリの作成
   - デフォルトでは data/ 下に DB が作られます。必要に応じてディレクトリを作成してください:
     - mkdir -p data

5. DB 初期化
   - run_monitoring/run_execution 起動時に monitoring DB スキーマ（init_monitoring_db）が自動で作成・マイグレーションされます。手動での初期化は不要です。

---

## 使い方

以下は典型的な実行例です。いずれもプロジェクトルートで実行してください。

- 監視ループ起動（本番監視）
  - MONITOR_POLL_INTERVAL（秒）でポーリング。デフォルト 60 秒。
  - 実行:
    - python -m kabusys.run_monitoring
  - 例（間隔 30 秒）:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 DB に書き込む（data/paper_trading.db）。
  - 実行:
    - python -m kabusys.run_execution
  - Paper Trading で起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード（監視）
  - 監視 DB を読み取り専用で表示します。
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - data/paper_trading.db から期間指定で集計して標準出力へ表示します。
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

- AI 系機能（ニュースセンチメント / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要。モジュール API を直接呼ぶことも可能（テスト用に関数を import して実行）。
  - 例（Python REPL）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="sk-...")

- kill.flag の操作
  - KillSwitch は conditions を満たすと設定（data/kill.flag を作成）し、ExecutionEngine 側で停止判定に利用する設計です。
  - 手動でクリアする場合:
    - rm data/kill.flag
  - 設定ファイルで KILL_FLAG_CLEAR_ON_START=1 にすると ExecutionEngine 起動時に自動クリアする動作が有る設計要素があります（Settings.kill_flag_clear_on_start を参照）。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV (development | paper_trading | live) — 環境モード
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE 通知）
- PID_FILE_PATH — 実行エンジンの PID ファイルパス
- KILL_FLAG_PATH — kill.flag のパス
- PAPER_FILL_MODE — paper_trading の約定モード（instant | partial | never | reject）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージメタデータ
- config.py — 環境変数 / Settings の読み取りと .env 自動ロード
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

モジュール群（主要ファイル）
- ai/
  - news_nlp.py — ニュースの LLM スコアリング（ai_scores 書込み）
  - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（schema 初期化、CRUD）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
  - trade_monitor.py — 注文滞留 / 約定異常の監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE 通知ユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - reconciler.py — 起動時リコンシリエーション
  - order_manager.py — 発注の高レベル API
  - order_repository.py, order_record.py, ...（発注関連）
  - broker_factory.py, broker_api.py（ブローカー抽象化）
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクター制限 / レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリ
- data/
  - pipeline.py, stats.py, ...（DuckDB 用ユーティリティ）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート

（上記は主要モジュールの要約です。実際のファイル一覧は src/kabusys 配下を参照してください）

---

## 注意点 / 運用上のポイント

- .env の自動読み込みはプロジェクトルート検出に依存します。CWD に依らず動作するよう設計されていますが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- Monitoring は KABUSYS_ENV の値に関わらず監視用 SQLite（SQLITE_PATH）を使用します。
- Paper Trading は settings.is_paper を元に paper_sqlite_path を使い本番 DB と物理的に分離します。
- OpenAI API 呼び出しにはレート制限やネットワーク障害に対するリトライロジックが組み込まれていますが、API キーの管理やコストには注意してください。
- process_priority の変更は権限に依存するため失敗する場合があります（警告ログが出ます）。
- DuckDB / SQLite への executemany に空リストを渡すとエラーになるバージョン制約があるため、コード内で空チェックを行っています。

---

問題や拡張、運用フロー（CI/CD、運用監視、バックアップなど）の要件があれば、その点に合わせた README の補足を作成します。必要な場合は教えてください。
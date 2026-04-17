# KabuSys

日本株向け自動売買システムのコアライブラリ群と運用ユーティリティ群です。  
このリポジトリには、発注実行エンジン、監視システム、ポートフォリオ構築ロジック、リサーチ用ファクター計算、LLM を使ったニュースセンチメント評価などが含まれます。

以下はこのコードベースの README（日本語）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買（アルゴリズミックトレーディング）を想定したモジュール群です。主な目的は以下の通りです。

- 信号から注文を生成してブローカーへ発注する ExecutionEngine。
- 実行中のシステム状態・注文状態・リスク指標を定期的に監視する Monitoring。
- ポートフォリオ構築（候補選定、重み付け、銘柄ごとの発注株数決定）。
- DuckDB を用いた時系列データ処理・ファクター計算（リサーチ用）。
- OpenAI（LLM）を用いたニュースセンチメント評価および市場レジーム判定（オプション）。
- 運用用ユーティリティ（プロセス優先度設定、Streamlit ダッシュボード、検証レポート生成など）。

設計方針として以下を重視しています。

- モジュール化（監視・実行・研究・AI・ユーティリティが分離）
- 本番とペーパートレードの明確な分離（DB 等）
- ルックアヘッドバイアス防止（日時の取り扱いに注意）
- フェイルセーフ（API失敗時のフォールバックやリトライ）

---

## 機能一覧（主要機能）

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / OrderRepository / Reconciler（自動復旧・同期）
  - ブローカーファクトリ（paper_trading 時は MockBroker を使用）
  - RiskManager（発注前チェック・利用率など）
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス健在性 / データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常チェック
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクイベント記録
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）生成
  - AlertManager：LINE へプッシュ通知（クールダウン付き）
  - MonitoringEngine：各モニタのまとめ・ポーリングループ
  - Streamlit ダッシュボード（監視結果可視化）
- Portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）
  - 等金額/スコア重量配分（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ / レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- Research（リサーチ）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続で SQL 実行）
  - 将来リターン計算、IC（Information Coefficient）算出、統計要約
- AI（任意）
  - news_nlp: raw_news を OpenAI でスコアリングして ai_scores へ書き込み
  - regime_detector: ETF MA200 とマクロニュースの LLM センチメントを統合して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB に対する検証レポート生成（稼働率・成功率・レイテンシ等）
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity の設定
  - config: 環境変数 / .env 自動読み込み・設定ラッパー
  - monitoring_db: SQLite スキーマ初期化・読み書きユーティリティ

---

## 必要条件（推奨）

- Python 3.10+
  - 型ヒントに | 記法（PEP 604）が使われているため Python 3.10 以降を推奨します。
- ライブラリ（最低限）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボードを利用する場合)
- 標準ライブラリ：sqlite3, threading, logging など

インストール例（仮の requirements）：

pip install duckdb psutil openai requests streamlit

（プロジェクトに requirements.txt がある場合はそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローンして、Python 仮想環境を作成して有効化します。

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell)

2. 必要パッケージをインストールします。

   pip install --upgrade pip
   pip install duckdb psutil openai requests streamlit

3. データディレクトリを作成します（必要に応じて）。

   mkdir -p data

   主要なデフォルトファイル・パス:
   - monitoring DB: data/monitoring.db (Settings.sqlite_path デフォルト)
   - duckdb: data/kabusys.duckdb (Settings.duckdb_path デフォルト)
   - paper trading DB: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
   - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

   多くのスクリプトは起動時に DB スキーマを初期化します（init_monitoring_db）。

4. 環境変数の設定
   - 推奨: プロジェクトルートに .env を置くと自動で読み込まれます（.env.local も上書き読み込み可）。
   - 必須（環境による）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他（必要に応じて）:
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject")
     - PAPER_TRADING_SQLITE_PATH
     - DUCKDB_PATH, SQLITE_PATH
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（監視アラートを LINE に送る場合）
     - LOG_LEVEL 等

   ヒント: .env.example を参考に .env を作成してください（リポジトリに例ファイルがある場合）。

5. （任意）データ初期化
   - DuckDB 用の時系列データや raw_news 等の投入は運用フローに依存します。リサーチや AI モジュールを使うには prices_daily / raw_financials / raw_news 等のテーブルが必要です。

---

## 使い方（主要スクリプト）

以下は代表的な起動方法とオプション例です。

- ExecutionEngine を起動（実際の発注エンジン）

  python -m kabusys.run_execution

  挙動:
  - KABUSYS_ENV が "paper_trading" の場合、MockBrokerClient を使い paper_trading 用 DB（data/paper_trading.db）へ記録します。
  - 停止は data/stop_requested.flag を作成することで指示できます（Run スクリプトがフラグを検知して終了します）。
  - 起動時に pid ファイル（data/execution.pid）を作成します。

- Monitoring（システム監視）を起動

  python -m kabusys.run_monitoring

  オプション/環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使います（監視・運用は共有 DB を参照する想定）。

- Streamlit ダッシュボード（監視可視化）

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  （引数 --db で別 DB を指定可能）

- Paper Trading 検証レポート生成

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

## 環境変数（主要なもの）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用アクセストークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文約定モード（instant/partial/never/reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒）

注意: Settings クラスは .env と OS 環境変数を読み、.env.local が .env を上書きします。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます。

---

## 運用上の注意

- データ鮮度チェックや PID ファイルの有無により Execution の稼働判定を行います。PID ファイルが stale（不正）と判明した場合は削除し、リスクログを残します。
- KillSwitch は RiskMonitor の結果に基づいて data/kill.flag を書き込み、ExecutionEngine を停止させる運用が可能です。kill.flag は冪等的に書き込まれます。
- LLM（OpenAI）を使うモジュールは API エラーやレート制限に対してエクスポネンシャルバックオフやフォールバックを実装していますが、API キーの管理・コストには注意してください。
- Paper Trading では本番 DB と完全に分離して動作するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル/ディレクトリは以下の通りです（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込みと Settings
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading の検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースの LLM ベースセンチメント評価
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite スキーマ初期化・読み書き
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
    - system_monitor.py             — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py              — 注文滞留・約定異常監視
    - risk_monitor.py               — ドローダウン等のリスク監視
    - kill_switch.py                — kill.flag 管理
    - alert_manager.py              — LINE 通知
    - streamlit_dashboard.py        — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - order_record.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - ... (その他 Execution 関連)
  - portfolio/
    - portfolio_builder.py          — 候補選定 / 重み
    - position_sizing.py            — 発注株数計算・スケール調整
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py            — Momentum / Value / Volatility 等
    - feature_exploration.py        — 将来リターン・IC・統計サマリ
    - __init__.py
  - data/  (運用時に作成される想定)
    - monitoring.db
    - kabusys.duckdb
    - paper_trading.db
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - utils/
    - process_priority.py           — プロセス優先度・CPU affinity ユーティリティ
    - __init__.py

---

## 主要な開発・運用ユースケース

- ローカルで戦略・研究を行う（DuckDB に価格データを読み込んで factor_research を実行）
- Paper Trading による機能検証（KABUSYS_ENV=paper_trading）
- 実運用時の監視（run_monitoring をサービスとして常時稼働）
- 異常検知時 LINE 通知（AlertManager）
- 定期レポートや検証（tools.paper_verification_report）

---

## 参考・補遺

- MONITOR_POLL_INTERVAL（run_monitoring）によりポーリング間隔をオーバーライドできます（秒、デフォルト 60）。
- Paper Trading は本番 DB と分離されるため、テスト/検証で本番資産に影響を与えません。
- Settings クラスは起動時に .env/.env.local を自動読み込みします。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- コード内ヘルプや docstring に実行方法や注意点が多く書かれているため、各モジュールの先頭 docstring も参照してください。

---

もし README のフォーマットや含める情報（例: サンプル .env、systemd サービス定義、より詳細な起動手順など）を追加したければ教えてください。必要に応じてサンプル .env 内容や systemd ユニット例も作成します。
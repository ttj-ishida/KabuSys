# KabuSys

KabuSys は日本株向けの自動売買・研究・監視プラットフォームのサンプル実装です。  
このリポジトリは戦略（ファクター計算・特徴量解析）、ポートフォリオ構築、発注実行・再接続処理、監視・アラート、そしてニュース NLP を利用した AI モジュールなどを含みます。

この README ではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

- 名称: KabuSys
- 目的: 日本株の自動売買システムに必要なコンポーネント（リサーチ、ポートフォリオ構築、発注/リコンシリエーション、監視・アラート、AI によるニュースセンチメント評価）を統合したサンプル実装。
- 設計方針:
  - DuckDB を用いた市場データ参照（prices_daily / raw_financials 等）。
  - SQLite を用いた監視ログ・注文ログ永続化。
  - OpenAI（gpt-4o-mini 等）経由でニュースセンチメントやマクロセンチメントを算出（オプション）。
  - Paper Trading 環境は本番 DB と分離して動作可能。
  - 自動停止用の kill.flag / stop_requested.flag 等による外部制御をサポート。

---

## 主な機能一覧

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリューなどのファクター計算（kabusys.research）
  - 将来リターン計算 / IC 計算 / 統計サマリー（feature_exploration）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等配分・スコア加重配分の重み付け
  - ポジションサイズ計算（リスクベース・等分配など）、単位株丸め、集約キャップ調整
  - セクター集中規制やレジーム乗数の適用
- 発注実行 / リコンシリエーション（kabusys.execution）
  - OrderManager, Reconciler による注文状態管理と起動時の自動復旧
  - ExecutionEngine（起動スクリプト: run_execution.py）を通じた発注ループ（本番 / PaperTrading 対応）
- 監視（kabusys.monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック（CPU・メモリ・ディスク・データ鮮度・滞留注文・約定異常・ドローダウン等）
  - MonitoringDB: SQLite による監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - KillSwitch: ドローダウン等をトリガとして ExecutionEngine に停止信号を送信（kill.flag）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
  - 監視ポーリング起動スクリプト: run_monitoring.py（環境変数でポーリング間隔を設定可）
- AI モジュール（kabusys.ai）
  - news_nlp: raw_news を OpenAI に投げ、銘柄ごとのセンチメントスコアを ai_scores に書き込み
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM 評価を合成して日次で市場レジーム（bull/neutral/bear）を決定
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 自動ロード機能（kabusys.config）と Settings クラス：主要環境変数をラップ

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上を推奨（型ヒントに新版構文が使われているため）
- git, SQLite が使える環境

1. リポジトリをクローン / ソースを配置
   - 例: git clone <repo-url>

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil requests openai streamlit
   - 他に必要なパッケージがある場合は適宜追加してください。

   （プロジェクトに requirements.txt があればそれを使ってください）

4. data ディレクトリ作成（初期 DB やフラグファイル保存場所）
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を作成して必要なキーを設定します。
   - 主要な環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能利用時に必要)
     - KABU_API_BASE_URL (任意; デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN (通知用)
     - LINE_USER_ID (通知用)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db) — 監視ログ DB
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (paper_trading の約定挙動: instant|partial|never|reject)
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - KILL_FLAG_PATH (デフォルト: data/kill.flag)
     - KILL_FLAG_CLEAR_ON_START (1 で起動時に kill.flag を削除)
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視しきい値）
     - KABUSYS_ENV = development | paper_trading | live
     - LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL
   - 監視ループのポーリング間隔:
     - 環境変数 MONITOR_POLL_INTERVAL（秒）。既定値 60 秒。1 未満や無効値はデフォルトにフォールバックします。

6. データベース初期化
   - run_monitoring.py や run_execution.py の起動時に monitoring DB のテーブルは自動作成されます（init_monitoring_db）。

---

## 使い方

以下は代表的な起動 / 利用方法です。

1. ExecutionEngine（発注エンジン）を起動
   - 本番 / 開発 / paper_trading は KABUSYS_ENV により切り替わります。
   - paper_trading の場合、MockBrokerClient が使われ、PaperTrading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。
   - 実行:
     - python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成するとループ終了を促します（スクリプトは _STOP_FLAG を参照）。
     - kill.flag は ExecutionEngine 側面からの停止トリガ（KillSwitch が書き込む）です。

2. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
   - 監視は Settings に指定された sqlite_path（監視 DB）にログを保存します（monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する点に注意）。

3. Streamlit ダッシュボード（監視 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、状況を可視化します。

4. Paper Trading 検証レポート生成ツール
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで PAPER_TRADING_SQLITE_PATH を指定できます。
   - 報告項目: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数 など。基準値を下回ると FAIL 表示になります。

5. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要です。
   - プロダクション化する場合は API キーの管理に注意してください。
   - モジュールを直接インポートして呼び出す例:
     - from kabusys.ai.news_nlp import score_news
     - from kabusys.ai.regime_detector import score_regime
   - これらは DuckDB 接続（prices_daily / raw_news 等のテーブルが存在すること）を引数に取り、DuckDB 内のテーブルへ書き込みを行います。

6. 停止・制御フラグ
   - data/stop_requested.flag: run_monitoring / run_execution のループを穏やかに終了させるためにプロセスが監視するファイル。
   - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に対する停止要求として扱われます（存在すれば engine は停止するように設計）。

---

## 主要コマンドまとめ

- 仮想環境作成 / 有効化:
  - python -m venv .venv
  - source .venv/bin/activate

- パッケージインストール:
  - pip install duckdb psutil requests openai streamlit

- 実行 (例):
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 設定（環境変数の一覧・注意点）

主要な環境変数（Settings クラス参照）:

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能利用時に必須)
  - KABU_API_BASE_URL (任意; デフォルト: http://localhost:18080/kabusapi)

- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN (任意)
  - LINE_USER_ID (任意)

- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)

- Paper Trading
  - KABUSYS_ENV = development | paper_trading | live
    - paper_trading の場合、MockBroker を使用し、本番 DB とは別の paper_sqlite_path を使用します。
  - PAPER_FILL_MODE = instant | partial | never | reject

- 監視しきい値 / 動作
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒、デフォルト 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - KILL_FLAG_CLEAR_ON_START = "1" で起動時に kill.flag をクリア

注意:
- Settings._require() により必須変数が未設定だと ValueError が発生します。
- .env の自動読み込みはデフォルトで有効。テスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数読み込み・Settings
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py            — レジーム判定（ETF MA + マクロ NLP）
  - research/
    - __init__.py
    - factor_research.py            — momentum / volatility / value の計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー等
  - portfolio/
    - __init__.py
    - portfolio_builder.py          — 候補選定・重み計算
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
    - position_sizing.py            — 株数決定・資金配分・集約キャップ
  - monitoring/
    - __init__.py
    - monitoring_db.py              — monitoring 用 SQLite テーブル定義 / API
    - system_monitor.py             — CPU/メモリ/ディスク/データ鮮度チェック
    - trade_monitor.py              — 滞留注文 / 約定異常チェック
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag 書き込みユーティリティ
    - alert_manager.py              — LINE への通知
    - monitoring_engine.py          — 各 monitor を束ねるエンジン
    - streamlit_dashboard.py        — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py              — 注文管理（Order State Machine 外向き API）
    - reconciler.py                 — 起動時の照合・自動復旧
    - （ExecutionEngine, broker などその他コンポーネントは同ディレクトリに存在）
  - utils/
    - __init__.py
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (実行時に生成される)
    - monitoring.db (sqlite)
    - paper_trading.db (sqlite)
    - kabusys.duckdb (duckdb)
    - execution.pid / stop_requested.flag / kill.flag

---

## 開発上の注意点 / Tips

- Paper Trading と本番 DB を分離する設計になっています。KABUSYS_ENV を適切に設定してから起動してください。
- OpenAI API を利用する処理は外部 API 呼び出しなので、失敗耐性（リトライ・フォールバック）が実装されていますが、API キー管理やコストに注意してください。
- monitoring_db.init_monitoring_db() は冪等にテーブル作成・簡易マイグレーションを行います。既存 DB での列追加（例: latency_ms 等）にも対応するロジックがあります。
- process_priority の設定はプラットフォーム依存です。権限不足で失敗することがあるためログで警告が出ますが処理は続行されます。
- Streamlit ダッシュボードは監視 DB を read-only URI で開くため、監視プロセスと同時に表示可能です。

---

必要に応じて README にサンプル .env.example、requirements.txt、起動ユニットファイル（systemd）や Dockerfile を追加できます。必要ならサンプル .env のテンプレートや systemd ユニットの例も作成しますので教えてください。
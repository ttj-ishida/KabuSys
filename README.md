# KabuSys

日本株向け自動売買システムの一部モジュール群（データ処理・リサーチ・ポートフォリオ構築、実行エンジン、監視、AI ユーティリティ等）。この README は、リポジトリ内の主要スクリプト／モジュールの概要、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を含みます。

- 市場データからのファクター計算・リサーチ（duckdb 経由で prices_daily / raw_financials を参照）
- ポートフォリオ構築（候補選定、重み付け、株数算出、セクター制約など）
- 実行エンジン（ブローカーとの発注・リコンシリエーション・リスク管理）
- 監視（システム状態・注文滞留・ドローダウン監視、LINE 通知、ダッシュボード）
- AI ユーティリティ（ニュースを LLM でスコア化、レジーム判定）
- 各種ツール（Paper Trading 検証レポート生成等）

設計方針のポイント：
- DuckDB / SQLite をデータ保存・分析に使用（外部 API 呼び出しは限定）
- 環境変数 / .env による設定（自動ロード機能あり）
- 本番／ペーパートレードを環境変数で切替可能（DB 分離、Mock ブローカー利用）
- フェイルセーフ設計（API リトライ、部分失敗時のデータ保護など）

---

## 主な機能一覧

- research: モメンタム / ボラティリティ / バリューのファクター計算（DuckDB）
- portfolio: 候補選定、等配分・スコア重み、リスク調整、ポジションサイズ算出
- execution: OrderManager / ExecutionEngine / Reconciler による発注・再同期
- monitoring:
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格異常の検出
  - RiskMonitor: ドローダウン・保有上限の監視とリスクログ
  - KillSwitch: フラグファイルを書き ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Push による通知（クールダウン付き）
  - Streamlit ベースの監視ダッシュボード
- ai:
  - news_nlp: ニュース記事を LLM（OpenAI）で銘柄別スコア化して ai_scores に書込
  - regime_detector: ETF（1321）の MA とマクロニュースを LLM で組合せ市場レジーム判定
- tools:
  - paper_verification_report: Paper Trading データから検証レポートを生成

---

## セットアップ手順

前提: Python 3.9+（duckdb, psutil, requests, openai, streamlit などが依存）

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb psutil requests openai streamlit
   ```

   実プロジェクトでは requirements.txt / poetry 等で依存を管理してください。

3. 環境変数を設定
   - 必須（運用機能を使う場合）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY
   - その他（任意、デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
     - PAPER_FILL_MODE (paper_trading の成行/部分約定挙動: instant | partial | never | reject)
     - PID_FILE_PATH, KILL_FLAG_PATH 等

   ルートに `.env` / `.env.local` があれば自動で読み込みます（既存 OS 環境変数は保護）。自動読み込みを無効化するには:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

注意: Paper Trading 運用では KABUSYS_ENV=paper_trading に設定すると MockBrokerClient が使われ、paper_sqlite_path に切替えられます（本番 DB と分離）。

---

## 使い方（主な実行方法）

- 監視プロセスを起動（ポーリングループ）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 監視は常に settings.sqlite_path（monitoring DB）を使用（環境に依存せず本番 DB パスを用いる設計）。
  ```
  python -m kabusys.run_monitoring
  # または
  python src/kabusys/run_monitoring.py
  ```

- 実行エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV=paper_trading の場合、Mock ブローカー & paper DB を使用（data/paper_trading.db）。
  ```
  python -m kabusys.run_execution
  # or
  python src/kabusys/run_execution.py
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスの指定（省略時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db を参照）
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Streamlit 監視ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  （`-- --db` のように streamlit 引数とスクリプト引数を分離して渡します）

- AI 機能（ニューススコアリング / レジーム判定）
  - `OPENAI_API_KEY` を設定した上で、モジュールの関数を呼び出す（例: kabusys.ai.news_nlp.score_news）。
  - CLI ラッパーは存在しないため、スクリプト／ジョブから呼ぶ想定です。

注意ポイント:
- run_monitoring / run_execution 起動時、最初に set_process_priority("high") が呼ばれ、可能ならプロセス優先度を上げます（psutil に依存）。権限不足などで失敗しても警告を出して続行します。
- run_execution は起動時に init_monitoring_db() を呼んで監視用テーブルの存在を保証します（冪等）。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH に記録する
- JQUANTS_REFRESH_TOKEN: J-Quants API
- KABU_API_PASSWORD: kabu ステーション用パスワード
- OPENAI_API_KEY: OpenAI を用いた AI 機能で必須
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（default: instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: プロセス制御 / kill フラグファイルのパス
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag をクリアするフラグ（"1" で有効）

その他はソースの Settings クラスを参照してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / .env ロード、Settings クラス（アプリ設定の集中管理）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール（CLI）
  - data/ (別モジュール想定 — ここでは duckdb 操作用ユーティリティ等が存在)
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・cap・丸めロジック
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - execution/
    - order_manager.py — 発注の高レベル管理（Order 作成→送信等）
    - reconciler.py — 起動時の注文・ポジション再同期
    - （その他: broker_factory, execution_engine, order_repository, order_record 等は実装ファイル群）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ作成 / ログ書き込みユーティリティ
    - system_monitor.py — CPU/メモリ/ディスク、データ鮮度、PID チェック
    - trade_monitor.py — 注文滞留 / 約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限の監視
    - kill_switch.py — kill.flag 書込ロジック
    - alert_manager.py — LINE 通知ユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン（テスト用 run_once とループ run）
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - ai/
    - news_nlp.py — ニュース記事を LLM で銘柄別スコア化して ai_scores に書込
    - regime_detector.py — ETF MA と マクロニュース LLM によるレジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity のクロスプラットフォームユーティリティ

---

## 運用上の注意点（要確認）

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は起動時にテーブルを作成し、既存 DB に対する簡易マイグレーション（カラム追加）を行います。
- kill.flag / PID 管理:
  - KillSwitch は data/kill.flag を作成して ExecutionEngine 停止シグナルとします。Execution 起動時のクリア設定は Settings.kill_flag_clear_on_start を確認してください。
- Paper Trading:
  - paper_trading モードは本番 DB と完全に分離するよう意図されています。テスト・検証時は必ず KABUSYS_ENV=paper_trading を設定してください。
- AI / OpenAI:
  - OpenAI 呼び出しは API 利用制限やネットワークエラーに備えたリトライ実装がありますが、API キー管理とコストに注意してください。
  - スコアリング関数は部分的失敗に寛容な設計（失敗時は該当銘柄をスキップ・全体失敗時は 0 件書込）です。

---

## 参考コマンド（例）

- モニタ起動（60 秒間隔）
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン（Paper Trading）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading レポート（期間指定）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード（読み取り専用 DB を指定）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

この README はコードベースの主要な用途と運用上の要点をまとめたものです。詳細な設計・アルゴリズム（PortfolioConstruction.md、StrategyModel.md 等参照）やブローカー API 実装は別ドキュメント／モジュールに記載されています。追加のドキュメント化や運用手順が必要であれば教えてください。
README
======

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした小規模な Python コードベースです。本プロジェクトは以下の主要コンポーネントを含みます。

- 実売買を担当する ExecutionEngine（ブローカー抽象化、注文管理、リコンシリエーション）
- システム／注文／リスクの監視ロジック（Monitoring）
- ポートフォリオ構築・ポジションサイジング（Portfolio）
- ファクター計算・リサーチユーティリティ（Research）
- ニュースの LLM によるセンチメントスコアリング・レジーム判定（AI）
- 運用支援ツール（Paper Trading 用検証レポート、Streamlit ダッシュボード等）

主な設計方針
- DuckDB を用いた価格・ファクタ計算（分析系）と、SQLite を使った監視ログ/取引ログの永続化を分離
- 本番／paper_trading（ペーパートレード）環境の明確な分離
- 外部 API 呼び出し（ブローカー / OpenAI 等）は抽象化とフェイルセーフ処理を重視

機能一覧
--------
- Execution
  - 注文生成・送信・状態同期（OrderManager / Reconciler）
  - リスク管理（RiskManager 等、設定に基づく制約）
  - paper_trading モード時は MockBroker を使用し専用 SQLite へ記録
- Monitoring
  - システム状態監視（CPU/メモリ/ディスク）、プロセス生存確認、データ鮮度チェック
  - 注文滞留・約定価格異常検出
  - ドローダウン／ポジション上限監視、kill.flag による ExecutionEngine 停止指示
  - LINE による通知（AlertManager）
  - Streamlit ダッシュボード（監視 UI）
- Portfolio
  - 候補選定、等配分/スコア配分、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイジング（単元丸め、aggregate cap など）
- Research
  - Momentum/Volatility/Value などのファクター計算（DuckDB）
  - 将来リターン、IC（情報係数）、統計サマリー
- AI
  - ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に書込む
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
- ユーティリティ
  - Paper Trading の検証レポート生成スクリプト
  - プロセス優先度 / CPU affinity 設定ユーティリティ

前提条件
--------
- Python 3.10+
- 必要パッケージ（一例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- データディレクトリ（デフォルト: data/）に書き込み可能であること

環境変数（主なもの）
-------------------
設定は .env / .env.local（プロジェクトルート）または OS 環境変数から読み込まれます。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

主なキー（省略時はコメントのデフォルト）:
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード ("instant" | "partial" | "never" | "reject")（デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag ファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で利用、デフォルト: 60）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら送信はスキップ）

セットアップ手順
--------------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化する:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトで requirements.txt がある場合はそちらを使ってください）

3. データディレクトリを作成:
   - mkdir -p data

4. .env を作成（.env.example を参考に環境変数を設定）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - KABUSYS_ENV=paper_trading
   - など

5. （任意）paper_trading 用 DB を既定パスに用意するか、実行時に指定します。Monitoring DB は起動時に自動でテーブル作成（migration を含む）されます。

使い方
------

起動スクリプト
- 監視ループ（SystemMonitor の単発起動ではなく簡易ポーリング）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を変更可能（秒、1 以上）。不正値は 60 秒にフォールバック。

- 実行エンジン（ExecutionEngine）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB とは分離されます。
  - 実行開始時に PID file（デフォルト data/execution.pid）を書き、kill.flag による停止を監視します。

Streamlit ダッシュボード（リアルタイム監視 UI）
- 起動方法:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 監視 DB に対して読み取り専用で接続し、Positions / Orders / System / Overview を表示します。

Paper Trading 検証レポート
- ツール:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で PAPER_TRADING_SQLITE_PATH を上書き可能
  - 出力は標準出力にテキスト形式のレポートを表示（稼働率、成功率、レイテンシ指標、PASS/FAIL 判定）

AI 関連
- ニュースセンチメント（ai_scores へ書き込む）:
  - 直接呼び出す場合の例:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  （conn は DuckDB 接続）
  - OPENAI_API_KEY が必要（api_key を None にすると環境変数を参照）

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="...")

プロセス優先度・CPU 固定
- 起動スクリプトは起動直後に set_process_priority("high") を呼んでいます。必要に応じて utils/process_priority.py の set_cpu_affinity を利用できます。

監視・停止シグナル
- KillSwitch は監視で検出された重大なリスク（例: ドローダウン超過、ポジション上限）時に KILL_FLAG_PATH（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine はこのフラグファイルを検知して停止するよう設計されています。

注意事項 / 運用のヒント
- init_monitoring_db は冪等であり、既存 DB へ必要なテーブル・カラムを作成します（マイグレーション処理を含む）。
- paper_trading は本番データと完全に分離するため、テストや検証に便利です。
- OpenAI API 呼び出しはエラー時にリトライやフォールバックを行う設計ですが、API キーやレート制限に注意してください。
- デフォルトの DB パスやファイルは Settings クラスで定義されています。別パスを利用する場合は環境変数で上書きしてください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数読み込み / Settings
- run_monitoring.py              — SystemMonitor のポーリング起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py               — SQLite 監視ログの永続化層（init + CRUD）
- system_monitor.py              — CPU/メモリ/ディスク・データ鮮度・PID チェック
- trade_monitor.py               — 注文滞留・約定価格異常チェック
- risk_monitor.py                — ドローダウン・ポジション制限監視
- monitoring_engine.py           — 各 Monitor を束ねるループ（テスト用 run_once あり）
- kill_switch.py                 — kill.flag 書込ロジック
- alert_manager.py               — LINE 通知（クールダウン付き）
- streamlit_dashboard.py         — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py               — 注文状態管理（Order State Machine 外向け API）
- reconciler.py                  — 起動時リコンシリエーション（注文・ポジション突合）
- (その他 execution 関連モジュール: broker_factory, execution_engine, order_repository 等)

src/kabusys/portfolio/
- portfolio_builder.py           — 候補選定・重み計算
- position_sizing.py             — 株数計算・単元丸め・aggregate cap
- risk_adjustment.py             — セクター制限・レジーム乗数
- __init__.py

src/kabusys/research/
- factor_research.py             — Momentum / Volatility / Value 等の計算
- feature_exploration.py         — 将来リターン / IC / 統計サマリー
- __init__.py

src/kabusys/ai/
- news_nlp.py                    — ニュースを LLM でスコアリングし ai_scores へ書込む
- regime_detector.py             — マクロセンチメント + MA200 によるレジーム判定
- __init__.py

src/kabusys/tools/
- paper_verification_report.py   — Paper Trading 検証レポート出力ツール
- __init__.py

src/kabusys/utils/
- process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ

その他
-----
- データファイル（デフォルト）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/kill.flag

サポート / 開発メモ
-----------------
- ユニットテストや CI の設定は含まれていませんが、モジュールは純粋関数設計や副作用の少ないインタフェースを意識して実装されています。DuckDB / SQLite 接続を注入することで単体テストが容易です。
- AI 周り（OpenAI 呼び出し）はテスト用に _call_openai_api を patch して差し替えられる設計です。

以上が本リポジトリの概要と利用方法です。実運用前に .env の設定、DB のバックアップ、OpenAI/ブローカー API の権限・コスト管理を十分ご確認ください。
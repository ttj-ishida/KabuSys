README
======

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主に「注文実行（Execution）」「監視（Monitoring）」「ポートフォリオ構築」「リサーチ」「ニュース NLP / レジーム判定」などの機能を提供し、実運用（live）／模擬運用（paper_trading）を想定した設計になっています。

特徴
----
- ExecutionEngine：ブローカークライアント経由で注文発行・状態管理・リコンシリエーションを実行
- Paper Trading モード：KABUSYS_ENV=paper_trading でブローカーをモック化し、本番 DB と完全分離して data/paper_trading.db に記録
- Monitoring：システム稼働・データ鮮度・注文滞留・約定異常・ドローダウン等を定期チェックし SQLite に永続化
- Kill Switch：ドローダウンなどの条件で stop フラグ（data/kill.flag）を書き込み、ExecutionEngine を停止可能
- AlertManager：LINE Messaging API によるアラート送信（クールダウン付き）
- Streamlit Dashboard：監視データの可視化用ダッシュボードを提供（streamlit 対応）
- Research：DuckDB を用いたファクター計算、将来リターン・IC 計算、統計サマリ等
- AI（ニュース NLP / レジーム検出）：OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価・市場レジーム推定
- ユーティリティ群：プロセス優先度設定、ポートフォリオ構築（候補選定／重み付け／ポジションサイズ計算）など純粋関数を多数実装
- 検証ツール：paper_trading の検証レポート生成スクリプトを同梱

前提条件 / 依存関係
-------------------
主に以下が必要です（プロジェクトで利用されている主要パッケージ）:
- Python 3.9+
- duckdb
- psutil
- requests
- streamlit（ダッシュボードを使う場合）
- openai（AI 機能を使う場合）

requirements.txt が無い場合は必要なパッケージを個別にインストールしてください:
pip install duckdb psutil requests streamlit openai

セットアップ手順
---------------
1. リポジトリをクローン（例）:
   git clone <リポジトリURL>
   cd <リポジトリ>/src

2. 仮想環境作成（任意）:
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール:
   pip install duckdb psutil requests streamlit openai

4. data ディレクトリの作成（自動で作られることがあるが明示的に作成しておくと安心）:
   mkdir -p data

5. 環境変数を設定（.env をプロジェクトルートに置くと自動で読み込まれます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   主要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合、必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading 時の約定挙動
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
   - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、default 60）

   簡易 .env 例（プロジェクトルート）:
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   KABUSYS_ENV=development
   PAPER_FILL_MODE=instant
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=

使い方
-----

起動スクリプト
- 監視ループを起動（Monitoring）
  python -m kabusys.run_monitoring
  環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。

- 実行エンジン（ExecutionEngine）を起動
  python -m kabusys.run_execution
  KABUSYS_ENV=paper_trading を設定するとモックブローカーを使用し、paper_trading 用 DB に記録されます。

停止方法
- プロセス実行中にプロセスを停止する一般的手段として Ctrl+C（KeyboardInterrupt）を利用できます。
- 外部から安全に停止させたい場合はプロジェクトルートの data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します。
- KillSwitch（ドローダウン等の条件で自動停止）は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります（KillSwitch は監視側ロジックで生成されます）。

ストリームリット ダッシュボード
- 監視 DB を読み取り専用で開いて可視化します。起動例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- paper_trading DB に対して検証レポートを生成します:
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

AI / レジーム関連
- OpenAI API を利用する機能（ニュース NLP / regime_detector）は OPENAI_API_KEY を環境変数に設定してください。
- score_news / score_regime 等の関数は duckdb 接続と target_date を受け取り、DB 内の raw_news / prices_daily 等のテーブルを参照して書き込みを行います。

注意点
- Monitoring は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を参照します（監視ログは本番 DB に集約する設計）。
- Paper Trading モードでは paper_sqlite_path を使用し本番 DB と分離されます。
- 初回起動時に必要テーブルは init_monitoring_db() により作成されます（冪等）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。CWD に依存しません。

主要モジュール / ディレクトリ構成
----------------------------
src/kabusys/
- __init__.py                — パッケージ定義（バージョン等）
- config.py                  — 環境変数/設定読み込み（.env サポート、Settings クラス）
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト

subpackages:
- execution/
  - order_manager.py         — 注文フロー管理（OrderManager）
  - reconciler.py            — 再起動時のリコンシリエーション
  - order_repository.py      — （存在）OrderRepository（SQLite）を通じた注文永続化
  - execution_engine.py      — 実行エンジン本体（EngineConfig, ExecutionEngine）  ※一部ファイルは抜粋に含まれていませんが想定
  - broker_factory.py        — ブローカークライアント生成（実ブローカー or Mock）

- monitoring/
  - monitoring_db.py         — SQLite を用いた監視ログ永続化層（テーブル定義 / MonitoringDB）
  - system_monitor.py        — システム状態・データ鮮度チェック（SystemMonitor）
  - trade_monitor.py         — 注文滞留・約定異常チェック（TradeMonitor）
  - risk_monitor.py          — ドローダウン・ポジション上限チェック（RiskMonitor）
  - kill_switch.py           — kill.flag の作成・管理（KillSwitch）
  - alert_manager.py         — LINE 通知（AlertManager）
  - monitoring_engine.py     — 各 Monitor を束ねるループ（MonitoringEngine）
  - streamlit_dashboard.py   — Streamlit ダッシュボード

- portfolio/
  - portfolio_builder.py     — 候補選定・等重/スコア重み付け
  - position_sizing.py       — 株数決定・リスク制限・単元丸め
  - risk_adjustment.py       — セクターキャップ・レジーム乗数

- research/
  - factor_research.py       — モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
  - feature_exploration.py   — 将来リターン計算・IC・統計サマリ

- ai/
  - news_nlp.py              — raw_news を LLM で評価して ai_scores に書き込む
  - regime_detector.py       — ETF MA とマクロセンチメントを合成して market_regime を書き込む

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- utils/
  - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

その他（DB / ファイル）
- data/monitoring.db          — 監視ログ（SQLite。デフォルト）
- data/paper_trading.db       — Paper Trading 時の SQLite（分離）
- data/kabusys.duckdb         — DuckDB（価格データなど）
- data/execution.pid          — ExecutionEngine の PID ファイル（パスは Settings で変更可能）
- data/stop_requested.flag    — 外部からの停止要求を表すファイル（存在するとループが終了）
- data/kill.flag              — KillSwitch が作成する停止フラグ（Execution を停止させる目的）

開発メモ / 拡張ポイント
-----------------------
- DuckDB / prices_daily / raw_financials 等のテーブルは research / ai モジュールで参照されます。データ投入は別途データパイプライン（kabusys.data.pipeline 等）を利用してください。
- paper_trading 用のモックブローカーや手数料・スリッページの振る舞いは PAPER_FILL_MODE で調整できます。
- OpenAI 呼び出しはリトライや JSON 検証の保護が入っていますが、API 仕様変更時は呼び出しラッパーの差し替えを検討してください。
- Monitoring のしきい値（CPU/MEM/DISK/ドローダウン等）は Settings 経由で環境変数から調整可能です。

サポート / テスト
-----------------
- 現状 README 内にテスト手順は含まれていません。ユニットテストや CI の追加を推奨します。
- AI 関連は外部 API を利用するため、ローカルでの単体テスト時には _call_openai_api をモックする設計になっています（コード内に注記あり）。

ライセンス
---------
プロジェクトのライセンス情報が未提供の場合はリポジトリの LICENSE を参照してください。

---
この README はコードベースの主要部分をもとに作成しています。運用前に .env の設定、DB 初期データ（prices / raw_news 等）の準備、及びブローカー接続情報の確認を行ってください。
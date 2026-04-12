# KabuSys — README

本プロジェクトは日本株自動売買システム（KabuSys）の一部モジュール群を含みます。  
この README ではプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめます。

注意：この資料はソースコード（src/kabusys 以下）をもとに作成しています。実行には追加の依存関係や実運用用の設定が必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するコンポーネント群です。主な責務は次のとおりです。

- シグナルに基づく発注・注文管理（Execution）
- リコンシリエーション（再起動後の状態同期）
- リスク管理（ドローダウン・ポジション上限等）
- 監視（システム状態、注文滞留、アラート）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リサーチ（ファクター計算・特徴量解析）
- AI を用いたニュースセンチメント / レジーム判定
- Paper Trading 向け検証レポートの生成

設計上の特徴：
- DuckDB / SQLite をデータレイヤに利用
- OpenAI API（gpt-4o-mini 等）との連携機能（ニュースセンチメント、レジーム判定）
- 環境変数 / .env ファイルからの設定読み込み（自動読込を無効化可能）
- モジュールはできるだけ純粋関数・副作用少なめで設計

---

## 機能一覧（抜粋）

- Execution
  - OrderManager：発注ワークフロー（作成 → 送信 → 同期 → エラー処理）
  - Reconciler：起動時の注文・ポジション照合
  - Broker クライアント抽象化（paper_trading では MockBroker を利用可能）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン検知・ポジション上限監視
  - KillSwitch：フラグファイルで ExecutionEngine 停止指示
  - AlertManager：LINE によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only 接続で監視情報可視化）
- Portfolio
  - 銘柄候補選定、等重・スコア重み、リスク調整、ポジションサイズ決定
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - news_nlp.score_news：ニュースを LLM で評価し ai_scores に書き込み
  - regime_detector.score_regime：ETF MA + マクロセンチメントで市場レジーム判定
- Tools
  - paper_verification_report：Paper Trading DB を集計して PASS/FAIL 判定するレポート生成

---

## セットアップ手順（開発 / 実行前準備）

前提
- Python 3.10+（typing で | 型注釈を使用）
- OS: Linux / macOS / Windows（プロセス優先度設定で差異有り）

1. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai requests streamlit
   - 実際のプロジェクトでは requirements.txt を用意している可能性があるため、あればそれを利用してください。

3. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主な環境変数（コード内で参照されるもの）：
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | ...)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (paper_trading の約定モード: instant | partial | never | reject)
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START（"1"で開始時に kill.flag を削除）

4. データディレクトリの作成
   - data/ ディレクトリを作成し、必要な DuckDB/SQLite ファイルや PID/flag 用フォルダが書き込み可能であることを確認してください。

---

## 使い方（主要スクリプト）

以下はソース内にある起動スクリプトやツールの起動方法例です。プロセス優先度設定や DB 初期化は各スクリプト内部で行われます。

1. Monitoring の単独起動
   - 目的: SystemMonitor のポーリングループを起動（system_status / risk_logs などを recording）
   - 実行:
     - KABUSYS_ENV の値に関わらず monitoring は本番 sqlite_path を使用します。
     - 環境変数でポーリング間隔を上書き可: MONITOR_POLL_INTERVAL（秒）
     - コマンド例:
       - python -m kabusys.run_monitoring
       - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

2. ExecutionEngine 起動（発注エンジン）
   - 特記事項: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い、paper_trading 用 DB（data/paper_trading.db）を使用し本番 DB と分離します。
   - 実行:
     - python -m kabusys.run_execution
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

3. Streamlit 監視ダッシュボード（read-only）
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - DB を読み取り専用モードで開きます。MonitoringEngine が稼働していることを前提とします。

4. Paper Trading 検証レポート生成
   - スクリプト:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --from YYYY-MM-DD, --to YYYY-MM-DD
     - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数を上書き）

5. AI 機能（ニュース / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と target_date（date）を渡して実行すると ai_scores テーブルへ書き込みます。
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF の MA とマクロニュースの LLM センチメントを合成して market_regime テーブルに書き込みます。
   - 実行には OPENAI_API_KEY の設定が必要（引数で渡すことも可能）。

6. kill.flag 操作（手動）
   - KillSwitch は data/kill.flag の存在で ExecutionEngine 停止指示を出します。
   - flag を手動でクリアする場合はファイルを削除してください、または KillSwitch.clear() を利用。

---

## 設定に関する注意点・挙動

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env / .env.local をロードします。
  - OS 環境変数は保護され、.env.local の override でも既存の OS 環境変数は上書きされません。
- KABUSYS_ENV の意味
  - development（デフォルト）
  - paper_trading：発注は MockBroker、DB は data/paper_trading.db を使用して本番と分離
  - live：実際のブローカー接続を想定
- Monitoring と Execution の DB
  - monitoring（system_status / trade_logs / risk_logs / dashboard 等）は settings.sqlite_path（デフォルト data/monitoring.db）を使用します。run_monitoring は環境にかかわらず本番 sqlite_path を参照します。
  - run_execution は KABUSYS_ENV に応じて paper_trading 用 DB を使う（is_paper 判定）。
- PAPER_FILL_MODE（paper_trading）
  - instant / partial / never / reject のいずれか。無効値だと起動時に例外が出ます。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼びます。psutil によってプラットフォーム依存で実行されます。権限がない場合は警告ログでスキップされます。

---

## ディレクトリ構成（主要ファイル・モジュール説明）

（src/kabusys をルートとする抜粋）

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス：環境変数 / .env の読み込みとアクセスラッパー
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（BrokerFactory 経由で本番 / Mock を切替）
  - tools/
    - paper_verification_report.py：Paper Trading DB の集計レポート
  - monitoring/
    - monitoring_db.py：SQLite ベースの永続化層（テーブル初期化 / CRUD）
    - system_monitor.py：システム状態・データ鮮度チェック
    - trade_monitor.py：滞留注文 / 約定異常検出
    - risk_monitor.py：ドローダウン・ポジション上限監視
    - kill_switch.py：kill.flag 管理
    - alert_manager.py：LINE 通知ラッパー
    - monitoring_engine.py：複数モニタを束ねるポーリングエンジン
    - streamlit_dashboard.py：監視ダッシュボード（Streamlit）
  - execution/
    - order_manager.py：注文作成 / 送信の高位 API
    - reconciler.py：起動時の注文/ポジション同期ロジック
    - order_repository.py, order_record.py, broker_factory 等（発注関連）
  - portfolio/
    - portfolio_builder.py：候補選定・重み計算
    - position_sizing.py：株数決定・単元丸め・投下金額制約
    - risk_adjustment.py：セクター上限・レジーム乗数
  - research/
    - factor_research.py：ファクター計算（Momentum / Volatility / Value）
    - feature_exploration.py：将来リターン、IC、統計サマリ等
  - ai/
    - news_nlp.py：ニュースを LLM でスコアリングして ai_scores に書き込み
    - regime_detector.py：ETF MA + マクロセンチメントで市場レジーム判定
  - data/ （想定されるデータ格納先）
    - kabusys.duckdb（DuckDB）
    - monitoring.db（監視 SQLite）
    - paper_trading.db（paper trading 用 SQLite）
  - utils/
    - process_priority.py：プロセス優先度 / CPU affinity ユーティリティ

---

## 実運用上の注意

- DB のバックアップや権限管理を適切に行ってください。
- OpenAI API 呼び出しにはコストとレート制限があります。news_nlp と regime_detector はリトライやバッチ化のロジックがありますが、運用時はキーと使用量に注意してください。
- MONITOR_POLL_INTERVAL などの間隔を短くしすぎると負荷や API レートに影響します。
- run_execution / run_monitoring はプロセス管理（systemd 等）で起動・監視することを推奨します。PID ファイルや kill.flag を用いた停止シグナル処理が組み込まれています。
- Paper Trading は本番 DB と完全に分離する設計ですが、設定ミスで本番 DB を参照しないよう環境変数管理を慎重に行ってください。

---

## 追加情報 / デバッグヒント

- ログレベルは LOG_LEVEL 環境変数で制御できます（INFO がデフォルト）。
- .env のパースは config._parse_env_line でかなり柔軟に処理されます（export 形式やクォート、コメント対応）。
- MonitoringDB.init_monitoring_db は冪等にテーブルを作成し、既存 DB に対する簡単なマイグレーション（カラム追加）処理も行います。

---

この README はソースコードの要点をまとめたものです。実際の導入・運用時は追加のドキュメント（デプロイ手順、監視・アラート運用ルール、Backtest データ取り扱い方針 等）を整備してください。質問や具体的な実行例が必要であれば、環境（OS、Python バージョン、使用する DB ファイルの場所、目的）を教えてください。
# KabuSys

日本株自動売買システムの一部を実装したコードベース向け README（日本語）。

この README はリポジトリ内の主要モジュール（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニュース NLP など）に基づき、プロジェクト概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成をまとめたものです。

注意: 本 README はソースコードの注釈や docstring を参照して記述しています。実運用の前に .env 設定やブローカークライアント実装の確認を行ってください。

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのモジュール群です。主な責務は次の通りです。

- シグナルに基づく発注（ExecutionEngine / OrderManager）
- 実行に関わるリスク管理（RiskManager）
- 起動時のリコンシリエーション（Reconciler）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- 監視用ダッシュボード（Streamlit）
- ポートフォリオ構築・配分・ポジションサイズ計算（portfolio パッケージ）
- リサーチ・ファクター計算（research パッケージ）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（ai パッケージ）
- Paper Trading 向けの検証ツール（tools）

設計上のポイント:
- DuckDB / SQLite をデータ永続化に使用
- 実行環境（KABUSYS_ENV）により paper_trading と live を分離
- LLM API 呼び出しはリトライやフォールバック処理を行いフェイルセーフ設計

## 主な機能一覧

- Execution
  - Order 作成・送信・同期（OrderManager / Reconciler）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使い data/paper_trading.db に記録
- Monitoring
  - システム状態、データ鮮度、滞留注文、約定異常、ドローダウンなどの監視
  - kill.flag による ExecutionEngine 停止シグナル生成
  - LINE によるアラート通知（AlertManager）
  - Streamlit による監視ダッシュボード
- Portfolio construction
  - 候補選定、等重/スコア重み、リスク調整（セクター上限、レジーム乗数）、ポジションサイジング
- Research
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC 計測、統計サマリー
- AI
  - ニュースの LLM センチメントスコアリング（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
- Tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

## セットアップ手順

前提
- Python 3.10+ を想定（PEP 604 の型合成や型注釈を使用）
- プロジェクトルートに pyproject.toml または .git があると自動で .env を読み込みます（デフォルト）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必要パッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例（pip）:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
   - 実プロジェクトでは pyproject.toml / requirements.txt に基づきインストールしてください。

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（および `.env.local`）を配置して必要な環境変数を設定できます。
   - 自動読み込み: OS 環境変数 > .env.local > .env の優先順位で読み込みされます。
   - 必須/推奨の環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合）
     - KABUSYS_ENV — execution 環境（development | paper_trading | live）。デフォルトは development
     - PAPER_TRADING_SQLITE_PATH — paper trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
   - 例 .env（サンプル）
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     ```

4. データディレクトリ
   - デフォルトで使用されるデータディレクトリは `data/`。必要に応じて作成しておくと便利です。
     ```
     mkdir -p data
     ```

## 使い方（主な実行方法）

以下は各エントリポイントの実行方法と簡単な説明です。

1. Execution エンジン（取引実行）
   - スクリプト: src/kabusys/run_execution.py
   - 実行:
     ```
     python -m kabusys.run_execution
     ```
   - 挙動:
     - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続します。
     - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用してブローカーは MockBrokerClient になります（本番 DB とは分離されます）。
     - PID ファイル (Settings.pid_file_path, デフォルト data/execution.pid) を参照してプロセス状態を管理します。

2. Monitoring 起動（ポーリング）
   - スクリプト: src/kabusys/run_monitoring.py
   - 実行:
     ```
     python -m kabusys.run_monitoring
     ```
   - 挙動:
     - システム/トレード/リスク関連のチェックを周期的に実行します（デフォルト 60 秒）。
     - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視は本番DBを参照する設計）。

3. Streamlit 監視ダッシュボード
   - スクリプト: src/kabusys/monitoring/streamlit_dashboard.py
   - 実行:
     ```
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     ```
   - 説明:
     - 監視 DB を読み取ってダッシュボードを表示します（読み取りモード推奨）。
     - DB が存在しない場合はエラー表示されます。MonitoringEngine を先に起動してデータを生成してください。

4. Paper Trading 検証レポート生成
   - スクリプト: kabusys.tools.paper_verification_report
   - 実行例:
     ```
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
     ```
   - 出力:
     - 指定期間（または DB 全体）の稼働率、注文成功率、送信率、レイテンシ等の集計と PASS/FAIL 判定を標準出力に表示します。

5. AI モジュール（ニュース NLP / レジーム判定）
   - 関数 API から呼ぶ形:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 必要:
     - OPENAI_API_KEY を環境変数で設定するか、関数引数で渡す必要があります。
   - 注意:
     - API 呼び出しはリトライ・フォールバック（失敗時はゼロ等）を実装していますが、利用時は API 使用料に注意してください。

その他のポイント:
- 設定は `kabusys.config.Settings` で一元管理されます。Settings は自動的に .env ファイルをロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化可）。
- kill flag: `Settings.kill_flag_path`（デフォルト data/kill.flag）。RiskMonitor / KillSwitch により書き込まれ、ExecutionEngine はそれを検知して停止する設計です。

## 環境変数の主な一覧

- KABUSYS_ENV: development | paper_trading | live（実行環境）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill flag パス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring 用、デフォルト 60）
- PAPER_FILL_MODE: paper trading の約定挙動（instant | partial | never | reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知のための設定

## ディレクトリ構成（抜粋）

（リポジトリの src/kabusys 以下の主要ファイルを示します）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定読み込み
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py    — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py              — マーケットレジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py                — SQLite モデル（監視ログ）
    - system_monitor.py               — システム / データ鮮度監視
    - trade_monitor.py                — 注文滞留 / 約定異常監視
    - risk_monitor.py                 — ドローダウン / ポジション上限監視
    - kill_switch.py                  — kill.flag 管理
    - alert_manager.py                — LINE 通知
    - monitoring_engine.py            — 監視ループのオーケストレーション
    - streamlit_dashboard.py          — Streamlit ダッシュボード
  - portfolio/
    - __init__.py
    - portfolio_builder.py            — 候補選定・重み計算
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
    - position_sizing.py              — 発注株数計算
  - research/
    - __init__.py
    - factor_research.py              — ファクター計算（momentum/value/volatility）
    - feature_exploration.py          — 将来リターン・IC・統計
  - execution/
    - order_manager.py                — OrderManager（Order State Machine 周辺）
    - reconciler.py                   — 起動時状態同期（リコンシリエーション）
    - （その他 execution 関連ファイル… broker_factory 等）
  - utils/
    - __init__.py
    - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (データファイル置き場、デフォルト)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

（上記はソース内に存在する主要ファイルの抜粋です。実際のリポジトリにはさらにモジュール/実装がある可能性があります。）

## 動作上の注意 / 運用メモ

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存 DB にないカラムを追加するマイグレーションロジックを一部持っています。
- PID / kill.flag
  - Execution 側は PID ファイルを出し、Monitoring はその PID をチェックして stale PID を検出した場合に削除・ログ記録します。
  - KillSwitch は条件成立時に kill.flag を書き込み、Execution 起動中に存在を検知して安全停止させる想定です。
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、Execution は paper_trading 用 DB を使用し本番データと完全分離します。
- LLM / OpenAI
  - AI モジュールは OpenAI API（gpt-4o-mini 等）を用いる設計です。API キーと利用料金に注意してください。
  - レスポンスのバリデーションやリトライを備えていますが、LLM の出力は保証されないため結果の取り扱いには注意してください。
- 権限
  - set_process_priority は OS に依存する操作のため権限不足で警告を出してスキップされる場合があります。

## 連絡・貢献

この README はコード内の docstring を元に作成されています。実際に運用・拡張を行う際は次を確認してください。

- ブローカークライアント実装（BrokerClientFactory / BrokerAPIProtocol）
- ExecutionEngine の具体的なワークフロー設定
- 実運用時の監視・通知設定（LINE トークン等）
- セキュリティ（API キーの管理、権限あるユーザーでの実行）

貢献や質問がある場合はリポジトリの issue / PR を通してご連絡ください。

---

必要であれば、この README をベースに例示的な .env.example、systemd ユニットファイル例、Dockerfile、または運用手順（デプロイ手順）を別途作成します。どれを追加するか教えてください。
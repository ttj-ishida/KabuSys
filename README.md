# KabuSys — README

KabuSys は日本株自動売買向けのライブラリ／実行フレームワークです。本リポジトリには以下の機能群を含みます：注文実行エンジン、監視（モニタリング）機能、ポートフォリオ構築ロジック、ファクター計算・リサーチ、ニュース NLP（OpenAI を利用したセンチメント評価）など。

以下はコードベースに基づく README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド例）
- 環境変数（主要な設定）
- ディレクトリ構成
- 補足・注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買システム用ユーティリティ群および実行コンポーネント群です。設計上のポイントは以下です。

- 注文ライフサイクル管理（OrderManager / OrderRepository / Reconciler）
- 実際のブローカー呼び出し（本番）と Mock ブローカー（paper_trading）の分離
- モニタリング（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE Push）
- ダッシュボード（Streamlit）による可視化
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限等）は純粋関数で実装
- DuckDB（市場データ・ファクター計算）と SQLite（監視ログ・注文ログ）を使ったデータ層
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価・レジーム判定（AI 部分は API キー必須）

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（完全分離の DB）モードをサポート
  - ブローカーファクトリ経由で BrokerClient を切り替え
  - ExecutionEngine の起動およびセッション実行
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングして監視ログを記録
  - ポーリング間隔は環境変数で調整可能
- 監視エンジン（MonitoringEngine）
  - System / Trade / Risk の各 Monitor を束ね、KillSwitch と AlertManager を連携
- 監視 DB ラッパー（monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを提供
  - マイグレーション（既存カラム追加）を含む init 関数
- Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）
  - 監視 DB を読み取り可視化
- ポートフォリオモジュール（portfolio）
  - 候補選定、等金額/スコア加重の重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン計算、IC 計算、統計サマリ
  - DuckDB を利用して SQL ベースで高速に実行
- AI 関連（ai）
  - news_nlp: raw_news を OpenAI に送って銘柄ごとのセンチメントを ai_scores に格納
  - regime_detector: ETF（1321）の ma200 とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を判定
- ユーティリティ
  - process_priority: プロセス優先度・CPU affinity 設定（Windows / POSIX に対応）
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプト

---

## セットアップ手順

※ 以下はコードベースから推測した一般的なセットアップ手順です。実行環境に合わせて適宜調整してください。

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成（推奨 Python >= 3.10）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/Mac
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 本コードで使われている主なライブラリ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - requirements.txt がない場合は手動でインストール:
     ```bash
     pip install duckdb psutil requests openai streamlit
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須: KABUSYS_ENV、KABU_API_PASSWORD、JQUANTS_REFRESH_TOKEN（使用機能による）等（下記「環境変数」参照）。

5. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

6. DuckDB / SQLite ファイルは実行時に作成・初期化されます（init_monitoring_db が自動でテーブルを作成します）。

---

## 使い方（起動コマンド例）

- 監視ループ起動（SystemMonitor をポーリングして監視ログを記録）
  ```bash
  # デフォルト: ポーリング間隔 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）
  python -m kabusys.run_monitoring
  ```

- 実行エンジン起動（注文送信等を行うメインプロセス）
  ```bash
  # KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Streamlit 監視ダッシュボード起動
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 系機能（ニューススコア / レジーム判定）はプログラムから呼び出します。OpenAI API キーが必要です。
  - 例: ai.score_news / ai.score_regime を Python スクリプトや REPL で利用

---

## 環境変数（主要な設定）

Settings クラスで参照・検証される主要な環境変数（デフォルト値／意味）：

- KABUSYS_ENV: 起動環境
  - 有効値: development / paper_trading / live
  - デフォルト: development

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須の場合あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）

- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）

- PAPER_FILL_MODE: Paper Trading の fill 動作（instant / partial / never / reject、デフォルト instant）

- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill スイッチ用フラグファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill flag をクリアするか（"1" で有効）

- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env 自動ロードを無効化

注意:
- run_monitoring は監視用途の SQLite（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に関わらず）。
- run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離します。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主なファイル / モジュール構成（抜粋）です。パスは src/kabusys 以下を示します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード含む）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度／CPU affinity 設定ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite 監視 DB 層（init + CRUD）
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - trade_monitor.py       — 注文滞留 / 約定異常価格チェック
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の作成 / 管理
    - alert_manager.py       — LINE Push 通知ラッパー
    - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py    (存在を前提に呼び出し)
    - broker_factory.py      (実行環境に応じた BrokerClient の生成)
    - broker_api.py          (Broker API のインターフェース)
    - order_record.py
    - order_* (その他 execution 関連)
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定 / 等配分・スコア配分
    - position_sizing.py     — 発注株数計算（単元丸め・リスク制限等）
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Volatility / Value のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - ai/
    - __init__.py
    - news_nlp.py            — OpenAI を使ったニュースセンチメント取得（ai_scores へ書込）
    - regime_detector.py     — ma200 + マクロセンチメントで市場レジーム判定
  - tools/
    - __init__.py
    - paper_verification_report.py — paper_trading DB に対する検証レポート出力ツール

（注）一部ファイル（execution_engine.py 等）は本抜粋では全文を示していませんが、起動スクリプトから呼び出されています。

---

## 補足・注意点

- 本システムは実際のブローカー API を利用する設計になっているため、live 環境で実行する場合は十分に注意してください。paper_trading モードでの十分な検証を推奨します。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キーを必要とし、呼出回数に応じた課金が発生します。rate limit / retry ロジックは入っていますが、運用ポリシーに従ってください。
- PID ファイル・kill.flag によるプロセス制御が実装されています。監視コンポーネントはこれらを監視して ExecutionEngine を停止させる仕組みです。
- monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に対して必要なカラムを追加するマイグレーション処理を行います。
- process_priority は OS に依存する処理（psutil）を行います。権限不足等で設定に失敗する場合は警告ログを出してスキップします。
- .env のパースは config.py に独自実装があります。特殊なクォートやエスケープにも対応しています。

---

以上がこのコードベースの概要および基本的な使い方です。必要に応じて README に実際の requirements.txt、.env.example、起動スクリプトの systemd / supervisor 用サンプルなどを追記してください。必要であれば .env.example のテンプレートや systemd ユニットのサンプルを作成しますので教えてください。
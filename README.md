# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視用ライブラリ群です。  
このリポジトリにはトレード実行エンジン、監視（モニタリング）、ポートフォリオ構築、ファクター計算、ニュース NLP などの機能が含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下です。

- 売買シグナルに基づく発注・リスク管理を行う ExecutionEngine
- 実行系の稼働状態・注文状態・リスクを監視する MonitoringEngine
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- DuckDB/SQLite を用いたデータ処理・ファクター計算・リサーチ
- ニュースを LLM（OpenAI）で解析して銘柄スコアを作成する AI モジュール
- Paper Trading（本番 DB とは分離して検証可能）と検証レポート生成ツール
- Streamlit を用いた監視ダッシュボード

設計方針としては、外部 API の呼び出しを最小限に抑え、ルックアヘッドバイアスへの配慮（日時の直接参照を避ける等）やフェイルセーフ（API失敗時のフォールバック）を組み込んでいます。

---

## 機能一覧（抜粋）

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker 抽象化と MockBroker（KABUSYS_ENV=paper_trading 時）
  - リコンシリエーション（再起動時の注文/ポジション同期）
  - リスク管理（最大ポジション比率、利用率、ドローダウン監視等）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス生存確認
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウンやポジション上限監視、ダッシュボード更新
  - KillSwitch / AlertManager: 条件で停止フラグを作成し LINE に通知
  - Streamlit ダッシュボード（監視用）
- Portfolio
  - 候補選定、等配分 / スコア配分、リスク調整（セクターキャップ・レジーム乗数）
  - 株数算定（単元切り捨て・aggregate cap のスケール調整）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算、IC 計算、統計サマリー
- AI
  - ニュースセンチメント（OpenAI）を使った銘柄スコアリング（ai.news_nlp）
  - 市場レジーム判定（ma200 + マクロニュースセンチメント合成）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提: Python 3.9+ を推奨します。

1. リポジトリをクローン／チェックアウトします。

2. 依存パッケージをインストールします（例）:
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai（AI 機能を使用する場合）
   - 例:
     ```
     pip install duckdb psutil requests streamlit openai
     ```
   実プロジェクトでは requirements.txt / Poetry を用意していると便利です。

3. 環境変数の設定:
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数は上書きされません。`.env.local` は強制上書き）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（少なくともプロダクション起動時に必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（デフォルト値や用途も併記）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - PID_FILE_PATH, KILL_FLAG_PATH 等（監視・制御ファイルのパス）
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト: 60）

   - 注意: Settings クラスは必須値が未設定だと ValueError を投げます。

4. データディレクトリ
   - `data/` ディレクトリに DB ファイルやフラグファイルが置かれます（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）。
   - 実行前に適宜ディレクトリを作成してください。

---

## 使い方・コマンド

### 1) 監視プロセスを起動する（Monitoring）
- デフォルトは本番の sqlite_path を利用（監視は環境にかかわらず本番 DB を参照する設計）。
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書きできます（秒）。
- 起動:
  ```
  python -m kabusys.run_monitoring
  ```
  または
  ```
  python src/kabusys/run_monitoring.py
  ```
- 終了方法:
  - 監視ループは Ctrl+C（KeyboardInterrupt）で停止できます。
  - 外部から停止させたい場合はプロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します（スクリプト内で参照しています）。

### 2) 実行エンジンを起動する（Execution）
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と完全に分離します。
- 起動:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  もしくは
  ```
  python src/kabusys/run_execution.py
  ```
- 実行中は `data/execution.pid` に PID が書かれます（設定で別パスに変更可）。
- 停止:
  - `data/stop_requested.flag` の作成で優雅に停止します。
  - KillSwitch（監視側）により `data/kill.flag` が書かれると Engine に停止シグナルが送られる設計です（設定に応じて）。

### 3) Streamlit ダッシュボード（監視）
- 起動:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- 監視 DB（読み取り専用）からダッシュボード表示します。

### 4) Paper Trading 検証レポート生成ツール
- コマンドライン:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- デフォルト DB パスは `data/paper_trading.db`。`--db` で明示的に指定可能。
- 出力は標準出力にレポートを表示します（稼働率、注文成功率、レイテンシ等の集計と PASS/FAIL 判定を行います）。

### 5) AI モジュール
- ニュース NLP（ai.news_nlp.score_news）と レジーム判定（ai.regime_detector.score_regime）は OpenAI API を使います。
- 環境変数 `OPENAI_API_KEY` を設定してください。プログラム引数で api_key を渡すことも可能です。
- AI 呼び出しはリトライやフェイルセーフ処理がありますが API キー未設定時は例外が上がります。

---

## 主要ファイル / ディレクトリ構成

（リポジトリの主要部分を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings: 環境変数の読み込み・検証・デフォルト管理
  - run_monitoring.py
  - run_execution.py
  - monitoring/
    - __init__.py
    - monitoring_db.py          — SQLite の監視ログ永続化層
    - system_monitor.py         — CPU/メモリ/ディスク、データ鮮度、PID チェック
    - trade_monitor.py          — 滞留注文・約定異常チェック
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag 書き込みユーティリティ
    - alert_manager.py          — LINE push 通知
    - monitoring_engine.py      — 各 Monitor を統括するループ
    - streamlit_dashboard.py    — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 broker_factory 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               — ニュースの LLM によるセンチメント解析
    - regime_detector.py        — ma200 + マクロニュース合成によるレジーム判定
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py       — プロセス優先度設定ユーティリティ

data/ ディレクトリ（実行時に利用）
- data/monitoring.db
- data/paper_trading.db
- data/kabusys.duckdb
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag

---

## 注意点 / トラブルシューティング

- 環境変数未設定による起動失敗
  - Settings クラスの _require() は未設定時に ValueError を投げます。必要なキーを .env などに設定してください。
- MONITOR_POLL_INTERVAL
  - 監視ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で指定可能。1 未満や負の値は無効と判断されデフォルト 60 秒にフォールバックします。
- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading のとき、Execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。監視（Monitoring）は環境にかかわらず本番 sqlite_path を参照する設計です（監視は常に本番を観測する想定）。
- OpenAI / ネットワークエラー
  - AI 呼び出しは一定回数リトライするロジックを持ちますが、API キー未設定・恒常的失敗時は処理がスキップまたはフォールバック（ゼロ・空）して継続します。ログを確認してください。
- プロセス優先度設定
  - 起動時に set_process_priority("high") を呼び出します。psutil の権限不足で設定できない場合は警告ログが出ますが、処理自体は継続します。
- ストリームリットで DB を開く際の読み取り専用
  - Streamlit は DB を読み取り専用で開くことを想定しており、URI を使った read-only 接続を行います。DB が存在しない場合はエラー表示されます。

---

## サンプル .env（例）

```
# 基本
KABUSYS_ENV=development
LOG_LEVEL=INFO

# API キー
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...

# DB パス（必要に応じて上書き）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# LINE 通知
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# その他
MONITOR_POLL_INTERVAL=60
PAPER_FILL_MODE=instant
```

---

## 開発者向けメモ

- データ更新やファクター計算では DuckDB を利用します。prices_daily / raw_financials / raw_news 等のテーブル構成に依存する処理が多いです。
- モジュールは可能な限り副作用を避ける（例えば日付の参照を直接しない）設計になっています。ユニットテストは日時を注入して行うことを推奨します。
- OpenAI 呼び出し部分はテスト用に _call_openai_api を patch/モックできるよう設計されています。

---

不明点や特定の起動手順（例: Docker / systemd でのサービス化、CI 設定など）についてもっと詳しく知りたい場合は、どの環境で使う予定かを教えてください。README をその用途向けに拡張します。
# KabuSys

日本株自動売買システムの一部を抜粋したコードベースの README。  
本ドキュメントはリポジトリ内のエントリポイント・ユーティリティ・主要モジュールの使い方／設定方法をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。本リポジトリには以下の主要機能を含みます：

- 実行エンジン（ExecutionEngine）による発注フロー（実取引 / ペーパートレード切替）
- 監視（Monitoring）コンポーネント：システム状態、注文滞留、リスク（ドローダウン等）の継続監視とアラート／Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算、特徴量解析、IC計算）
- AI（OpenAI）を使ったニュースセンチメント評価・レジーム判定
- 各種 CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針として、データ処理（DuckDB）と監視（SQLite）を分離しており、ペーパートレード時は本番 DB と分離して安全に検証できます。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV により実際のブローカーか Mock（paper_trading）を自動で選択。
  - ペーパートレードでは専用 SQLite（デフォルト: data/paper_trading.db）を使用。
  - 停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動。監視結果は監視用 SQLite に記録（monitoring は常に本番 sqlite_path を参照）。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。

- monitoring パッケージ
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager 等
  - 監視ログ保存用の monitoring_db（SQLite）を提供（テーブル作成・マイグレーションを含む）

- portfolio パッケージ
  - 銘柄候補選定、等比率／スコア加重配分、セクターキャップ、レジーム乗数、ポジションサイズ計算

- research パッケージ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- ai パッケージ
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores テーブルへ書込む
  - regime_detector: ETF の MA とマクロニュースセンチメントを合成して日次レジーム判定し market_regime テーブルへ書込む

- tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定付きレポートを生成

- config_setup.py / validate_config.py
  - .env 作成ウィザード、設定検証 CLI

---

## 前提・依存パッケージ（例）

- Python 3.10 以上（型ヒントの | 記法、型注釈を想定）
- 必須（最低限）:
  - duckdb
  - psutil
- AI 関連（OpenAI を使う場合）:
  - openai（または openai-sdk v1 に対応するパッケージ）
- 設定ファイル YAML 検証（任意）:
  - PyYAML

インストール例（プロジェクトに requirements.txt がある場合はそちらを利用）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

SQLite は標準ライブラリに含まれます。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd repo

2. 仮想環境の作成と依存インストール
   - 上記のように venv を作成し、必要なパッケージをインストールしてください。

3. .env の作成
   - 対話ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成し、機密値はマスクして入力できます。
   - 自動読み込み
     - リポジトリルートに .env / .env.local があれば自動で読み込まれます（ただし OS 環境変数が優先）。
     - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定の検証
   - .env や config/*.yaml の基本検証を行う:
     ```
     python -m kabusys.validate_config
     ```
     警告をエラー扱いにしたい場合は `--strict` を付与します。

5. データベース初期化
   - 監視用 SQLite（デフォルト: data/monitoring.db）は起動時にテーブルが自動作成されます（init_monitoring_db）。
   - DuckDB（デフォルト: data/kabusys.duckdb）は別途データ投入が必要です（prices_daily / raw_financials / raw_news などのテーブルは想定される）。


---

## 環境変数（主要なもの）

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - live: 実際のブローカーを使う（注意して設定を行う）

- API / 認証
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)

- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用

- ログ等
  - LOG_LEVEL (DEBUG/INFO/...)

- Kill / PID
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0 or 1) — 本番では 0 推奨

- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）。デフォルト 60。
    - 0 以下や不正値はデフォルトにフォールバック。

- OpenAI
  - OPENAI_API_KEY — AI モジュール（news_nlp / regime_detector）で使用

---

## 使い方（代表的なコマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV によって振る舞いが変わります（paper_trading なら MockBroker）。
  - 実行中に data/stop_requested.flag が置かれると安全に停止します。
  - PID ファイルを data/execution.pid に書きます（設定で変更可）。

- 監視ループ起動（SystemMonitor 単体）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書きできます。
  - 監視は常に本番 sqlite_path を使用します（monitoring ログは production DB を参照）。

- Paper Trading レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db path/to/paper_trading.db
  ```

- AI モジュール（例: ニューススコアリング、外部呼び出し）
  - OPENAI_API_KEY を環境変数で設定し、モジュール関数を呼ぶことで処理します。
  - 例（スクリプト内呼び出し）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="sk-...")

---

## 停止・Kill Switch の挙動

- 停止フラグ:
  - data/stop_requested.flag：run_execution / run_monitoring で監視され、存在するとループは終了します。
  - data/kill.flag：KillSwitch が書き込みを行い、ExecutionEngine の停止トリガーとして機能します。KillSwitch は冪等に動作し、既存の flag がある場合は再書き込みしません。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が `1` の場合、kill.flag を自動でクリアする設定があります（本番では `0` 推奨）。

---

## DB（DuckDB / SQLite）について

- DuckDB は市場データ・ニュース・ファイナンシャル等の分析用 DB（prices_daily / raw_financials / raw_news / market_regime / ai_scores などのテーブルを想定）。
- SQLite（monitoring.db / paper_trading.db）は監視ログ・発注ログ・ポジション・ダッシュボード等の永続化に使用。
- ペーパートレードは paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使い、本番 sqlite_path とは分離されます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル/フォルダ構成（抜粋）:

```
src/kabusys/
├── __init__.py
├── config.py
├── config_setup.py
├── validate_config.py
├── run_execution.py
├── run_monitoring.py
├── utils/
│   ├── __init__.py
│   └── process_priority.py
├── monitoring/
│   ├── monitoring_db.py
│   ├── system_monitor.py
│   ├── trade_monitor.py
│   ├── risk_monitor.py
│   ├── kill_switch.py
│   ├── monitoring_engine.py
│   └── alert_manager.py   # 実装ファイルあり（省略）
├── execution/
│   ├── execution_engine.py
│   ├── order_manager.py
│   ├── order_repository.py
│   ├── reconciler.py
│   ├── broker_factory.py
│   └── ...
├── portfolio/
│   ├── __init__.py
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py
│   └── regime_detector.py
├── tools/
│   ├── __init__.py
│   └── paper_verification_report.py
└── data/                # 実行時に使用されるファイル例:
    ├── kill.flag
    ├── stop_requested.flag
    ├── execution.pid
    ├── monitoring.db
    ├── paper_trading.db
    └── kabusys.duckdb
```

---

## 開発メモ / 注意点

- .env を絶対にリポジトリへコミットしないでください（秘匿情報が含まれます）。
- 本番（KABUSYS_ENV=live）で起動する際は LINE 通知や kill flag 設定等を十分に確認してください（validate_config で注意表示があります）。
- AI（OpenAI）を使う処理は API の失敗に対してフェイルセーフに設計されていますが、API キー管理やリクエスト量には注意してください（レート制限対策あり）。
- DuckDB のテーブル構成・データ投入は別途スクリプトで準備する必要があります（prices_daily / raw_financials / raw_news など）。
- process priority / CPU affinity の設定は psutil に依存し、権限が不足すると警告が出ます（無視して継続します）。

---

この README はコードベースからの導出ドキュメントです。実行環境や追加スクリプトはプロジェクトのルート README / docs や運用手順に従ってください。必要であれば、各モジュール（ExecutionEngine、AlertManager、BrokerClient 等）の詳細ドキュメントも作成できます。必要な箇所を指定してください。
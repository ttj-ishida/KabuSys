# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、アルゴリズム売買のための以下機能群を提供します：データパイプライン、ファクター計算、ポートフォリオ構築、ポジションサイズ計算、実行エンジン（ExecutionEngine）、監視（Monitoring）、および AI を使ったニュース / レジーム解析補助。  
README はプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめたものです。

注意: 本 README はソースコード（src/kabusys 以下）を元に作成しています。実行には Python ランタイムといくつかの外部ライブラリが必要です。

---

## プロジェクト概要

- 目的: 日本株の自動売買（実際の発注 / ペーパートレード両対応）に必要なロジックをモジュール化して提供する。
- 構成: データ処理（DuckDB）、監視用 DB（SQLite）、ExecutionEngine（発注・リスク管理）、監視エージェント（System / Trade / Risk）、AI ベースのニュース評価 / レジーム判定、研究用ファクター計算モジュールなど。
- 環境管理: .env ファイルまたは環境変数で設定。`.env` を対話的に作るヘルパーが用意されています。

---

## 主な機能一覧

- 環境設定
  - .env 自動読み込み（.env / .env.local、OS 環境変数を優先）
  - 対話式ウィザード: `kabusys.config_setup`（.env 作成支援）
  - 設定検証ツール: `kabusys.validate_config`

- 実行エンジン
  - ExecutionEngine（発注 / 注文管理 / リコンシリエーション / リスク制御）
  - paper_trading モードでは MockBrokerClient を使い、paper_trading 専用 SQLite に記録して本番 DB と分離

- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / Execution プロセス状態の定期チェック
  - TradeMonitor：注文遅延や約定異常の検出（trade_logs テーブル）
  - RiskMonitor：ドローダウン・ポジション数の監視、kill.flag の生成
  - MonitoringEngine：上記をまとめてポーリング・アラート発報

- ポートフォリオ構築（純関数）
  - 候補選定、等金額・スコア加重、ポジションサイズ計算、セクター制約、レジーム乗数

- 研究用（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン・IC 計算、統計サマリー

- AI（OpenAI）連携
  - ニュースのセンチメント評価（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI API の利用により取得したスコアは DuckDB に書き込む

- ユーティリティ
  - ロギング設定（console + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - Paper Trading の検証レポート生成スクリプト

---

## 必要要件（想定）

最低限の Python パッケージ（例）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定検証で YAML 内容を検証する場合に必要）

インストール例（pip）:
```bash
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 展開する
2. Python と必要パッケージをインストールする（上記参照）
3. 環境変数設定（.env）を作成する
   - 推奨: 対話式ウィザードで作成
     ```bash
     python -m kabusys.config_setup
     ```
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（PAPER 用デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - PAPER_FILL_MODE（paper_trading 時のモック約定挙動: instant | partial | never | reject）

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする strict モード:
   python -m kabusys.validate_config --strict
   ```

5. データベース初期化
   - Execution / Monitoring 起動時に必要なテーブルは自動作成されます（init_monitoring_db が呼ばれます）。

---

## 使い方（基本コマンド）

- ExecutionEngine（売買実行）を起動
  - 通常:
    ```bash
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、紙上取引用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 実行中は `data/execution.pid` に PID を書きます。停止は `data/stop_requested.flag` を作成するか、kill.flag を利用する運用フローに従って下さい。

- Monitoring（ポーリング監視）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用します（監視用 DB は共通）
  - 停止: `data/stop_requested.flag` を作成するとループが検知して終了します

- .env ウィザード（再掲）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（再掲）
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（例: ニュース評価・レジーム判定）
  - これらはライブラリ関数として呼び出す API を提供します（OpenAI API キー必須）。
  - 例: Python スクリプト内から
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 1), api_key="sk-...")
    ```
  - OpenAI 関連は API レート制限や 5xx を考慮したリトライ実装がありますが、API キーの設定は必須です。

---

## 運用に関するポイント / ファイル

- デフォルトの DB / パス
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db
  - PID ファイル: data/execution.pid
  - stop フラグ: data/stop_requested.flag
  - kill flag: data/kill.flag

- Kill Switch / 停止フロー
  - RiskMonitor / KillSwitch により、ドローダウンやポジション上限違反が検出されると `data/kill.flag` が書かれ、ExecutionEngine 停止のトリガーにできます。
  - ExecutionEngine / Monitoring はループ中に `data/stop_requested.flag` を検知して安全に停止します。

- ログ
  - 標準: console (stdout) と 日次ローテートファイル（logs/<app_name>.log）
  - ログレベルは環境変数 LOG_LEVEL（または setup_logging の引数）で調整

---

## よく使う環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — execution 環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0。本番では 0 推奨）

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールのツリー（src/kabusys 以下）です。実際のリポジトリにはさらに多くのファイルがある場合があります。

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
│   ├── logging_setup.py
│   └── process_priority.py
├── monitoring/
│   ├── monitoring_db.py
│   ├── monitoring_engine.py
│   ├── system_monitor.py
│   ├── trade_monitor.py
│   ├── risk_monitor.py
│   ├── kill_switch.py
│   └── alert_manager.py
├── execution/
│   ├── execution_engine.py
│   ├── order_manager.py
│   ├── order_repository.py
│   ├── reconciler.py
│   └── broker_factory.py
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
└── monitoring/
    └── ... (上に記載の各モジュール)
```

---

## 開発 / デバッグのヒント

- テストや開発時に環境変数の自動読み込みを無効にする:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- Monitoring の1回実行をテストする場合は MonitoringEngine を直接インスタンス化して `run_once()` を呼ぶことで単発のチェックができます（ユニットテスト向け）。
- DuckDB / SQLite のパスが指しているファイルの親ディレクトリが存在しない場合、validate_config は警告を出します。起動時に自動作成されるケースもありますが、手動で作成しておくと安全です。
- OpenAI 系は API レスポンスの不安定さを考慮してリトライ実装がありますが、API キー・レート制限・料金に注意してください。

---

## ライセンス / 著作権

（この README ではライセンス情報は含めていません。プロジェクトに LICENSE ファイルがある場合はそちらを参照してください。）

---

何か追加したい項目（例: 具体的な .env.example、動作フロー図、運用手順書）があれば教えてください。README をそれに合わせて拡張します。
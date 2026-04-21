# KabuSys

日本株向け自動売買システムのコードベース。シグナル生成・ポートフォリオ構築・発注（実運用 / ペーパートレード）・監視・研究ツール群を含みます。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた自動売買プラットフォームのコンポーネント群です。

- 戦略（ファクター計算 / 特徴量解析）によるシグナル生成（research）
- ポートフォリオ構築（候補選定・配分、リスク調整、株数決定）
- 発注エンジン（ExecutionEngine） — 本番 / ペーパートレード対応
- 監視（システム・注文・リスク監視）と Kill Switch
- AI モジュール（ニュース NLP による銘柄センチメント評価、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）
- ロギング / 優先度設定などのユーティリティ

設計方針の一部：
- DuckDB/SQLite を使ったデータ管理（分析用 DuckDB、監視/注文ログ用 SQLite）
- 本番データへのルックアヘッドを防ぐ（日時参照を直接用いない箇所など）
- フェイルセーフを重視（API失敗時はフォールバック、ログ出力）

---

## 主な機能一覧

- config
  - 環境変数 / .env ロードと Settings オブジェクト（KABUSYS_ENV, DB パス等）
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- execution
  - ExecutionEngine（発注ロジック、RiskManager、OrderManager 等）
  - BrokerClientFactory により本番/モック（paper_trading）を切替
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor とそれらを束ねる MonitoringEngine
  - MonitoringDB: SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch: 条件により data/kill.flag を作成して Execution を停止
- portfolio
  - 候補選定、配分（等金額 / スコア加重）、株数決定（単元丸め・リスクベース）
  - セクターキャップ、レジーム乗数適用ロジック
- research
  - ファクター算出（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC / 統計サマリ等
- ai
  - news_nlp: OpenAI を用いたニュースセンチメント（ai_scores へ格納）
  - regime_detector: MA + マクロニュースで市場レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## 必要条件（概略）

推奨: Python 3.10+

主要依存ライブラリ（プロジェクト内の使用箇所から抜粋）:
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証用。任意）
- （その他：標準ライブラリ）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（実際には requirements.txt を用意していればそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     これで .env が生成されます（機密情報はマスクされます）。.env は絶対に Git にコミットしないでください。
   - 必須環境変数
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定する（news_nlp / regime_detector）
4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```
5. データディレクトリの作成（必要に応じて）
   - デフォルトでは `data/` に SQLite / pid / flag ファイルが置かれます。ログは `logs/`（LOG_DIR で変更可）。

---

## 使い方

主要な起動スクリプト（モジュールとして実行）:

- ExecutionEngine（発注エンジン）起動
  - 本番 / ペーパートレードは KABUSYS_ENV により切替
    - development / paper_trading / live
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、デフォルトで `data/paper_trading.db` を使用して本番 DB と完全分離します。
    - 起動時に `data/stop_requested.flag` が存在すると起動を中止します。
    - 実行中は `data/execution.pid` に PID を書きます。
    - stop は monitoring の KillSwitch により `data/kill.flag` が書き込まれる、または `data/stop_requested.flag` により検出されます。

- Monitoring（監視ループ）起動
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。1 未満や不正な値はデフォルトにフォールバック。
  - 動作:
    - process priority を "high" に設定（可能な場合）
    - monitoring 用に SQLite（settings.sqlite_path）と DuckDB（settings.duckdb_path）へ接続
    - SystemMonitor.check_once() をポーリングで呼び出す
    - `data/stop_requested.flag` を見つけるとループを終了

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`。`--db` で指定可能。

環境変数（代表的なもの）
- KABUSYS_ENV: development | paper_trading | live
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: 分析用 DB（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード Mock の約定挙動（instant | partial | never | reject）
- LOG_LEVEL / LOG_DIR: ログ設定
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

停止 / Kill
- KillSwitch により条件を満たすと `data/kill.flag` が書かれ、ExecutionEngine はそれを検出して停止します。
- `data/stop_requested.flag` を作成すると run_monitoring / run_execution が外部的に検知して停止します。
- `KILL_FLAG_CLEAR_ON_START=1` を .env に設定すると起動時に kill.flag を自動でクリアします（本番では推奨しない）。

ログ
- 共通の logging セットアップ: `kabusys.utils.logging_setup.setup_logging(app_name="...")`
- ログは stdout と `logs/<app_name>.log`（日次ローテーション、30 日保持）に出力されます。ログディレクトリは `LOG_DIR` または引数で変更可能。

---

## ディレクトリ構成（抜粋）

以下は主なファイル / モジュールの一覧（src/kabusys 以下）。実際のリポジトリではさらに多くのファイルが存在する可能性があります。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings、.env 自動ロードロジック
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID / stop flag 管理）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ（テーブル作成・CRUD ヘルパ）
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag 書込みロジック
    - monitoring_engine.py — 各 Monitor を束ねる
    - (trade_monitor.py, alert_manager.py 等、プロジェクトにより存在)
  - execution/
    - execution_engine.py — 発注エンジン（EngineConfig 等）
    - broker_factory.py — Broker クライアント生成（本番 / ペーパートレード）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py etc.
  - portfolio/
    - portfolio_builder.py — 候補選定・スコア順ソート
    - position_sizing.py — 株数計算・スケール調整・単元丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — OpenAI を使ったニュース NLP（ai_scores への書込）
    - regime_detector.py — MA + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 開発 / デバッグのヒント

- .env の自動ロードはデフォルトで有効（config.py）。テスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の接続は research / ai / regime 等で直接受け取る実装（SQL を使った計算）。テスト時はモック接続を渡せます。
- OpenAI 呼び出しは API エラー（429、タイムアウト、5xx 等）に対して指数バックオフでリトライする設計。ただし API キーは必須です。
- ログディレクトリの権限や作成に失敗した場合はコンソール出力のみで継続する仕組みです。

---

## よく使うコマンド（まとめ）

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- Execution 起動
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に追記する詳細（設定ファイルのサンプル .env.example、各コンポーネントの API 仕様、DB スキーマの詳細、デプロイ手順など）を作成します。どの情報を追加しますか？
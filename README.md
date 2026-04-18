# KabuSys

日本株自動売買システム KabuSys の README（日本語）

このリポジトリは、戦略リサーチ、ポートフォリオ構築、実行エンジン、監視、AI ニューススコアリングなどを含む自動売買システムのコードベースです。本 README はプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークで、主に以下の機能を提供します。

- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- ポートフォリオ構築（候補抽出・重み計算・株数決定）
- 実行エンジン（broker 抽象、ペーパートレード切替、リスク制御）
- 監視（システム状態・注文状況・リスク監視、Kill Switch）
- AI ベースのニュースセンチメント（OpenAI を用いた銘柄・マクロのスコアリング）
- 各種ユーティリティ（設定ウィザード・設定検証・ログ設定等）
- ペーパートレード検証レポート生成ツール

設計上、DB（DuckDB / SQLite）や外部 API（kabuステーション / J-Quants / OpenAI）との連携を想定し、環境に応じて実際発注するかペーパートレードに切り替えられます。

---

## 主な機能一覧

- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索、IC 計算、統計サマリ
- portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額・スコア加重）
  - ポジションサイズ計算（リスクベース・等配分等）
  - セクター制限・レジーム乗数
- execution
  - ExecutionEngine（実行スレッド、broker 抽象）
  - Paper trading サポート（KABUSYS_ENV=paper_trading で MockBroker）
  - RiskManager / OrderManager / Reconciler
- monitoring
  - SystemMonitor（CPU/メモリ/ディスク/データ鮮度/プロセス監視）
  - TradeMonitor（滞留注文・約定異常チェック）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（stop フラグ生成）
  - MonitoringEngine（総合ポーリング + アラート連携）
  - monitoring DB 層（SQLite スキーマ + 永続化ユーティリティ）
- ai
  - news_nlp: ニュースを LLM（OpenAI）でセンチメント分析し ai_scores に保存
  - regime_detector: ETF MA とマクロニュースで日次レジーム判定
- utils
  - logging_setup: stdout + 日次ローテートファイルログの統一設定
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- tools
  - paper_verification_report: ペーパートレードの検証レポート生成

---

## 前提 / 必要パッケージ

推奨 Python バージョン: 3.9+

主な依存パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- その他：標準ライブラリ

インストール例（仮）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

（実際の requirements.txt がある場合はそちらを使用してください。）

---

## 環境設定 (.env)

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みはデフォルトで有効ですが、テスト等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

優先順位:
1. OS 環境変数
2. .env.local
3. .env

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合に必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR（ログ出力先、デフォルト: logs/）
- PAPER_FILL_MODE（ペーパートレードでの成行充足挙動: instant|partial|never|reject）

.env の初期作成はウィザードを使うと便利です（下記参照）。

---

## セットアップ手順（推奨の流れ）

1. レポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成して依存をインストール
3. .env を設定
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```bash
     python -m kabusys.validate_config
     ```
     strict モードで警告も失敗扱いに:
     ```bash
     python -m kabusys.validate_config --strict
     ```
4. 必要ならデータベース（DuckDB / SQLite）ファイルの配置や初期データ投入
5. ログディレクトリは通常自動作成されます（`logs/`）。問題がある場合は `LOG_DIR` を設定してディレクトリを作成してください。
6. OpenAI を使う場合は `OPENAI_API_KEY` を設定

注意:
- `.env` は決してリポジトリにコミットしないでください（config_setup も README に記載あり）。
- 起動時に Kill Flag を自動的にクリアするかどうかは `KILL_FLAG_CLEAR_ON_START` で制御します（本番では `0` を推奨）。

---

## 使い方（起動と主要コマンド）

すべてモジュール実行形式で提供されています。パッケージを PYTHONPATH に置いて次のように起動します。

- 実行エンジン（ExecutionEngine）を起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV で切替
  - ペーパートレード時は専用 DB（data/paper_trading.db）を使用
  ```bash
  python -m kabusys.run_execution
  ```

- 監視ループ（SystemMonitor のポーリング）を起動
  - ポーリング間隔を秒で上書き（デフォルト 60 秒）
  ```bash
  # デフォルト（60秒）
  python -m kabusys.run_monitoring

  # 間隔を 30 秒に変更
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 環境設定ウィザード（.env 生成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（.env / config/*.yaml のチェック）
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成ツール
  ```bash
  # 全期間（DB がある場合）
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パスを明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI（ニューススコア・レジーム判定）
  - 実行サンプルは ai モジュール内の関数を呼び出して使用します。
  - OpenAI API を利用するため `OPENAI_API_KEY` を設定してください（引数経由でも可）。
  - 例（Python スクリプト / REPL で）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

プロセス停止・再起動:
- 監視・実行ともに「停止フラグ」ファイルを検出すると安全にループ/エンジンを終了する仕組みがあります。
  - プロジェクトルートの data/stop_requested.flag（run_monitoring, run_execution がチェック）
  - Kill Switch は data/kill.flag を書き込み実行エンジンに停止シグナルを送ります。
- PID ファイル:
  - ExecutionEngine はデフォルトで `data/execution.pid` を使用します（Settings.pid_file_path）。

---

## ログ

ログは以下の仕組みで出力されます（utils/logging_setup.py）。

- stdout に StreamHandler（標準出力）
- 日次ローテートファイル: logs/<app_name>.log（TimedRotatingFileHandler、30日分保持）
- ログレベルは環境変数 `LOG_LEVEL`、`LOG_DIR` で制御可能

例:
```bash
LOG_LEVEL=DEBUG LOG_DIR=logs python -m kabusys.run_execution
```

---

## 重要な挙動メモ

- Settings（kabusys.config）:
  - .env/.env.local の自動読み込みを行い、OS 環境変数を保護します。
  - `Settings` クラス経由で各種設定値・パスを取得できます。
- Monitoring は環境（KABUSYS_ENV）にかかわらず監視用の production sqlite_path（設定で指定された sqlite_path）を使用する設計になっています。
- Execution は `KABUSYS_ENV=paper_trading` の場合、MockBroker を使い paper_trading 用 sqlite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
- OpenAI 呼び出しはリトライロジックと安全なフォールバック（失敗時にゼロスコア等）を備えています。API キーの管理は厳重に行ってください。

---

## ディレクトリ構成（主要ファイルの概要）

以下は src/kabusys 以下の主要構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度設定ユーティリティ
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ / 永続化層
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      —（注文監視ロジック）
    - risk_monitor.py       — ドローダウン・ポジション監視
    - monitoring_engine.py  — 各 Monitor を束ねるループ
    - kill_switch.py        — Kill Switch（flag 書込）
    - alert_manager.py      —（通知管理）
  - execution/
    - execution_engine.py   — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py    — ファクター計算
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py           — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py

（上記は代表的ファイルのみを抜粋しています。詳細はソースを参照してください。）

---

## よくある運用ワークフロー例

- 開発環境立ち上げ:
  1. .env を作成（config_setup）
  2. validate_config でチェック
  3. DuckDB / SQLite にテストデータを投入（あるいはテスト用のデータファイルを配置）
  4. python -m kabusys.run_execution（単発実行）または適宜スケジューラで起動
  5. python -m kabusys.run_monitoring を並列で起動し、監視・Kill Switch を有効にする

- ペーパートレード検証:
  1. KABUSYS_ENV=paper_trading を設定
  2. run_execution を起動 → data/paper_trading.db に記録
  3. 本番条件に近い負荷で動作させ、tools/paper_verification_report で評価

---

## トラブルシューティング / 注意点

- .env のプレースホルダ値（例: your_value）をそのままにしていないか validate_config で確認してください。
- OpenAI の呼び出しは API 制限やエラーが発生するため、キーの利用量やリトライ動作を監視してください。
- ログディレクトリ作成に失敗するとファイル出力が無効化されますが、標準出力にはログが流れます（utils/logging_setup の挙動）。
- 実運用（KABUSYS_ENV=live）では Kill Switch の設定（KILL_FLAG_CLEAR_ON_START など）に注意してください。自動クリアは危険です。

---

もし README に加えたい具体的なコマンド例や、deploy 用の systemd / docker のテンプレートなどのサンプルがあれば教えてください。必要に応じて追記します。
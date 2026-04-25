# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README（日本語）。

この README は、提供されたコードベースに基づき、プロジェクト概要、機能、セットアップ手順、使い方、およびディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（研究・ペーパートレード・本番運用を想定）です。  
主なコンポーネントは以下です。

- ExecutionEngine：発注・注文管理・リスク管理・約定のリコンサイルなどを担う（本番 / ペーパートレード対応）。
- Monitoring：システム状態、取引状況、リスク（水準・ドローダウン等）を定期監視し、アラート／Kill Switch を発動。
- Research：ファクター計算や特徴量探索などの研究用モジュール（DuckDB を用いる）。
- AI：ニュースの NLP によるセンチメント評価や市場レジーム判定（OpenAI API を利用）。
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度設定、各種ツール。

設計上、多くのモジュールは DB に直接アクセスする実装（DuckDB / SQLite）や純粋関数（ポートフォリオ構築・リスク調整）を組み合わせており、ペーパートレード用 DB と本番用 DB は分離されています。

---

## 機能一覧

- 環境設定ウィザード（.env の対話的作成/更新）
- 設定検証 CLI（環境変数・config/*.yaml のチェック）
- ExecutionEngine の起動（本番 / paper_trading 切替）
- Monitoring ポーリングループ（プロセス監視・データ鮮度・リスク監視）
- Kill Switch（フラグファイルにより ExecutionEngine を停止）
- 監視ログ永続化（SQLite ベース、テーブル: system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数）
- Research（ファクター計算：Momentum/Value/Volatility、将来リターン、IC 計算、統計サマリ）
- AI モジュール（ニュース NLP スコアリング、レジーム検出。OpenAI API 使用）
- ツール：Paper Trading 検証レポート生成スクリプト

---

## 要件（目安）

- Python 3.10+
- 推奨パッケージ（抜粋）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証に任意で使用）
- SQLite（標準ライブラリで利用）
- （開発）pip, virtualenv 等

（requirements.txt はリポジトリに付属していない想定のため、上記パッケージをインストールしてください。）

例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
# あるいは pip install -e . を用いるパッケージ化されている場合
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成・有効化（推奨）
3. 必要な Python パッケージをインストール（上記参照）
4. .env の作成（対話式ウィザード推奨）
   - 実行:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいはプロジェクトルートに `.env` を直接作成
   - 自動ロード: `kabusys.config` はプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルトあり）:
- KABUSYS_ENV: 実行環境。`development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` の場合、ExecutionEngine は MockBrokerClient を使用し、Paper Trading 用 DB に記録します。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- OPENAI_API_KEY: AI 機能（ニュース NLP / レジーム判定）を使う場合に必要
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）。デフォルト 60 秒（`run_monitoring.py` で参照）

Kill / Stop フラグ（ファイル）:
- data/kill.flag — Kill Switch（Monitoring により書き込まれると ExecutionEngine に停止シグナル）
- data/stop_requested.flag — Monitoring / Execution の起動スクリプトでポーリングループを終了するための外部停止フラグ

その他の閾値等は .env / config ファイルや Settings クラスで取得できます。

---

## 使い方

CLI ベースで実行可能なモジュール（python -m を推奨）:

- 環境設定ウィザード（.env 生成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動
  - 通常（本番/開発）:
    ```bash
    python -m kabusys.run_execution
    ```
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード専用 DB（`PAPER_TRADING_SQLITE_PATH`）を使用し、MockBrokerClient が利用されます。
    - 起動時に `data/stop_requested.flag` が存在する場合は起動を行いません。
    - ExecutionEngine は PID を `data/execution.pid` に書き込みます（設定により変更可）。

- Monitoring 起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには環境変数 `MONITOR_POLL_INTERVAL` を秒で指定（例: `MONITOR_POLL_INTERVAL=30`）。
  - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使用します。
  - 停止は `data/stop_requested.flag` を作成することで行います（ループが検知して終了します）。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` を指定できます（デフォルト: `data/paper_trading.db`）。

- AI 機能（プログラムから呼び出す）
  - ニュース NLP スコアリング:
    ```python
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: duckdb.connect(...)
    score_news(duckdb_conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```
  - 両機能とも OpenAI API キーが必要（引数 or 環境変数 `OPENAI_API_KEY`）。API の呼び出しはリトライやフェイルセーフ（失敗時のフォールバック値）を実装しています。

ログ設定:
- すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging` を使ってログを統一設定します。
- デフォルトログディレクトリ: `logs/`。各アプリは `logs/<app_name>.log` に日次ローテーションでログを書きます（30日保持）。

停止・Kill フローの概要:
- Monitoring の RiskMonitor がしきい値超過を検出すると `KillSwitch` が `data/kill.flag` を書き込みます。
- ExecutionEngine は起動時やポーリング中に `kill.flag` を確認し、存在すれば安全に停止するよう設計されています。
- 外部からの終了（開発用）には `data/stop_requested.flag` を置くことで Monitoring/Execution のループを終了できます。

---

## ディレクトリ構成

以下は主要なファイル・ディレクトリの抜粋（提供コードに基づく）。

```
src/
└── kabusys/
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
    │   ├── system_monitor.py
    │   ├── trade_monitor.py        # ※実装ファイルは省略されている可能性があります
    │   ├── risk_monitor.py
    │   ├── kill_switch.py
    │   ├── monitoring_engine.py
    │   └── alert_manager.py        # ※実装ファイルは省略されている可能性があります
    ├── execution/
    │   ├── execution_engine.py     # 実行エンジン本体
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
    ├── monitoring/                   # 上述の monitoring サブモジュール
    ├── tools/
    │   ├── __init__.py
    │   └── paper_verification_report.py
    └── data/                         # 実行時に作成される想定ファイル
        ├── monitoring.db (SQLITE_PATH)
        ├── paper_trading.db (PAPER_TRADING_SQLITE_PATH)
        ├── kabusys.duckdb (DUCKDB_PATH)
        ├── kill.flag
        ├── stop_requested.flag
        └── execution.pid
```

（実際のリポジトリにはさらに細かいモジュールやスクリプト、config ディレクトリ等が存在する想定です。）

---

## 追加の技術ノート / 注意事項

- .env 自動読み込み
  - `kabusys.config` はリポジトリのプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動的に読み込みます（OS 環境変数が優先）。自動読み込みを止めるには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB の初期化
  - Monitoring 用 SQLite DB のスキーマ初期化は `monitoring_db.init_monitoring_db()` が行います。`run_monitoring` / `run_execution` 起動時に呼ばれ、テーブルとマイグレーション（不足カラムの追加）を行います。

- Paper Trading と本番の分離
  - `KABUSYS_ENV=paper_trading` のとき、Execution はペーパートレード専用 DB（`PAPER_TRADING_SQLITE_PATH`）を使用し、MockBrokerClient を用いて注文のシミュレーションを行います。これにより、本番 DB と発注 API への影響を分離します。

- OpenAI（AI）関連
  - AI モジュールは OpenAI を利用します。API キーが必要です（`OPENAI_API_KEY`）。API 呼び出しはリトライやエラーハンドリングが組み込まれていますが、API 利用料やレート制限に注意してください。

- ログ／権限
  - ロギングは `logs/` に書き出されるため、実行ユーザーに書き込み権限が必要です。プロセス優先度設定（`psutil` を利用）は OS 権限によっては失敗することがあります（警告ログが出ますが、処理は継続します）。

---

## よく使うコマンドまとめ

- 環境ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動:
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```bash
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README をプロジェクトの実ファイル構成や運用ルールに合わせて拡張してください。具体的な実装箇所（broker client、execution engine の細かい設定や alert_manager の実装など）に合わせて依存関係・運用手順を補足することを推奨します。
# KabuSys

日本株向け自動売買システムのライブラリ／実行スクリプト群です。本リポジトリはトレード実行エンジン、監視（Monitoring）、リスク管理、ポートフォリオ構築、リサーチ／ファクター計算、AI（ニュースNLP / レジーム判定）などの主要コンポーネントを含みます。

> バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を持つモジュール群です。

- 株式売買エンジン（ExecutionEngine）による発注管理とリスク制御
- システム稼働状態・発注ログ・リスクイベントの永続化（SQLite）
- 監視ループ（System / Trade / Risk Monitor）による自動アラートと Kill Switch
- ポートフォリオ構築ロジック（候補選定・重み付け・株数算出）
- リサーチ用ファクター計算（DuckDB を使用）
- AI を利用したニュースセンチメントや市場レジーム判定（OpenAI）
- ペーパートレード用の分離された DB（完全分離で検証可能）
- ユーティリティ: 設定ウィザード、設定検証、レポート生成など

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルート基準）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定の事前検証 CLI（kabusys.validate_config）
- 実行／監視
  - run_execution.py：ExecutionEngine 起動（本番 / paper_trading 切替あり）
  - run_monitoring.py：SystemMonitor ポーリングループ起動
  - Kill Switch（data/kill.flag）による外部からの停止シグナル
  - stop_requested.flag によるプロセス停止シグナルの検出
- データベース
  - DuckDB（分析用）と SQLite（監視・発注ログ）
  - monitoring_db モジュールでテーブル作成・マイグレーションを自動化
- ポートフォリオ
  - 候補選定、等金額／スコア重み付け、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数の適用ロジック
- リサーチ
  - Momentum / Value / Volatility ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ
- AI
  - ニュースセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（ma200 + マクロセンチメント）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 前提 / 必要要件

- Python 3.10+（型注釈や一部の記法を想定）
- 必要となるパッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（validate_config の YAML 検証用）
- SQLite は標準で利用可

requirements.txt はプロジェクトに含めている想定です。まずは仮想環境を作成してインストールしてください:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

（requirements.txt がない場合は上記の主要パッケージを個別にインストールしてください）

---

## セットアップ手順

1. プロジェクトルートで仮想環境を作成・有効化して依存をインストール
2. .env の作成
   - 対話式ウィザードを使う（推奨）:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参考に手動で作成
3. 設定の検証:
   ```bash
   python -m kabusys.validate_config      # 警告は許容
   python -m kabusys.validate_config --strict  # 警告を FAIL 扱い
   ```
4. 必要に応じてデータディレクトリを作成:
   - デフォルトの DB / ログ / pid / flag は `data/`、`logs/` を使用します。通常は自動作成されますがアクセス権等を事前に確認してください。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: 分析用 DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を利用するモジュールで必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番での LINE 通知 (任意)
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
- LOG_DIR: ログ出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定シミュレーション挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

注意: .env の自動ロードはプロジェクトルート（.git または pyproject.toml 基準）を探して行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 実行方法（使い方）

以下は主要なスクリプト／CLI の利用方法例です。

### 設定ウィザード（対話式）

```bash
python -m kabusys.config_setup
# .env を生成・更新します
```

### 設定検証

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

### ExecutionEngine（発注エンジン）起動

- 通常（本番 / development）:
  ```bash
  python -m kabusys.run_execution
  ```
- ペーパートレード:
  - 環境変数 `KABUSYS_ENV=paper_trading` を設定すると MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録します。
  - 例:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
- 停止方法:
  - `data/stop_requested.flag` を作成すると起動中のプロセスが検知して終了します。
  - Kill Switch（重大リスク検知時）は `data/kill.flag` を書き込み ExecutionEngine を停止させます（起動時に自動クリア設定の有無に注意）。

### Monitoring（監視）起動

```bash
python -m kabusys.run_monitoring
```

- ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）。
- 監視は monitoring DB（`SQLITE_PATH`）へログを書き込みます。Monitoring は環境にかかわらず本番 sqlite_path を使用します。
- 停止は `data/stop_requested.flag` を作成するか Ctrl+C。

### Paper Trading 検証レポート生成

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

### AI モジュール（プログラムから呼び出す）

- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

これらは直接 CLI 化されていないため、Python スクリプトや REPL から DuckDB 接続を作成して呼び出します。OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` から取得します。

---

## ログ / PID / フラグの場所（デフォルト）

- ログ: logs/<app_name>.log（app_name 例: execution, monitoring）
- PID: data/execution.pid（ExecutionEngine が利用）
- 停止フラグ: data/stop_requested.flag（プロセス停止に使用）
- Kill Switch フラグ: data/kill.flag（監視コンポーネントが書き込み）
- SQLite / DuckDB: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb

ログは StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート）で出力されます。

---

## 開発者向けノート

- 設計方針の一部
  - リサーチ / AI モジュールは実行系（発注）とは分離し、DuckDB と既存テーブルだけを参照するように設計されています（ルックアヘッドバイアス防止のため date 未満の条件等に注意）。
  - Paper Trading は本番 DB と完全に分離されるように `paper_sqlite_path` を使用します（KABUSYS_ENV=paper_trading）。
  - OpenAI 呼び出しはリトライ（指数バックオフ）やレスポンス検証を実装しており、API 失敗時はフォールバック（例: 0.0）で継続する設計です。
- テストのしやすさ
  - OpenAI 呼び出し部は `_call_openai_api` を差し替え可能にしてあるため、ユニットテストでモックしやすくなっています。
  - monitoring_db.init_monitoring_db は冪等でスキーママイグレーション処理を含みます。
- 注意点
  - .env は絶対にリポジトリにコミットしないでください（config_setup も同ドキュメントに注意書きがあります）。
  - 本番環境（KABUSYS_ENV=live）では Kill Switch まわりや LINE 通知設定を必ず確認してください。
  - process_priority と CPU affinity の設定は psutil を使用しており、プラットフォーム間差異を吸収する実装になっていますが、権限不足で設定できない場合は警告になるだけです。

---

## ディレクトリ構成（主要ファイル）

（src 以下を基準に表示）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数／設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル初期化 / CRUD）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム状態 / データ鮮度監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - trade_monitor.py        — （注文監視 — 実装ファイルあり）
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - alert_manager.py        — （通知管理 — 実装ファイルあり）
  - execution/
    - execution_engine.py     — ExecutionEngine 実装（発注ループ等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py       — ブローカークライアントの生成（Mock含む）
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（ma200 + macro sentiment）
  - data/                     — （運用時に生成される想定のディレクトリ）
    - *.db, *.pid, kill.flag, stop_requested.flag
  - logs/                     — デフォルトのログ出力先

---

## よくある運用フローの例

1. 開発環境での確認
   - .env を作成（config_setup）
   - python -m kabusys.validate_config
   - DuckDB / SQLite にテストデータをロード
   - python -m kabusys.run_monitoring を起動して監視の動作確認
2. ペーパートレード検証
   - KABUSYS_ENV=paper_trading を設定
   - python -m kabusys.run_execution を起動（MockBroker により data/paper_trading.db に記録）
   - トレード結果を集計： python -m kabusys.tools.paper_verification_report
3. 本番運用
   - KABUSYS_ENV=live、必要な API キー類と LINE 通知等を設定
   - 実行プロセスは systemd / supervisor / docker などで管理（PID / ログ / stop flag を使用）

---

## サポート / 追加情報

- README やドキュメントに記載のないモジュール（trade_monitor や alert_manager 等）はリポジトリ内の該当ファイルを参照してください。
- 本 README はコードベースから抽出した設計意図・運用手順を要約しています。詳細なパラメータや内部仕様は各モジュールの docstring を参照してください。

---

作業や導入で不明点があれば、どのコンポーネント（例: ExecutionEngine、AI スコアリング、監視）についてさらに詳しい手順やコマンド例が必要か教えてください。必要に応じて起動コマンドの systemd ユニット例や Dockerfile 例も提供できます。
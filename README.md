# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システム（KabuSys）のコア実装です。取引実行エンジン、監視機構、ポートフォリオ構築、リサーチ/ファクター計算、AIベースのニュースセンチメント評価などを含みます。本 README はコードベースの概要、セットアップ手順、利用方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成されます。

- ExecutionEngine：発注・注文管理・リスク管理・リコンシリエーション
- Monitoring：システム状態・注文ログ・リスクの定期チェックとアラート管理
- Portfolio：シグナルから銘柄選定・重み付け・株数決定までの純粋関数群
- Research：DuckDB上の価格/財務データを用いたファクター計算・特徴量解析
- AI：OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価 / レジーム判定
- Tools：ペーパートレードの検証レポート等のユーティリティスクリプト
- Utils：ログ設定、プロセス優先度設定、環境読み込み等のヘルパー

設計上の重要点：
- 本番監視は環境（KABUSYS_ENV）に依らず監視用 SQLite（デフォルト `data/monitoring.db`）を使用します。
- `paper_trading` 環境では MockBrokerClient を使用し、ペーパートレード用 DB（`data/paper_trading.db`）に完全分離して記録します。
- .env ベースの設定管理を採用し、`config_setup` による対話式ウィザードと `validate_config` による事前チェックを提供します。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートに `.env` / `.env.local` があればロード）
  - 対話式 .env ウィザード（`python -m kabusys.config_setup`）
  - 起動前検証 CLI（`python -m kabusys.validate_config`）

- 実行・発注
  - ExecutionEngine（リスク管理、OrderManager、Reconciler などを統合）
  - Paper trading モードでの完全分離（MockBrokerClient + `data/paper_trading.db`）

- 監視・Kill Switch
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - 異常検出で `data/kill.flag` を書き込む KillSwitch
  - `data/stop_requested.flag` による外部停止（起動ループが検知して終了）

- ポートフォリオ構築
  - 候補選定、等重/スコア重み、リスクベースのポジションサイズ計算
  - セクターキャップやレジーム乗数の適用

- リサーチ
  - Momentum/Volatility/Value ファクター、将来リターン、IC 計算、統計サマリー（DuckDB 前提）

- AI（OpenAI）
  - ニュース記事をまとめて LLM に投げ、銘柄ごとの sentiment を ai_scores に書き込む
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成（`python -m kabusys.tools.paper_verification_report`）

---

## 必要条件（依存関係）

最低限インストール推奨パッケージ（pyproject.toml等がある場合はそちらを利用）:

- Python 3.10+
- duckdb
- psutil
- openai（AI機能を使う場合）
- PyYAML（`validate_config` で YAML の検証を行う場合）
- （その他プロジェクト固有の依存があれば pyproject.toml を参照）

仮想環境を作成して依存を入れる例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動します。

2. 仮想環境を作成・有効化し、依存パッケージをインストールします（上記参照）。

3. .env ファイルを作成・編集
   - 対話式ウィザードを使う：
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（`.env.example` があれば参照）。

4. 設定の検証（推奨）:
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの準備（デフォルト）:
   - `data/` （SQLite / pid / flag 用）
   - `logs/` （ログ出力）

   これらはスクリプト実行時に自動作成されることが多いですが、権限等の都合で事前作成しておくと確実です。

---

## 環境変数（主なもの）

以下は主要な環境変数とデフォルト値のまとめです（詳細は `kabusys.config.Settings` を参照）。

- KABUSYS_ENV: 実行環境。`development` | `paper_trading` | `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合に必要）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）※ run_monitoring 用

注意:
- `.env.local` は `.env` より優先して読み込まれ、既存 OS 環境変数は保護されます。
- `KILL_FLAG_CLEAR_ON_START` は `1` にすると ExecutionEngine 起動時に `data/kill.flag` を自動クリアします（本番では `0` 推奨）。

---

## 実行方法（使い方）

スクリプトはモジュールとして実行できます（プロジェクトルートが PYTHONPATH に入っていることを前提）。

- ExecutionEngine を起動（デフォルト: 実行環境に応じて実 DB / paper_trading DB を選択）
  ```bash
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBroker が選択され、`PAPER_TRADING_SQLITE_PATH` に書き込みます。
  - 実行中に `data/stop_requested.flag` を作成すると安全に停止します。
  - ExecutionEngine の PID はデフォルト `data/execution.pid` に保存されます。

- Monitoring（ポーリングループ）を起動
  ```bash
  # ポーリング間隔を変更したい場合:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  # デフォルト:
  python -m kabusys.run_monitoring
  ```
  - モニタは Settings の sqlite_path（監視 DB）と duckdb_path を接続して動作します。
  - `MONITOR_POLL_INTERVAL` 環境変数で秒数を上書き（不正な値はデフォルトの 60 秒にフォールバック）。
  - `data/stop_requested.flag` が作成されているとループが終了します。

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # データベースパスの指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- ライブラリ的利用（例）
  - リサーチ API:
    ```python
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    ```
  - AI ニューススコア:
    ```python
    from kabusys.ai import score_news
    # score_news(conn, target_date, api_key=...)
    ```

---

## Kill Switch / 停止フラグについて

- Kill Switch:
  - `KillSwitch` は `data/kill.flag` ファイルの作成で ExecutionEngine に停止シグナルを送ります。監視が検出した異常（ドローダウン超過など）でファイルを作成します。
  - ファイル作成は冪等（既に存在すれば上書きしない）です。

- stop_requested.flag:
  - `data/stop_requested.flag` は運用者がプロセスに安全停止を要求するために使用するファイルです。`run_execution` と `run_monitoring` のループはこのファイルの存在を監視し、検知時にシャットダウンします。

- PID ファイル:
  - ExecutionEngine は PID を `data/execution.pid` に保存します。監視や運用ツールがプロセスの存在を確認するのに利用します。

---

## 開発・デバッグのヒント

- ロギング:
  - `kabusys.utils.logging_setup.setup_logging(app_name="...")` を全起動スクリプトが利用します。ログは標準出力および `logs/<app_name>.log` に日次ローテートで出力されます。

- プロセス優先度:
  - スクリプト起動時に `set_process_priority("high")` を呼んでいます（権限がない場合は警告のみ）。

- DuckDB / SQLite:
  - DuckDB は分析向け、SQLite は監視・トレードログ用（軽量永続層）として使われています。
  - `monitoring_db.init_monitoring_db` はテーブルの初期化・マイグレーションを行います（冪等）。

- OpenAI 呼び出し:
  - API の呼び出しはリトライ・バックオフ・レスポンス検証を行います。`OPENAI_API_KEY` を設定してください。テストでは `_call_openai_api` をモックできます。

---

## ディレクトリ構成

主要なファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在する場合)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/, research/, ai/ etc. （上記参照）
- data/   — データファイル保存先（SQLite, pid, flag 等）
- logs/   — ログ出力先（デフォルト）

（実際のリポジトリでは上記以外の補助スクリプトやモジュールが含まれる可能性があります）

---

## よくある操作例

- 開発用（ペーパートレード）で起動:
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- 監視を別プロセスで起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
- Kill Flag をクリア:
  ```bash
  # 手動で削除
  rm -f data/kill.flag
  ```

---

## トラブルシューティング

- OpenAI 関連エラー:
  - `OPENAI_API_KEY` が未設定、または API レートリミット・ネットワークエラー。APIキーの確認と再試行を行ってください。ログにリトライ情報が出力されます。

- DB 関連:
  - DuckDB/SQLite のパスが存在しないディレクトリを指している場合、`validate_config` が警告を出します。ディレクトリを作成するか、環境変数で適切なパスを指定してください。

- ログファイルが作れない:
  - `LOG_DIR` の書き込み権限やディレクトリ作成の失敗が原因です。`logs/` のパーミッションを確認してください。失敗するとコンソールのみの出力にフォールバックします。

---

README は以上です。必要であれば、デプロイ手順（systemd / Docker / Kubernetes 向け）や CI/CD、詳細な設定例（.env のサンプル）を追加しますか？
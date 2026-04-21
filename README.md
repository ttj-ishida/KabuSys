# KabuSys

日本株自動売買システムのコアモジュール群（ライブラリ + 起動スクリプト群）。  
このリポジトリは以下の機能を持つコンポーネント群を含みます：ポートフォリオ構築、ポジションサイジング、リスク調整、研究用ファクター計算、監視・アラート、ペーパートレード検証、OpenAI を使ったニュース NLP / レジーム判定など。

---

## プロジェクト概要

- 目的：日本株の自動売買エンジンとそれを支える周辺ツール群を提供する。
- アーキテクチャ要点：
  - 実行時設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込み（自動読み込みを無効化することも可能）。
  - 発注ロジックは `ExecutionEngine`（起動スクリプト: `run_execution.py`）で稼働。`KABUSYS_ENV` によって paper_trading（モックブローカー）/ live（本番）の挙動が切り替わる。
  - 監視は `MonitoringEngine`（起動スクリプト: `run_monitoring.py`）でポーリング実行。
  - 永続化：SQLite（監視・注文ログ等）と DuckDB（分析用データ）を併用。
  - OpenAI を利用するモジュール（ニュース NLP・レジーム判定）は API キーを必要とする（フェイルセーフ・リトライ機構あり）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（paper_trading 時は MockBroker, DB を分離）
  - run_monitoring.py — SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL で間隔制御）
- 設定 / ユーティリティ
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env / config/*.yaml 等の事前検証 CLI
  - config.py — Settings クラス（環境変数ラッパ）
  - logging_setup.py — 統一的なログ設定（コンソール + 日次ローテーション）
  - process_priority.py — プロセス優先度 / CPU affinity 設定（psutil ベース）
- モニタリング
  - monitoring_engine.py — 各 Monitor の集約とポーリング
  - system_monitor.py / trade_monitor.py / risk_monitor.py — それぞれのチェックロジック
  - monitoring_db.py — SQLite テーブルの初期化・簡易永続化 API
  - kill_switch.py — 条件により `data/kill.flag` を書いて ExecutionEngine に停止シグナル
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py
- 研究用ツール
  - research.factor_research — Momentum / Value / Volatility 等のファクター計算（DuckDB）
  - research.feature_exploration — 将来リターン計算、IC（Information Coefficient）等
- AI（OpenAI 連携）
  - ai.news_nlp.py — ニュースのセンチメントを LLM でスコアリングして ai_scores に書き込み
  - ai.regime_detector.py — ETF の MA とマクロニュースを組み合わせて市場レジーム判定
- 補助ツール
  - tools.paper_verification_report.py — ペーパートレード検証レポート生成

---

## 前提 / 推奨環境

- Python 3.10 以上（PEP 604 の型記法 `X | Y` を使用しているため）
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml（`validate_config.py` の YAML 検証を有効にする場合）
- 推奨：仮想環境（venv / pyenv / conda など）

例（pip で最低限インストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai
# YAML 検証を有効化するなら:
pip install pyyaml
```

※ requirements.txt があればそれを利用してください:
```
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで J-Quants トークン、kabu API パスワード、KABUSYS_ENV などを設定します。

5. 設定の検証
   ```
   python -m kabusys.validate_config
   # 警告も厳密に扱いたい場合:
   python -m kabusys.validate_config --strict
   ```

6. 必要ディレクトリの確認（`data/` や `logs/` は自動作成されますが、パーミッションなど注意）

---

## 使い方（起動コマンド例）

- ExecutionEngine を起動（デーモン化は実行環境で設定）
  ```
  python -m kabusys.run_execution
  ```
  挙動:
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を利用し、`data/paper_trading.db` に記録（本番 DB と分離）。
  - 起動時に `data/stop_requested.flag` が存在する場合は起動を中止します。
  - PID ファイルを書き込む（Settings.pid_file_path の値）。

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルト 60 秒ごとにポーリング。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒単位）。
  - 停止制御: プロジェクトルート `data/stop_requested.flag` を作成すると監視ループが終了します（ファイル存在チェックで停止）。
  - 監視は常に本番用の sqlite_path を使用（環境に依らず監視 DB を共有）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - 環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出しで明示的に API キーを渡してください。
  - 例（ライブラリ API を直接呼ぶ場合）:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 20), api_key="sk-...")
    ```

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（デフォルトあり）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
- LOG_LEVEL — ログレベル（INFO など）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス
- KILL_FLAG_PATH — kill.flag のパス（KillSwitch が書き込む）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading の約定モード（instant / partial / never / reject）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）

.env 自動読み込み:
- プロジェクトルートに `.env` / `.env.local` がある場合、自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 停止 / Kill 制御

- run_monitoring と run_execution はプロジェクトルートの `data/stop_requested.flag` を監視しており、存在するとループを終了します（手動停止用）。
- `KillSwitch` は監視モジュールが判定した場合に `data/kill.flag` を作成し、ExecutionEngine に停止シグナルを送出する仕組み（ExecutionEngine 側は設定に従って kill.flag を参照し停止処理を行います）。
- ExecutionEngine の PID は `data/execution.pid`（デフォルト）に書き込まれます。

---

## ディレクトリ構成（主要ファイル）

想定ルート: src/kabusys 以下

- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動ロード
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
  - utils/
    - logging_setup.py
    - process_priority.py

（補足）
- `config/` ディレクトリ（プロジェクトルート配下）には各種 `*_config.yaml` が置かれる想定です。`validate_config.py` が存在チェック・パース検証を行います（PyYAML がインストールされている場合）。

---

## 開発者向けメモ / 注意点

- SQLite / DuckDB のパスは Settings で一元管理。paper_trading 環境では SQLite を分離しているため本番データと混ざらないようになっています。
- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- Process priority / CPU affinity は `psutil` を使って OS に合わせて設定されます（権限不足や未対応 OS の場合は警告を出してスキップ）。
- OpenAI 呼び出しはリトライや JSON バリデーションを組み込んでおり、API 失敗時はフェイルセーフで処理を継続する設計です。
- `.env` は機密情報を含むため Git にコミットしないでください（`config_setup.py` のヘッダにも注意書きあり）。

---

README は以上です。実行上の不明点や、各モジュールのより詳細な使い方（ExecutionEngine の API、OrderManager / Reconciler の挙動など）を知りたい場合は、対象ファイルや実行ログを指定していただければ、用途に応じた追補ドキュメントを作成します。
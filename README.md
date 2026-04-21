# KabuSys — 日本株自動売買システム（README）

本ドキュメントは、このリポジトリの概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめた README です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な機能は以下の通りです：

- 戦略・ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 発注実行エンジン（ExecutionEngine）
- リスク監視・監督（ドローダウン、ポジション上限など）
- システム監視（CPU/メモリ/ディスク、プロセス稼働、データ鮮度）
- AI を用いたニュースセンチメント（OpenAI API 経由）
- ペーパートレード用の分離された DB 対応
- 運用支援ツール（設定ウィザード、設定検証、レポート生成など）

設計方針として、DB（DuckDB / SQLite）や外部 API 呼び出しの扱いに注意を払い、運用時のフェイルセーフや冪等性を重視した実装がなされています。

---

## 主な機能一覧

- config
  - .env 自動読み込み（プロジェクトルートに基づく）
  - Settings クラスで環境変数を一元管理
  - `config_setup`：.env を対話的に作成・更新
  - `validate_config`：起動前の設定検証（必須環境変数、YAML ファイル、パス等）
- execution
  - ExecutionEngine：発注処理を行うエンジン
  - BrokerClientFactory：`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、ペーパートレード DB に記録
  - RiskManager / OrderManager / Reconciler 等の発注周りコンポーネント
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - MonitoringDB：SQLite ベースの監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）
  - KillSwitch：危険条件で ExecutionEngine 停止を指示するフラグ機構（data/kill.flag）
  - run_monitoring.py：ポーリングループで監視を継続実行
- portfolio
  - 候補選定、スコア配分、セクター制限、ポジションサイズ計算（単元株丸め等）
- research
  - ファクター計算（momentum / volatility / value）
  - forward returns / IC 計算 / 統計サマリー
- ai
  - news_nlp：ニュース記事を OpenAI に送信して銘柄別センチメントを計算して保存
  - regime_detector：ETF（1321）MA 等とマクロニュースを合成して市場レジーム判定
- tools
  - paper_verification_report：ペーパートレード DB を集計して検証レポートを生成

---

## 前提・依存関係

- 推奨 Python バージョン: 3.10 以上（型注釈に Python 3.10 の構文を使用）
- 主要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（optional、validate_config の YAML 検証に使用）
- 標準ライブラリ: sqlite3, threading, datetime, logging など

pip でインストールする一例:
```
python -m pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   python -m pip install -r requirements.txt
   ```
   あるいは（requirements.txt がない場合）:
   ```
   python -m pip install duckdb psutil openai PyYAML
   ```
4. 初期環境変数 (.env) を作る（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで作成後、`.env` をプロジェクトルートに保存します。
   注意: `.env` は Git にコミットしないでください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   問題がなければ OK 表示、`--strict` を付けると警告もエラー扱いになります。

6. DB ディレクトリの確認
   - デフォルト DuckDB: `data/kabusys.duckdb`
   - デフォルト SQLite (monitoring): `data/monitoring.db`
   - ペーパートレード SQLite: `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時に使用）
   必要に応じて `.env` の変数で上書きします。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient を使い、paper DB に記録します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp, ai.regime_detector で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60） — run_monitoring で利用

サンプル `.env`（抜粋）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 実行方法・使い方

- 設定ウィザード（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - 監視ループはプロジェクトルート下 `data/stop_requested.flag` の存在を検知すると終了します。
  - Monitoring は常に（環境に関わらず）本番用の `sqlite_path` を使用して監視 DB に接続します。

- ExecutionEngine（発注エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録します（本番 DB と分離）。
  - 起動直後に `data/stop_requested.flag` が存在していれば起動を中止します。
  - 起動中に同フラグが作成されるとエンジンを停止します。
  - PID ファイル: `data/execution.pid`（デフォルト）。Settings.pid_file_path で変更可能。
  - Execution 側でも `KILL_FLAG_CLEAR_ON_START` 等の設定挙動があります（注意）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 関連
  - OpenAI API を使用する機能（news_nlp, regime_detector）は `OPENAI_API_KEY` が必要です。
  - API 呼び出しはリトライやフェイルセーフを備えていますが、API キーが未設定だと例外になります。

---

## 運用上の注意

- .env は絶対にリポジトリにコミットしないでください（機密情報含む）。
- 本番実行時は `KABUSYS_ENV=live` を設定し、`validate_config` で本番用ガード（LINE 設定や Kill Flag 設定）を十分確認してください。
- Monitoring の stop フラグや kill flag（data/kill.flag）は運用で重要な制御信号になります。意図せず削除しないでください。
- プロセス優先度や CPU affinity の設定は OS 権限により失敗することがあります（ログに警告が出ます）。

---

## ディレクトリ構成（抜粋）

（リポジトリの `src/kabusys` を基準に主要ファイルを示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — Monitoring DB 層（SQLite）
    - monitoring_engine.py   — モニタ群を束ねるエンジン
    - system_monitor.py      — システム監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - trade_monitor.py       — （省略: 注文監視）
    - alert_manager.py       — （省略: アラート送信）
    - kill_switch.py         — Kill Switch 実装（data/kill.flag）
  - execution/               — 発注・エンジン関連（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py
  - data/                    — （運用時に各種 DB / フラグファイルを配置）
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード)
    - kill.flag
    - stop_requested.flag
    - execution.pid

---

## 開発者向けメモ

- ロギングは共通の setup_logging() を使用して一元管理しています。ログは stdout と日次ローテーションファイル（logs/<app_name>.log）に出力されます。
- `.env` の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。
- MonitoringDB の初期化は冪等（init_monitoring_db）です。既存スキーマに対する簡易マイグレーション（カラム追加チェック）も含まれます。
- AI 呼び出し部分はネットワーク/429/5xx に対してリトライやフォールバックを設けており、API 失敗時はスコア計算をスキップまたは中立値にフォールバックする設計です。

---

README は以上です。必要であれば、運用手順書（起動スクリプトの systemd / supervisor 設定例やデプロイ手順）、より詳しい環境変数一覧、各コンポーネントの API ドキュメントを追加します。どの情報を優先して追加しますか？
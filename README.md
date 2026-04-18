# KabuSys — 日本株自動売買システム README

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。
コードはトレード実行・監視・ポートフォリオ構築・リサーチ・AI ニュース解析等の
機能をモジュール化しています。本 README はプロジェクト概要、機能一覧、
セットアップ／起動手順、使い方のサンプル、ディレクトリ構成を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 主な機能
- 必要要件
- セットアップ手順
- 設定 (.env / config)
- 実行方法（各スクリプトの使い方）
- Kill / Stop フラグの仕組み
- よく使う環境変数
- ディレクトリ構成（主要ファイル説明）
- 注意事項 / トラブルシューティング

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤ライブラリ群です。  
主要コンポーネントは次の通りです。

- ExecutionEngine: ブローカークライアントを通じて注文を管理・実行
- Monitoring: システム健全性、注文ログ、リスク監視、Kill Switch 等の監視機構
- Portfolio: 候補選定・重み付け・ポジションサイズ算出（純粋関数）
- Research: DuckDB 上でのファクタ計算・特徴量解析
- AI: OpenAI（LLM）を用いたニュースセンチメントやレジーム判定
- Tools: ペーパートレード検証レポート作成などのユーティリティ

設計上、研究・AI モジュールは本番口座や発注 API にアクセスしないように分離されています。
また、ペーパートレード用 DB は本番 DB とは分離されます（KABUSYS_ENV に依存）。

---

## 主な機能一覧

- system_monitor: CPU/メモリ/ディスク、Execution プロセスの存否、データ鮮度を定期記録
- trade_monitor: 注文の滞留・約定異常などの検出（ログ参照）
- risk_monitor: ドローダウンや保有銘柄上限の検出・アラート記録
- KillSwitch: 指定条件での停止フラグ (data/kill.flag) 発行
- ExecutionEngine: ブローカークライアント抽象化（本番/ペーパー分離）、リスク管理、発注
- portfolio.*: 候補選定、重み計算、セクター制限、ポジションサイズ計算
- research.*: ファクター計算（モメンタム、ボラティリティ、バリュー）や IC 計算
- ai.news_nlp / ai.regime_detector: OpenAI を利用したニューススコアリング・レジーム判定
- tools.paper_verification_report: ペーパートレード DB から PASS/FAIL 形式の検証レポート生成
- config_setup / validate_config: .env の対話式作成＆設定検証 CLI

---

## 必要要件（基本）

- Python 3.10+
  - typing における union 型記法 (A | B) を利用しているため 3.10 以上を推奨
- 推奨（実行する機能に依存）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証時。任意）

例: pip インストール例（必要に応じて調整してください）
```
pip install duckdb psutil openai pyyaml
```

注: requirements ファイルは本リポジトリに含まれていない想定のため、実行環境に合わせて必要パッケージをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージ展開
2. Python 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict  # 警告を FAIL 扱いにする
     ```
5. 必要なディレクトリ（`data/`、`logs/` 等）は実行時に自動作成されますが、権限に注意してください。

---

## 設定 (.env / config/*.yaml)

自動ロード
- プロジェクトルートに `.env` / `.env.local` がある場合、起動時に自動で読み込まれます（OS 環境変数を上書きしない）。
- 自動ロードを無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

主な環境変数（必須 / 重要）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development)
  - 値: development | paper_trading | live
  - paper_trading の場合、ExecutionEngine は MockBroker を使い paper 用 SQLite に書き込みます
- OPENAI_API_KEY (AI 機能利用時に必要)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — Monitoring が使用（監視は環境に依らず本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — KABUSYS_ENV=paper_trading 時の専用 DB
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- PAPER_FILL_MODE (paper の MockBroker の約定モード: instant|partial|never|reject)

簡単な .env 例
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

config/*.yaml
- `config/` 以下に複数の YAML 設定ファイル（system_config.yaml 等）が想定されています。
- `python -m kabusys.validate_config` で存在確認・YAML パース検証を行います（PyYAML が必要）。

---

## 実行方法（主要スクリプト）

プロジェクトはパッケージ化された Python モジュールとして実行できます。最も基本的な実行法は `python -m kabusys.<module>` です。

- ExecutionEngine を起動（実際に注文を行う/ペーパーは分離）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録されます。
  - 実行中は `data/execution.pid` に PID が書き込まれます。
  - 停止用フラグ: `data/stop_requested.flag` があると起動を中止・実行中は停止処理が行われます。

- Monitoring を起動（定期ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    ```
    export MONITOR_POLL_INTERVAL=30
    ```
  - Monitoring は KABUSYS_ENV に関わらず本番の `SQLITE_PATH` を使用して監視データを永続化します。
  - 停止フラグ: `data/stop_requested.flag`（存在するとループを終了）

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示したい場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

ログ
- ログは `kabusys.utils.logging_setup.setup_logging` により統一的に設定され、コンソール出力（stdout）と日次ローテーションファイル（`logs/<app_name>.log`）へ出力されます。
- 起動スクリプトは `app_name` として `execution` / `monitoring` などを渡しています。

---

## Kill / Stop フラグの仕組み

- 停止（停止要求）:
  - `data/stop_requested.flag` — 管理用の簡易停止フラグ。`run_execution` / `run_monitoring` はこのファイルを検知して安全に停止します。
- Kill Switch（自動停止）:
  - `KillSwitch`（監視ルールにより）`data/kill.flag` を書き込むことで ExecutionEngine に対して停止を要求します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では推奨されない）。
- PID ファイル:
  - `data/execution.pid` に ExecutionEngine の PID が書き込まれます。

---

## よく使う環境変数（まとめ）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 重要
  - KABUSYS_ENV (development | paper_trading | live)
  - OPENAI_API_KEY (AI 機能使用時)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔 秒)
  - PAPER_FILL_MODE (instant|partial|never|reject)
  - KILL_FLAG_CLEAR_ON_START (0/1)

---

## ディレクトリ構成（主要ファイルの説明）

以下はパッケージ内部の主要なファイルと簡単な説明です（src/kabusys ベース）。

- __init__.py
  - パッケージ定義、バージョン情報
- config.py
  - 環境変数読み込み・Settings クラス（アプリケーション設定の取得）
- config_setup.py
  - `.env` を対話式に作成 / 更新するウィザード
- validate_config.py
  - .env & config/*.yaml を検証する CLI
- run_execution.py
  - ExecutionEngine の起動スクリプト（PID / stop flag 管理、paper_trading の分離）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
- utils/
  - logging_setup.py: ログ設定ユーティリティ（stdout + 日次ファイルローテーション）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py: SQLite を使った監視ログ永続化（テーブル作成 / CRUD）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
- execution/ (実行ロジック: BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等)
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py: OpenAI を使ったニュースセンチメント解析（ai_scores へ書き込み）
  - regime_detector.py: マクロ+ETF MA200 を使った市場レジーム判定
- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成

例（ツリー）:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ config_setup.py
├─ validate_config.py
├─ run_execution.py
├─ run_monitoring.py
├─ utils/
│  ├─ logging_setup.py
│  └─ process_priority.py
├─ monitoring/
│  ├─ monitoring_db.py
│  ├─ system_monitor.py
│  ├─ risk_monitor.py
│  └─ ...
├─ execution/
│  └─ ...
├─ portfolio/
│  └─ ...
├─ research/
│  └─ ...
├─ ai/
│  └─ ...
└─ tools/
   └─ paper_verification_report.py
```

---

## 注意事項 / トラブルシューティング

- SQLite / DuckDB のパスに書込権限があるか確認してください。
- Monitoring は常に `SQLITE_PATH`（本番用）を使用します。環境にかかわらず監視データは本番 DB に記録されますので注意してください。
- KABUSYS_ENV=paper_trading の場合、Execution は paper 用 DB に対して動作し本番 DB とは分離されます。
- OpenAI API を使う機能はネットワークアクセスと API キーが必要です。失敗時はフェイルセーフ（スコア=0 など）で続行しますが、API 利用制限や料金に注意してください。
- `psutil` を使ったプロセス優先度/アフィニティ設定は OS により挙動や権限が異なります。権限不足だと警告が出ますが処理は継続されます。
- config/*.yaml のパース検証には PyYAML が必要です（インストールされていない場合は検証がスキップされます）。

---

もし README の特定セクション（例えばデプロイ例 systemd ユニット、CI 設定、より詳しい ExecutionEngine の設定や BrokerFactory の使い方等）を追加したい場合は、必要な対象部分を指定してください。
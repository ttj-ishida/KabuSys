# KabuSys

日本株自動売買システムのリポジトリ（軽量コアライブラリ）。  
この README はコードベース（src/kabusys 以下）に基づき、導入・運用に必要な情報を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主要な機能は以下の通り：

- 発注・リスク管理を担う ExecutionEngine（プロセス化して起動）
- システム状態・注文状況を監視する Monitoring（ポーリングで監視ログを保存、アラート/kill switch）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用モジュール（ファクター計算・特徴量探索）
- AI 補助（ニュースセンチメント、レジーム判定） — OpenAI API を使用
- 運用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

設計方針の例：
- DuckDB や SQLite など簡易 DB を用いてデータ永続化・分析を行う
- 本番/ペーパートレードを分離（paper_trading 用 DB）
- ルックアヘッドバイアス対策：日付計算で `date.today()` を直接参照しない実装方針が多く採用されている

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し `data/paper_trading.db` に記録（本番DBと分離）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番 sqlite_path を使用
- config_setup.py
  - 対話式 `.env` 作成・更新ウィザード
- validate_config.py
  - `.env` と config/*.yaml の存在・基本妥当性を検証する CLI
- tools/paper_verification_report.py
  - Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）
- portfolio モジュール
  - 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数などの純粋関数群
- research モジュール
  - ファクター計算（モメンタム、ボラティリティ、バリュー）や IC/統計分析
- ai モジュール
  - news_nlp: ニュースを LLM でセンチメント評価し ai_scores に格納
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジームを判定

ユーティリティ:
- utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテートファイル）
- utils/process_priority.py: プロセス優先度 / CPU affinity 設定

永続化（監視用）:
- monitoring/monitoring_db.py: SQLite に対するテーブル作成・読み書きラッパー

---

## 要件（主な外部パッケージ）

- Python（互換性はコードに明記はないが、typing の構文等から 3.9+ を想定）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証を行う場合に必要）

標準ライブラリ（sqlite3, logging, threading, datetime など）は不要な追加インストールは不要です。

例（仮の requirements）:
```
duckdb
psutil
openai
PyYAML    # optional
```

仮想環境を作成してからインストールしてください：
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成し有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数ファイル `.env` を作成（対話式ウィザード推奨）

対話式ウィザードで `.env` を作る例：
```bash
python -m kabusys.config_setup
```

ウィザードで `.env` を作成したら設定検証：
```bash
python -m kabusys.validate_config
# 警告も失敗にしたい場合:
python -m kabusys.validate_config --strict
```

重要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（例: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時 kill.flag を自動クリアするか: 0/1）

サンプル（.env の抜粋）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方

各スクリプトはモジュール実行可能（python -m ...）になっています。

- ExecutionEngine を起動（本番またはペーパートレード）
  - 本番（`KABUSYS_ENV=live` または `development` など適宜）:
    ```bash
    python -m kabusys.run_execution
    ```
  - ペーパートレード（`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用）
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  実行時の注意:
  - 実行前に `.env` を作成・検証することを推奨します
  - paper_trading 時は `PAPER_TRADING_SQLITE_PATH` に記録され、本番データとは分離されます
  - 起動時に `data/execution.pid` を利用し、stop フラグ `data/stop_requested.flag` を監視します

- Monitoring（SystemMonitor）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  オプション:
  - ポーリング間隔を秒で変更:
    ```bash
    MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
    ```
    デフォルトは 60 秒。無効な値（0 以下や非整数）は無視され、デフォルトが使われます。
  機能概要:
  - システムリソース（CPU, メモリ, ディスク）や Execution プロセスの存否、データ鮮度をチェックし SQLite に記録します
  - `data/stop_requested.flag` を検知するとループを終了します

- .env ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート出力
  ```bash
  python -m kabusys.tools.paper_verification_report \
    --from 2026-04-01 --to 2026-04-11 \
    --db data/paper_trading.db
  ```
  または環境変数 `PAPER_TRADING_SQLITE_PATH` を設定して `--db` を省略可。

- AI 機能（プログラムから利用）
  - news_nlp.score_news(conn, target_date, api_key=None) — OpenAI API キーは `OPENAI_API_KEY` 環境変数または引数で指定
  - regime_detector.score_regime(...) — 同様に OpenAI API を使用

ログ:
- ログは `kabusys.utils.logging_setup.setup_logging` が統一して設定します。
- デフォルトログディレクトリ: `logs/`、ファイル名はアプリ名 (`execution.log`, `monitoring.log` など)
- 環境変数 `LOG_DIR` で変更可

停止 / Kill Switch:
- Kill Switch は `data/kill.flag` を書き込むことで ExecutionEngine 停止をトリガーします（監視が条件を満たした場合など）。
- `data/stop_requested.flag` を作成すると run_execution/run_monitoring は安全に終了処理を行います。

---

## ディレクトリ構成

以下は主要ファイルの一覧（src/kabusys 配下）です。実際のリポジトリにはさらにファイルやサブパッケージがある可能性があります。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/            # 発注系の実装（BrokerClientFactory, ExecutionEngine, OrderManager 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
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

（注）上記ファイル群はコードベースの説明から抜粋しています。リポジトリ内の実際の構成は差分がある場合があります。

---

## 開発者向けメモ / 運用上の注意

- 環境ファイル自動ロード:
  - `kabusys.config` はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動で読み込みます。
  - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成を行い、既存 DB にカラムが無い場合の簡易マイグレーションも実施します（例: `peak_value`, `latency_ms`）。
- AI (OpenAI) 呼び出し:
  - LLM 呼び出しはリトライ・バックオフやレスポンスの検証（JSON モードのパース）を考慮した実装です。
  - API キーは `OPENAI_API_KEY` で指定。テスト時は API 呼び出し関数をモック可能（モジュール内で patch できる設計）。
- ログディレクトリ作成に失敗した場合はファイル出力をスキップし stdout のみで継続します。
- プロセス優先度・CPU affinity の設定は `psutil` を介して行われますが、権限不足やプラットフォーム差により失敗することがあります（その場合は警告を出して継続）。

---

## トラブルシューティング

- .env に必須項目がない or placeholder のまま → `python -m kabusys.validate_config` で検出可能
- モデル呼び出しで 429 / タイムアウト等が出る → openai 側のレート制限。実装はリトライを行いますが、キー/プランを確認してください
- SQLite / DuckDB のパスが存在しない（親ディレクトリがない） → validate_config が警告を出します。`data/` など必要なディレクトリを作成してください

---

この README はコードベースの主要な運用フローとファイルの要点をまとめたものです。実際の運用時は `.env` の保護（絶対に Git にコミットしない）や本番環境での慎重な設定（特に `KABUSYS_ENV=live` 時）を徹底してください。質問や追加ドキュメントが必要であれば、どのセクションを詳しく書くか教えてください。
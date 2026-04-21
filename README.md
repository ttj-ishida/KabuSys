# KabuSys

日本株向けの自動売買システム（プロトタイプ実装）。  
戦略・ポートフォリオ構築・発注エンジン・監視・アラート・リサーチ用ユーティリティを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の役割を持つコンポーネント群を提供します。

- 戦略・ファクター計算（research）
- ポートフォリオ構築（portfolio）
- 発注／Execution Engine（execution）
- 監視・リスク検出（monitoring）
- ニュース NLP / レジーム判定（AI 集約）
- 運用支援ツール（設定ウィザード、構成検証、ペーパートレード検証レポート）

設計方針の一部：
- 本番とペーパートレードの DB を分離（`KABUSYS_ENV=paper_trading` 時は paper DB を使用）
- ルックアヘッドバイアスを避ける実装（API 呼び出しや日付処理に注意）
- OpenAI を用いる処理は APIキー要、冗長性（バックオフ等）を持たせている
- ログ・DB・フラグファイルでプロセス間の連携を行う（PID ファイル / stop flag / kill flag）

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（`run_execution.py`）
  - `KABUSYS_ENV=paper_trading` では MockBroker を用い、ペーパートレード用 DB に記録
  - プロセス優先度設定、PID 書き出し、停止フラグ監視
- Monitoring（`run_monitoring.py` と `monitoring` パッケージ）
  - システム状態（CPU/メモリ/ディスク）監視
  - トレードログ / リスクログ の集計・監視
  - Kill Switch（条件に応じて `data/kill.flag` を書き込む）
  - アラート発行（AlertManager）
- AI モジュール
  - ニュースのセンチメント集約・スコア保存（`ai/news_nlp.py`）
  - 市場レジーム判定（`ai/regime_detector.py`）
- Research（`research`）
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン・IC 計算、特徴量サマリ
- Portfolio（`portfolio`）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- ツール
  - 環境設定ウィザード（`.env` 作成支援）`config_setup.py`
  - 設定検証 CLI `validate_config.py`
  - Paper Trading 検証レポート生成 `tools/paper_verification_report.py`

---

## 前提 / 必要環境

- Python 3.10+
- 主な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（任意・config YAML 検証用）
- OS: Linux / macOS / Windows（プロセス優先度設定等で差異あり）

実際の要件は環境に合わせて requirements ファイル等を用意してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して有効化します。
   - python -m venv .venv
   - source .venv/bin/activate など

2. 必要パッケージをインストールします（例）。
   - pip install duckdb psutil openai PyYAML

3. 初期設定ファイル（`.env`）を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabu API パスワード 等を入力してください。

4. 設定検証を実行します。
   - python -m kabusys.validate_config
   - `--strict` を指定すると警告も失敗扱いになります。

5. 必要に応じてデータディレクトリを作成します（通常は自動作成されますが権限エラー等に注意）。
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading sqlite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - ログディレクトリ: logs/（`LOG_DIR` 環境変数で変更可）

注意:
- `.env`（機密情報）を Git にコミットしないでください。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API パスワード）
- OPENAI_API_KEY — AI モジュール利用時に必要
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`
- LOG_LEVEL — `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の fill モード（`instant`|`partial`|`never`|`reject`）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（`0`/`1`）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用）

---

## 使い方（実行例）

- 環境準備（例）
  - .env を作成/編集して、KABUSYS_ENV 等を設定する。

- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 動作中は PID ファイル（デフォルト: data/execution.pid）を書きます。
  - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB に記録され、本番 DB とは分離されます。

- Monitoring の起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - デフォルト 60 秒間隔。環境変数で変更可:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

停止／フラグ関連:
- グレースフル停止（run_execution / run_monitoring）は `data/stop_requested.flag` を作成するとループが検知して終了します。
- Kill Switch（監視により実行エンジン停止を要求する仕組み）は `data/kill.flag` を書き込みます。`KILL_FLAG_CLEAR_ON_START=1` にすると起動時に自動クリアされますが本番では `0` が推奨です。

ログ:
- setup_logging により stdout と `logs/<app>.log` に出力（ファイルは日次ローテーション、30 日保持）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py — パッケージ宣言
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores へ書込
  - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite 操作用ラッパ（テーブル作成・読み書き）
  - system_monitor.py — システム状態 / データ鮮度監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - trade_monitor.py — （注文ログ監視等; 実装参照）
  - kill_switch.py — kill.flag の作成・評価
  - monitoring_engine.py — 各モニタの取りまとめ
  - alert_manager.py — （アラート発行; 実装参照）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - 発注エンジン / ブローカー抽象 等（エンジンの起動／発注処理）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出・資金制限処理
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB 利用）
  - feature_exploration.py — 将来リターン・IC 等の分析ユーティリティ
- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

設定ファイル（プロジェクトルートに配置想定）:
- .env, .env.local — 環境変数
- config/*.yaml — 各種構成ファイル（system_config.yaml 等、validate_config で参照）

---

## 開発／運用上の注意点

- 本番運用時（KABUSYS_ENV=live）は特に `KILL_FLAG_CLEAR_ON_START` や LINE の通知設定を確認してください（validate_config で警告を出します）。
- OpenAI API を使う処理は API キーが必要です。失敗時はフェイルセーフ（デフォルト値やスキップ）になるよう実装されていますが、API コスト／レート制限には注意してください。
- DuckDB / SQLite のファイルパスは環境変数で変更可能です。ファイルのパーミッション・ディスク容量に注意してください。
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみになります（警告が出ます）。

---

## トラブルシューティング

- 起動時に必須環境変数エラーが出る:
  - `.env` を作成し、`JQUANTS_REFRESH_TOKEN` および `KABU_API_PASSWORD` を設定してください。
- ログファイルが作成されない:
  - `LOG_DIR` 環境変数や filesystem の権限を確認。ログディレクトリは自動作成を試みますが失敗することがあります。
- OpenAI API 呼び出しでエラー:
  - `OPENAI_API_KEY` が設定済みか確認。レート制限やネットワークエラーはリトライロジックがあります。
- 実行エンジンが停止しない:
  - `data/stop_requested.flag` を作成すると実行スクリプトはループを抜けます。監視側からの強制停止は `data/kill.flag` が使われます。

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。各モジュールの詳細な挙動・引数・戻り値などはソースコード内の docstring を参照してください。必要であれば README に含める追加の利用例や運用手順を作成します。
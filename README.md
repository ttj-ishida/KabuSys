# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群です。  
本リポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・ポジションサイジング、リサーチ（ファクター計算）、およびニュースを用いた AI スコアリング等のコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を備えたモジュール群で構成されています。

- 発注エンジン（実口座 / ペーパートレード対応）
- 実行監視（CPU/メモリ/ディスク、データ鮮度、プロセス死活）
- リスク監視（ドローダウン、ポジション上限等）と Kill Switch
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- ニュースを用いた AI（OpenAI）によるセンチメントスコアリングと市場レジーム判定
- ペーパートレード検証レポート生成ツール

設計上のポイント：
- 環境変数 / .env で設定管理
- SQLite（監視・発注ログ）および DuckDB（分析・リサーチ）を使用
- ペーパートレードは本番 DB と完全分離（`KABUSYS_ENV=paper_trading` 時は `data/paper_trading.db` を使用）
- ロギングは統一されたセットアップ（stdout + 日次ローテートファイル）

---

## 主な機能一覧

- run_execution: ExecutionEngine 起動（`python -m kabusys.run_execution`）
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード DB に記録
  - 起動/停止は flag ファイルで制御（`data/stop_requested.flag`, `data/kill.flag`）
- run_monitoring: SystemMonitor のポーリングループ起動（`python -m kabusys.run_monitoring`）
  - MONITOR_POLL_INTERVAL 環境変数で間隔を指定可能（デフォルト 60 秒）
  - 監視結果は監視用 SQLite に保存
- config_setup: 対話式 .env 作成ウィザード（`python -m kabusys.config_setup`）
- validate_config: 起動前の設定検証 CLI（`python -m kabusys.validate_config [--strict]`）
- tools.paper_verification_report: ペーパートレード検証レポート生成（`python -m kabusys.tools.paper_verification_report`）
- portfolio モジュール: 候補選定・重み付け・ポジションサイズ計算、セクターキャップやレジーム乗数
- research モジュール: ファクター計算（Momentum / Value / Volatility）・forward returns・IC 等
- ai モジュール: ニュース NLP による銘柄スコアリング、レジーム判定（OpenAI 使用）

---

## セットアップ手順

前提:
- Python 3.9+（typing の記法等を参照）
- system-level: SQLite は標準搭載、DuckDB・psutil・openai 等は pip でインストールします

1. リポジトリをクローン：
   git clone <リポジトリ URL>
2. 仮想環境を作成・有効化（推奨）：
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール（例）：
   pip install duckdb psutil openai
   - 開発時や追加機能で PyYAML 等を使う場合は別途インストールしてください（validate_config は PyYAML があれば config/*.yaml の文法検査を行います）。
   - 実行環境に合わせて requirements.txt があればそれを使用してください。
4. 初期設定：
   - 対話式ウィザードで .env を生成：
     python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参照して値を設定してください）。
5. 設定検証（任意）：
   python -m kabusys.validate_config
   --strict を付けると警告もエラー扱いになります。

注意:
- .env は絶対に Git にコミットしないでください（秘密情報を含みます）。

---

## 主要な環境変数（一部・デフォルト値込み）

主な必須項目：
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要な任意 / デフォルト：
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード SQLite — デフォルト: data/paper_trading.db
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル — デフォルト: data/execution.pid
- KILL_FLAG_PATH: Kill Switch 用フラグパス — デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1） — デフォルト: 0
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒） — デフォルト: 60

（config_setup ウィザードで設定項目を補助的に入力できます）

---

## 使い方（例）

1. ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）：
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - ペーパートレード時は `data/paper_trading.db` を使用します。
   - 起動中の停止は data/stop_requested.flag を生成することで実施できます（run_execution はこのフラグを監視して安全停止します）。

2. Monitoring を起動：
   python -m kabusys.run_monitoring
   - ポーリング間隔を変えたい場合：
     MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring

3. 設定ウィザード：
   python -m kabusys.config_setup

4. 設定検証：
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict

5. Paper Trading の検証レポート生成：
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   --db オプションで DB パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。

6. AI スコアリング / レジーム判定（プログラム経由）：
   - news_nlp.score_news(conn, target_date, api_key=None)
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - API キーは引数または環境変数 OPENAI_API_KEY を使用

ログ:
- ログは stdout に出力され、`logs/<app_name>.log` に日次ローテーションで保存されます（デフォルト 30 日保持）。

停止 / Kill Switch:
- Kill Switch は `data/kill.flag` に理由を書き込むことで ExecutionEngine の停止を促します（monitoring 側から評価して書き込み）。
- Execution 停止（即時）を要求する場合は `data/stop_requested.flag` を作成できます。起動中のスクリプトはこのフラグを検出して停止します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み／Settings
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - 発注エンジン・注文管理・ブローカー抽象化など

src/kabusys/monitoring/
- monitoring_db.py — 監視用 SQLite のスキーマとアクセスラッパ
- system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
- risk_monitor.py — ドローダウン・ポジション上限監視
- trade_monitor.py — （trade 関連監視：滞留注文等）
- monitoring_engine.py — 監視コンポーネント束ねるループ
- kill_switch.py — kill.flag の書き込みユーティリティ
- alert_manager.py — アラート送信（LINE 等）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数計算・制約処理
- risk_adjustment.py — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
- feature_exploration.py — forward returns / IC / 統計サマリ

src/kabusys/ai/
- news_nlp.py — OpenAI を使ったニュースセンチメント集約/書き込み
- regime_detector.py — ma200 + マクロセンチメントを合成してレジーム判定

src/kabusys/tools/
- paper_verification_report.py — ペーパートレードの集計・判定レポート生成ツール

src/kabusys/utils/
- logging_setup.py — 共通ロギング設定
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他:
- data/ — デフォルトで使用される DB / フラグファイルの格納先（自動作成される可能性あり）
  - monitoring.db, paper_trading.db, kabusys.duckdb, execution.pid, kill.flag, stop_requested.flag
- logs/ — ログファイル出力先（デフォルト）

---

## 開発メモ / 注意点

- DuckDB の SQL を使ったファクター計算や AI 連携が多く含まれているため、開発時は DuckDB ファイルに適切なテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）が存在することを確認してください。
- OpenAI を利用する部分は API 呼び出しを行うため、テスト時はモック化（patch）して呼び出しを抑止してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番（KABUSYS_ENV=live）では特に kill.flag やログレベル、LINE 通知設定を慎重に確認してください。validate_config の live ガードを利用してください。

---

必要に応じて README を拡張できます（例：API 詳細、DB スキーマ説明、実運用オペレーション手順、サンプル .env、デプロイ手順など）。どの情報を追加したいか教えてください。
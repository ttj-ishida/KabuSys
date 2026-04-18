# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）のリポジトリです。  
この README はコードベース（src/kabusys 以下）を元に主要コンポーネントと使い方を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 株価データ（DuckDB）を用いたファクター計算・リサーチ（research）
- ポートフォリオ構築（候補選定・重み付け・単元丸め）
- 実際の発注ロジック（ExecutionEngine）とリスク管理
- 監視（MonitoringEngine）・アラート・Kill Switch
- AI（OpenAI）を用いたニュースセンチメント / レジーム判定
- ペーパートレード用の分離 DB と検証ツール

設計方針の一部：
- 環境変数 / .env による設定管理（src/kabusys/config.py）
- Paper Trading（検証）と Live（本番）は DB を分離
- ログは stdout と日次ローテーションファイル（logs/*.log）で出力
- LLM（OpenAI）呼び出しはフェイルセーフでリトライを実装

---

## 主な機能一覧

- 設定ウィザード（.env 生成）: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動スクリプト（ExecutionEngine）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 SQLite に記録
- 監視ポーリング起動スクリプト（SystemMonitor）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可
- 監視コンポーネント群: SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager
- ポートフォリオ構築ユーティリティ: 候補選定 / 等配分・スコア配分 / ポジションサイズ計算
- リサーチ: モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB ベース）
- AI モジュール:
  - ニュース NLP による銘柄別センチメント（ai.news_nlp.score_news）
  - マクロ＋ETF 指標を使った市場レジーム判定（ai.regime_detector.score_regime）
- ツール:
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンしてプロジェクトルートへ移動。

2. Python 仮想環境作成 & 有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール（requirements.txt がない場合は以下主要パッケージを入れてください）:
   - pip install duckdb psutil openai PyYAML
   - （実行環境では他の依存が追加で必要な場合があります）

4. .env の作成:
   - 対話式ウィザードを実行して初期 .env を生成:
     - python -m kabusys.config_setup
   - 生成後、必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を確認・編集してください。

5. 設定検証:
   - python -m kabusys.validate_config
   - 問題があれば修正。--strict を付けると警告も失敗扱いになります。

6. データディレクトリの準備:
   - デフォルトでは data/ 以下に DB・PID・フラグを作成します。必要に応じて .env でパスを上書きしてください。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード
  - development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — 監視用 DB（monitoring）
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading 時に使用
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY: OpenAI 呼び出し時に使用
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (デフォルト: logs/)
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング秒数（デフォルト: 60）

注意: .env ファイルは機密情報を含むため絶対に Git にコミットしないでください。

---

## 使い方（実行方法）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) 扱い

- ExecutionEngine 起動（本番/ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を .env に設定すると paper_trading 用 DB に記録され、本番 DB と分離されます。
  - 停止は data/stop_requested.flag を作成することで行えます（スクリプトは起動時に flag をチェックします）。

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔上書き可（秒）。例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI 関連（プログラム呼び出し）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
    - api_key を None にすると OPENAI_API_KEY を参照します。未設定なら例外。
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ:
- 標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。ログディレクトリは LOG_DIR 環境変数で変更可。

停止 / Kill Switch:
- KillSwitch はリスク条件（ドローダウン超過、ポジション上限超過等）で data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- 外部からの即時停止には data/stop_requested.flag を作成します（run_* スクリプトが検出して終了します）。

---

## ディレクトリ構成（主要ファイルの説明）

（src/kabusys 以下）

- __init__.py
  - パッケージのエントリポイント、バージョン定義

- config.py
  - 環境変数/.env の自動読み込みロジック、Settings クラス（全設定をプロパティとして提供）

- config_setup.py
  - 対話式ウィザードで .env を作成/更新する CLI

- validate_config.py
  - 起動前に環境・設定ファイルの整合性をチェックする CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト
  - BrokerClientFactory を用いてブローカークライアントを生成し、エンジンをスレッドで実行

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト

- ai/
  - news_nlp.py: ニュースを OpenAI に送って銘柄別センチメントを ai_scores テーブルへ書き込む
  - regime_detector.py: ETF+マクロニュースを合成して市場レジームを判定・書き込み

- monitoring/
  - monitoring_db.py: 監視用 SQLite のスキーマ初期化と単純な読み書き API（MonitoringDB）
  - system_monitor.py: CPU/メモリ/ディスク、データ鮮度、実行プロセス PID をチェック
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - kill_switch.py: flag ファイルによる停止信号生成ロジック
  - monitoring_engine.py: 各 Monitor を束ねる実行ループ
  - alert_manager.py, trade_monitor.py 等（アラートや注文監視） — （コードベースに存在）

- execution/
  - execution_engine.py: 発注ループやセッション管理（Engine）
  - broker_factory.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 発注株数計算（単元丸め・資金制約対応）
  - risk_adjustment.py: セクター制限・レジーム乗数

- research/
  - factor_research.py: モメンタム、ボラティリティ、バリュー計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリー

- data/
  - 実行時に生成されるローカルファイル（SQLite, DuckDB, PID, flags 等）
  - デフォルト:
    - data/kabusys.duckdb
    - data/monitoring.db
    - data/paper_trading.db
    - data/execution.pid
    - data/kill.flag
    - data/stop_requested.flag

- logs/
  - 日次ローテーションされたログファイルが生成されます（logs/<app_name>.log）

---

## 注意事項 / 運用メモ

- .env に API キー等の機密情報を含めるため、絶対に Git 等にコミットしないこと。
- KABUSYS_ENV=live は本番モードです。validate_config の警告／チェックを必ず通すこと。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB から分離された専用 SQLite を使用するので、検証時は本番 DB に影響を与えません。
- OpenAI 呼び出しはネットワークエラーや 5xx に対してリトライを行いますが、API キーが未設定の場合は例外が発生します。
- PID / flag ファイルはプロセス制御に使用します。スクリプト起動前に不要なフラグをクリアしてください（KillSwitch の clear() 等も利用可）。

---

## 開発者向け補足

- duckdb 接続を渡して純粋関数としてファクターやレポートを呼べる設計のため、テストが容易です（外部 API との依存を最小化）。
- logging_setup.setup_logging() を各起動スクリプトで最初に呼ぶことで統一的なログ設定が行われます。
- process_priority.set_process_priority() により起動時に優先度を上げる処理があります（psutil を利用）。
- MonitoringDB はスキーマのマイグレーション（カラム追加）を起動時に冪等的に行います。

---

README はここまでです。実際の運用やデプロイ手順（systemd / supervisor / コンテナ化等）は環境に依存するため、この README はローカル開発・手動起動向けの概要としています。追加でデプロイ手順や CI / テストの説明が必要であれば、実行方法（systemd ユニット例、Dockerfile など）を追記します。
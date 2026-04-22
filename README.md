# KabuSys

日本株自動売買システムのライブラリ／実行スクリプト群です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI を用いたニュース評価などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームを想定したコードベースです。主要機能は次のとおりです。

- データ分析（DuckDB を利用したファクター計算）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ決定）
- 発注系（ExecutionEngine、OrderManager、RiskManager 等 — 本番／ペーパートレードに対応）
- 監視（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、アラート）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定） — OpenAI API を利用
- 運用ユーティリティ（.env ウィザード、設定検証、紙トレード検証レポート生成 等）

設計方針としては、DB 書き込み部分を疎に分離し、研究（research）と運用（execution/monitoring）を分ける形になっています。多くの関数は純粋関数として実装され、テストしやすい構成です。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い、paper_trading 用 DB に記録
- Monitoring 起動（python -m kabusys.run_monitoring）
  - SystemMonitor を定期実行して system_status 等を記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- AI:
  - kabusys.ai.news_nlp.score_news: raw_news から銘柄ごとのセンチメントを生成して ai_scores に書込
  - kabusys.ai.regime_detector.score_regime: ma200 とマクロセンチメントを合成して market_regime を更新
- ポートフォリオ:
  - 候補選定 / 等重・スコア重み付け / セクターキャップ / レジーム乗数 / 発注株数算出
- ユーティリティ:
  - ログ設定統一（kabusys.utils.logging_setup）
  - プロセス優先度設定・CPU affinity（kabusys.utils.process_priority）
  - Monitoring DB の永続化層（kabusys.monitoring.monitoring_db）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 環境の準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 推奨パッケージ（最低限）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML パースを行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt があれば pip install -r requirements.txt を利用してください）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは環境変数を直接設定してください。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB。デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/…、デフォルト: INFO）
     - LOG_DIR（ログ出力先、デフォルト: logs/）
     - MONITOR_POLL_INTERVAL（監視ポーリング秒数、run_monitoring では環境変数で上書き可能）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
    - 実行中の PID を data/execution.pid に書きます。
    - data/stop_requested.flag が存在する場合、起動をキャンセルまたは実行の停止トリガになります。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60 秒）。
    - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を参照します（環境にかかわらず）。
    - 停止フラグ: プロジェクトルート/data/stop_requested.flag をチェックしてループを抜けます。
    - ログは logs/monitoring.log（デフォルト）に日次ローテーションで出力されます。

- .env ウィザード
  - python -m kabusys.config_setup
  - 対話式で .env を生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - .env および config/*.yaml の基本的な検証を行います。PyYAML が無ければ YAML 検証はスキップされます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能、または --db オプションで指定できます。

- AI 機能
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して新聞記事のセンチメント評価やレジーム判定を実行できます（OPENAI_API_KEY が必要）。

---

## 運用上のファイル・フラグ

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が存在を確認する停止用フラグ（存在した場合は安全に終了します）。

- data/execution.pid
  - run_execution が起動時に書き込む PID ファイル（デフォルト設定）。

- data/kill.flag
  - KillSwitch が書き込むファイル。存在すると ExecutionEngine に停止指示を与えられます（Settings.kill_flag_path でパスを変更可能）。
  - Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動クリアされますが、本番では危険です（デフォルト 0 推奨）。

- ログ
  - デフォルトは logs/ ディレクトリに app 名ごとのログファイル（例: logs/execution.log, logs/monitoring.log）が日次ローテーションで保存されます。ログ設定は kabusys.utils.logging_setup.setup_logging で制御可能。

---

## 主要モジュール一覧（ディレクトリ構成）

src/kabusys/
- __init__.py
- config.py — Settings クラス・.env 自動ロードロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングスクリプト

サブパッケージ:
- ai/
  - news_nlp.py — raw_news を OpenAI で評価し ai_scores に書込
  - regime_detector.py — ma200 とマクロセンチメントで market_regime を判定
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス・データ鮮度チェック
  - trade_monitor.py — 注文滞留や約定異常の検出（ファイルには別実装あり）
  - risk_monitor.py — ドローダウンやポジション上限の監視
  - kill_switch.py — kill.flag の書き込みロジック
  - monitoring_engine.py — 各モニタをまとめるエンジン
  - alert_manager.py — アラート送信管理（ファイル内参照）
- execution/
  - execution_engine.py — ExecutionEngine とセッション実行
  - broker_factory.py — Broker クライアントの生成（本番/モック切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
- portfolio/
  - portfolio_builder.py — 候補選定・重み算出（等重・スコア重み）
  - position_sizing.py — 株数算出・スケーリング・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / ファクター統計
- tools/
  - paper_verification_report.py — ペーパートレードの検証レポート生成ツール
- utils/
  - logging_setup.py — 統一的なログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
  - 他ユーティリティ

---

## 開発者向けメモ

- DB
  - DuckDB: 分析用に prices_daily / raw_financials / raw_news 等を格納して利用します。パスは DUCKDB_PATH で指定。
  - SQLite: 監視ログや発注ログは SQLite（Settings.sqlite_path, PAPER_TRADING_SQLITE_PATH）を使用します。

- AI（OpenAI）
  - OPENAI_API_KEY を設定して使用してください。AI モジュールは API エラー時にフォールバックする設計ですが、キー未設定だと ValueError を送出する関数があります。

- テスト容易性
  - 多くの外部呼び出しは関数分割されており、_call_openai_api などをモック可能です。
  - MonitoringEngine は run_once() を持つため単体テストが容易です。

- ロギング
  - setup_logging はアプリケーション起動側（run_execution/run_monitoring 等）で必ず呼び出してください。ログディレクトリが作れない場合はコンソールのみで継続します。

---

## よく使うコマンド一覧

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  （ポーリング間隔を 30 秒に変更）

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db を使って別 DB を指定可能

---

## ライセンス / 注意事項

- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダーにも注意喚起があります）。
- KABUSYS_ENV=live の設定は本番発注を行うため、キーやパラメータの確認を十分行ってください（validate_config の live チェックを活用してください）。

---

必要であれば README を英語版にする、あるいは各モジュール（AI、Execution、Monitoring、Research、Portfolio）ごとの詳細なドキュメント（API 例・入出力仕様・DB スキーマ）を追加できます。どの部分を補足しましょうか？
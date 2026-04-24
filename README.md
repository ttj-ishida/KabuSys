# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
このREADMEはコードベース（src/kabusys/*）の概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

注意: 実行には外部ライブラリ（例: duckdb, psutil, openai など）が必要です。requirements.txt が同梱されている前提で説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な役割は次のとおりです。

- データ分析（DuckDB を利用したファクター計算・リサーチ）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- 発注エンジン（ExecutionEngine）と注文管理（OrderManager、OrderRepository）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- AI モジュール（OpenAI を使ったニュースセンチメントや市場レジーム判定）
- ペーパートレード用の分離運用（paper_trading 環境）

設計方針として、データベースは分析用に DuckDB、監視・発注ログ等は SQLite を使用し、環境（development / paper_trading / live）に応じた挙動の切り替えを行います。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートに .env / .env.local があれば読み込み）
  - 対話式ウィザードで .env を生成（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行エンジン
  - ExecutionEngine（run_execution.py から起動）
  - 実際の注文は本番 API / ペーパートレードで Mock を使い分け
  - 停止フラグ（data/stop_requested.flag）や kill.flag による停止制御
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - 監視ログを SQLite に永続化（monitoring_db）
  - KillSwitch による自動停止判定（ドローダウン等で kill.flag を出す）
- ポートフォリオ構築
  - 候補選定、等重/スコア重み付け、セクター上限適用、ポジションサイジング等の純粋関数群
- リサーチ
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュースを LLM（OpenAI）でスコアリングして ai_scores に格納（news_nlp）
  - マクロニュース + ETF MA による市場レジーム判定（regime_detector）
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools.paper_verification_report）

---

## 必須 / 推奨環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う / 重要:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading 環境で使用）
- OPENAI_API_KEY: OpenAI 利用時に必要（AI モジュール）
- LOG_LEVEL / LOG_DIR
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

設定は .env ファイルを使うのが容易です。サンプルは .env.example を参照してください。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - 省略

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存関係インストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は少なくとも duckdb, psutil, openai を入れてください）

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict オプションを付与

6. データディレクトリの準備（ログ / DB の書き込み権限確保）
   - デフォルトで data/ と logs/ を使用します。必要なら事前に作成:
     - mkdir -p data logs

注意:
- OpenAI を利用するモジュールは OPENAI_API_KEY を設定していないとエラーまたはフォールバック処理になります（モジュールにより挙動が異なる）。
- psutil を使ったプロセス優先度設定は管理者権限が必要な場合があります。

---

## 使い方（主要コマンド）

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - プロセスは data/stop_requested.flag を監視して停止。
    - 起動時に Settings.kill_flag_clear_on_start が 1 の場合は kill.flag をクリアする設定が影響します。

- 監視ループ（MonitoringEngine）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を参照（環境に依存せず）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （デフォルトは 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 関連（プログラム API として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols から記事を集約して OpenAI に送信し ai_scores に保存
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA 等とマクロニュースから市場レジームを判定し market_regime に保存

停止（手動）
- エンジンの停止は以下いずれかを行う:
  - data/stop_requested.flag ファイルを作成（run_execution/run_monitoring はこのファイルを見て正常に終了する）
    - 例: touch data/stop_requested.flag
  - KillSwitch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促す（実装により対応）

ログ
- デフォルトのログディレクトリ: logs/
- ログファイル名はアプリ名（execution, monitoring 等）に応じて logs/<app_name>.log に出力

---

## 主要ファイル / モジュールの説明

- run_execution.py
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV に応じて本番/ペーパートレードを切替。

- run_monitoring.py
  - SystemMonitor を周期実行しシステム状態を監視する起動スクリプト。MONITOR_POLL_INTERVAL で間隔変更可能。

- config.py
  - Settings クラスで環境変数をラップ。自動 .env ロード、型変換、検証を提供。

- config_setup.py
  - 対話式で .env を作成するウィザード。

- validate_config.py
  - .env および config/*.yaml の存在/基本整合性をチェックする CLI。

- monitoring/
  - monitoring_db.py: SQLite スキーマ作成・永続化 API
  - monitoring_engine.py: 各 Monitor の統合ループ
  - system_monitor.py: CPU/MEM/DISK/データ鮮度/実行プロセスの監視
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - kill_switch.py: kill.flag の作成/評価
  - alert_manager.py（存在する想定）: 通知周り（LINE等）を管理

- execution/
  - ExecutionEngine、BrokerClientFactory、OrderManager、OrderRepository、RiskManager、Reconciler 等（起動時に組み立てられる）

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定〜株数決定、セクター制限、レジーム乗数

- research/
  - factor_research.py: momentum/value/volatility ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py: OpenAI を用いた銘柄単位のニュースセンチメント集計・保存
  - regime_detector.py: マクロ記事 + ETF MA による市場レジーム判定

- utils/
  - logging_setup.py: 一貫したログ設定（コンソール + 日次ローテーションファイル）
  - process_priority.py: psutil を用いたプロセス優先度・CPU affinity 設定

- tools/
  - paper_verification_report.py: ペーパートレードの運用検証レポート生成

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py
    run_execution.py
    run_monitoring.py
    utils/
      logging_setup.py
      process_priority.py
    monitoring/
      monitoring_db.py
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
    execution/
      execution_engine.py
      broker_factory.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py
      regime_detector.py
    tools/
      paper_verification_report.py
    data/ （実行時に生成される想定）
    logs/ （デフォルトログ出力先）

---

## 運用／運転時の注意点・トラブルシューティング

- DB パスやログディレクトリの親ディレクトリが存在しない場合、起動時に自動作成を試みますが、権限不足で失敗することがあります。事前にディレクトリと権限を確認してください。
- psutil を使ったプロセス優先度設定はプラットフォーム依存であり、権限が無いと設定に失敗します（警告を出して続行）。
- OpenAI の API 呼び出しはレート制限・ネットワークエラー・5xx を想定して指数バックオフでリトライしますが、APIキーが未設定の場合は処理がエラーとなります（モジュールによりフォールバックあり）。
- monitoring 系は停止フラグ（data/stop_requested.flag）をチェックして穏やかに終了します。手動停止の際はこのファイルを作成するか、SIGINT を送ってください。
- .env は絶対に機密情報を git にコミットしないでください（config_setup.py でも明示）。

---

## 追加情報

- 開発者向け: 各モジュールはユニットテストしやすいように純粋関数と DB 接続抽象化を意識して実装されています（例: portfolio 関数群は DB に依存しない）。
- Paper Trading: KABUSYS_ENV=paper_trading にすると ExecutionEngine は MockBroker を使い、発注イベントは別 DB（data/paper_trading.db）に記録され本番 DB と分離されます。

---

何か他に README に追記したい内容（例: 具体的な config/*.yaml の説明、API 仕様、サンプル .env）があれば教えてください。必要に応じて README を拡張します。
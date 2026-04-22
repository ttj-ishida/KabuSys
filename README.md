# KabuSys

日本株向けの自動売買（バックテスト / ペーパートレード / 本番運用）を想定した小規模なシステム群です。  
このリポジトリは、シグナル計算・ポートフォリオ構築・発注エンジン・監視・AI 補助モジュールなどをモジュール化して実装しています。

バージョン: 0.1.0

主な設計方針:
- DuckDB / SQLite によるローカル DB 管理
- 環境変数および .env による簡易設定
- Paper Trading（モックブローカー）と Live（実ブローカー）を明確に分離
- OpenAI を用いたニュース NLP / レジーム判定（任意）
- 監視コンポーネントによる自動的な Kill Switch（停止フラグ）発動

---

## 機能一覧

- 環境設定ウィザード（.env 自動生成）: python -m kabusys.config_setup
- 設定検証ツール（.env, config/*.yaml のチェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（発注エンジン）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは data/paper_trading.db に記録
- Monitoring 起動スクリプト（SystemMonitor のポーリング）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視用 DB 層（SQLite）: 監視ログ / トレードログ / ポジション / リスクログ / ダッシュボード
- RiskMonitor / KillSwitch / MonitoringEngine による自動監視とアラート連携
- Portfolio モジュール
  - 候補選定（スコア順）/ 等金額配分・スコア加重配分
  - セクターキャップ適用、レジーム乗数計算
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research（DuckDB を利用したファクター計算）
  - モメンタム、ボラティリティ、バリューなどのファクター算出
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリー
- AI モジュール（OpenAI）
  - ニュース NLP（銘柄ごとのセンチメントスコアを ai_scores テーブルへ書込み）
  - レジーム判定（ETF MA200 とマクロセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

前提:
- Python 3.9+（DuckDB・psutil 等が動作するバージョン）
- 任意の仮想環境推奨（venv / conda 等）

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 必須: duckdb, psutil
   - AI 機能を使う場合: openai
   - config YAML 検証を使う場合: PyYAML
   例:
   - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt）

4. データ / ログ ディレクトリ作成
   - data/ と logs/ は起動時に自動作成されますが、手動で作る場合:
     - mkdir -p data logs

5. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live） デフォルト: development
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL（秒、run_monitoring で読み込むことも可能）

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで終了コード 1 を返します。

注意:
- KABUSYS_ENV=paper_trading の場合、発注はモック実装（DB：data/paper_trading.db）に記録され、実口座とは分離されます。
- 本番（live）運用時は設定値を十分に確認してください（validate_config に本番向けの追加警告あり）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - 起動中は data/execution.pid（デフォルト）に PID を書きます。
  - KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH に書き込みます。

- Monitoring（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を作成するとループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ログ:
- デフォルトで logs/<app_name>.log（日次ローテーション、30日保持）と stdout に出力されます。
- ログディレクトリは環境変数 LOG_DIR または setup_logging() の引数で変更可能。

監視・停止フラグ:
- data/kill.flag: KillSwitch によって書き込まれる停止フラグ（ExecutionEngine に停止シグナル）
- data/stop_requested.flag: 起動スクリプト側の外部停止フラグ（起動中の run_* スクリプトが読んで終了）

AI 機能:
- OpenAI を使う API キーは OPENAI_API_KEY 環境変数で指定
- news_nlp / regime_detector は OpenAI 呼び出しを行うため、API 利用料・レート制限に注意

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールとその用途（抜粋）です。

- kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数・.env 自動ロード、Settings クラス（各種設定プロパティ）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証ツール
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- kabusys/utils/
  - logging_setup.py — 共通ログ設定（stdout + 日次ローテートファイル）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- kabusys/monitoring/
  - monitoring_db.py — SQLite 監視 DB 層（テーブル作成・CRUD ヘルパ）
  - system_monitor.py — システム状態監視（CPU/メモリ/ディスク/データ鮮度）
  - trade_monitor.py — （注文滞留・約定異常検出など — リポジトリ内に存在）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック（Execution 停止判定）
  - monitoring_engine.py — 複数モニタを束ねて定周期実行
  - alert_manager.py — （アラート配信のラッパー — リポジトリ内に存在）

- kabusys/execution/
  - execution_engine.py — 発注エンジン本体（EngineConfig / run_session 等）
  - broker_factory.py — 実ブローカ / MockBroker の生成
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・リスク管理周り

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数算出（単元丸め / aggregate cap）
  - risk_adjustment.py — セクター上限・レジーム乗数
  - __init__.py — 主要関数の再エクスポート

- kabusys/research/
  - factor_research.py — momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - __init__.py — 主要 API 集約

- kabusys/ai/
  - news_nlp.py — ニュース記事の LLM によるセンチメント評価と ai_scores 書込み
  - regime_detector.py — MA200 とマクロセンチメントを合成して market_regime を計算

- kabusys/tools/
  - paper_verification_report.py — Paper Trading データ検証レポート生成

- その他
  - data/ — 実行時に使用する SQLite ファイル、フラグファイルなど（起動時に生成される）
  - logs/ — ログファイル（デフォルト）

---

## 実運用時の注意点

- 本番環境（KABUSYS_ENV=live）では .env の内容を厳密に確認してください。validate_config の警告や未設定変数に注意。
- process_priority の設定や nice 値変更は権限・OS に依存します。設定できない場合は警告が出力されます。
- OpenAI を使う処理は API 失敗時にフォールバック（ゼロスコアやスキップ）する設計ですが、頻繁なエラーは運用面での影響があります。API キー管理・レート管理を行ってください。
- Paper Trading と Live DB は分離されています（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH）。Data を誤って混在させないよう注意してください。
- kill.flag / stop_requested.flag を用いることで外部からエンジンを安全に停止できます。運用時の手順を運用ドキュメントに定義しておくことを推奨します。

---

以上がこのコードベースの概要・セットアップ・使い方・構成です。追加で README に含めたい情報（例: 詳細な運用フロー、データベーススキーマ図、サンプル .env）や、特定モジュールの API ドキュメント化が必要であれば教えてください。
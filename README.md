# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
このドキュメントはローカル実行・開発・運用のための概要・セットアップ・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主要な責務は次のとおりです。

- 市場データ / ファクター計算（research）
- ポートフォリオ構築（portfolio）
- 注文実行エンジン（execution） — 実口座 / ペーパートレード切替可
- モニタリング・リスク監視（monitoring）
- ニュース NLP / レジーム判定（AI モジュール）
- 運用支援ツール（設定ウィザード、設定検証、検証レポートなど）

設計方針の一例：
- DuckDB を分析用 DB として使用、SQLite を監視・注文履歴用 DB として使用
- 本番 DB とペーパートレード DB を分離
- 設定は .env ファイル（または環境変数）で管理
- 監視やエンジン停止はフラグファイル（data/kill.flag 等）で制御

---

## 主な機能一覧

- 実行スクリプト
  - run_execution.py: ExecutionEngine（発注エンジン）を起動
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）

- 設定管理 / ツール
  - config_setup.py: 対話式 .env ウィザード（初期設定作成）
  - validate_config.py: .env と config/*.yaml の事前検証 CLI

- モニタリング
  - system_monitor.py: CPU/メモリ/Disk、データ鮮度、Execution プロセスの監視
  - trade_monitor.py / risk_monitor.py: 注文滞留・約定異常・ドローダウン・ポジション上限監視
  - monitoring_engine.py: 各モニタを束ねてポーリング、アラート発行・Kill Switch 制御
  - monitoring_db.py: 監視ログの永続化（SQLite）

- ポートフォリオ構築（純粋関数）
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py

- リサーチ
  - factor_research.py / feature_exploration.py: DuckDB 上でファクター・将来リターン・IC 等を計算

- AI（OpenAI）
  - news_nlp.py: ニュース記事を LLM でスコアリングして ai_scores に書き込み
  - regime_detector.py: マクロ + ETF MA200 に基づく市場レジーム判定（LLM 併用）

- 運用ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテーション）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定

---

## 前提・依存

推奨環境（例）
- Python 3.9+
- pip install で以下を導入
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml の検証に利用）
  - その他プロジェクトで必要なライブラリ

（実際の requirements.txt は本リポジトリに合わせてください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンする
   - git clone <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は少なくとも duckdb, psutil, openai をインストール）

4. .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabu API / DB パス等の入力を促します

   自動ロードに関する補足:
   - 起動時、プロジェクトルートに .env/.env.local があれば自動で環境変数へ読み込まれます
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定の検証
   - python -m kabusys.validate_config
   - 問題があれば修正してください
   - --strict オプションをつけると警告もエラー扱いになります

6. データディレクトリの準備
   - デフォルトの SQLite / DuckDB は data/ 以下を参照します。必要に応じて作成してください。
   - ログは logs/ に出力されます（LOG_DIR / LOG_LEVEL 環境変数で変更可）。

---

## 使い方（主要コマンド例）

- 実行エンジンを起動（デフォルト: .env の KABUSYS_ENV に従う）
  - python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV=paper_trading を設定して起動すると MockBroker を使用し data/paper_trading.db に記録されます（本番 DB と分離）
  - ExecutionEngine は停止フラグ（data/stop_requested.flag や data/kill.flag など）を検知して停止できます
  - 実行時に data/execution.pid を生成します

- 監視ループを起動（デフォルト 60 秒間隔）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  補足:
  - 監視は常に本番用 sqlite_path を参照します（KABUSYS_ENV の値にかかわらず）
  - 停止は data/stop_requested.flag を作成することで行えます

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB パスを指定できます

- AI 関連（OpenAI）
  - news_nlp.score_news / regime_detector.score_regime を使用するには OPENAI_API_KEY を設定してください
  - 例: export OPENAI_API_KEY=sk-...（または .env に設定）

---

## よく使う環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB パス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite、デフォルト: data/paper_trading.db）
- ログ
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- 監視・制御
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒。デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START（本番での自動 kill flag クリア: 0 推奨）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（.env の自動ロードを無効化）
- OpenAI
  - OPENAI_API_KEY

---

## 運用メモ / 注意点

- ペーパートレードは本番 DB と分離されています。KABUSYS_ENV=paper_trading を使用してください。
- monitoring は本番 sqlite_path（SQLITE_PATH）を使用してログを取ります。run_monitoring は環境にかかわらず本番 sqlite_path を参照する実装になっています（意図的な仕様）。
- Kill Switch: risk 条件を満たすと data/kill.flag が書かれ、ExecutionEngine に停止シグナルを送ります。clear は KillSwitch.clear() を使用できます。
- ロギング: setup_logging は stdout とファイル（logs/<app_name>.log 日次ローテーション）を設定します。ログディレクトリが作れない場合はファイル出力をスキップして stdout のみになります。
- OpenAI を利用する処理はネットワークエラー・429 等に対してリトライロジックを実装していますが、API キーやコストに注意してください。

---

## ディレクトリ構成（主要ファイル・ディレクトリ）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — （注）滞留注文等の監視（実装ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 制御（flag ファイル）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信（LINE 等、実装による）
  - execution/  — ExecutionEngine 関連（OrderManager, RiskManager, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/ (上記)
  - tools/
    - paper_verification_report.py
  - data/ (ランタイムで使用するファイル: DB, pid, flags 等)
    - stop_requested.flag (監視・エンジン停止用)
    - execution.pid (ExecutionEngine PID)
    - kill.flag (Kill Switch)
  - logs/ (runtime logs、デフォルト)

---

## 開発 / 貢献

- コーディングスタイルやテストはプロジェクトの方針に従ってください。  
- データベーススキーマの変更は monitoring_db.init_monitoring_db などにマイグレーションロジックを追加してください（既存実装に倣う）。

---

README はここまでです。必要であれば以下を補足できます：
- より詳細な起動例（systemd / supervisor / docker-compose のサンプル）
- config/*.yaml の仕様やテンプレート
- 各モジュールの API 仕様（関数引数・戻り値）一覧

どの情報を追加しますか？
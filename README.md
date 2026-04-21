# KabuSys — 日本株自動売買システム

この README はコードベースから生成された概要ドキュメントです。日本株の自動売買・バックテスト・リサーチ・監視を目的としたモジュール群を含みます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのプロジェクト構成を模したライブラリ／アプリケーション群です。主な目的は以下のとおりです。

- 売買シグナル生成・ポートフォリオ構築・ポジションサイジング
- 発注管理（ExecutionEngine）とリスク管理
- システム稼働監視・アラート・Kill Switch
- DuckDB／SQLite を用いたデータ管理と解析
- ニュースの NLP によるセンチメント評価やレジーム判定（OpenAI）
- ペーパートレード検証用のツール群

設計方針として、外部 API 呼び出し（実取引・OpenAI など）は設定に応じて分離し、フェイルセーフ（API失敗時のフォールバック）を持たせています。また、.env 自動読み込みや CLI ウィザードで初期設定が可能です。

---

## 主な機能一覧

- Execution
  - ExecutionEngine：発注エンジン起動スクリプト（run_execution.py）
  - BrokerClientFactory：本番 or ペーパートレード用クライアント切替
  - OrderManager / OrderRepository / Reconciler / RiskManager 等
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor：発注ログの監視（滞留注文／約定異常など）
  - RiskMonitor：ドローダウン、ポジション上限監視
  - MonitoringEngine：各監視のポーリング統括（run_monitoring.py）
  - KillSwitch：条件により Execution を停止するフラグ生成
  - MonitoringDB：SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算（等分・スコア加重）
  - セクター制限（apply_sector_cap）、レジームによる乗数（calc_regime_multiplier）
  - ポジションサイズ計算（risk_based / equal / score）
- Research（リサーチ）
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, 統計サマリ）
  - DuckDB 経由の SQL＋Python 実装
- AI（OpenAI 連携）
  - news_nlp.score_news：ニュース記事を集約してセンチメントを AI によって算出し ai_scores に書き込み
  - regime_detector.score_regime：MA とマクロニュース（LLM）を併せて市場レジーム判定
- ツール
  - config_setup.py：対話式 .env 作成ウィザード
  - validate_config.py：起動前の設定検証 CLI
  - tools/paper_verification_report.py：ペーパートレード DB を基に検証レポートを出力
- ユーティリティ
  - logging_setup.py：統一的なログ設定（コンソール + 日次ローテーションファイル）
  - process_priority.py：プラットフォーム差分を吸収したプロセス優先度 / CPU affinity 設定

---

## 前提条件（例）

- Python 3.9+
- duckdb
- psutil
- openai（AI機能を使う場合）
- PyYAML（validate_config の YAML 検証を有効にする場合）
- （任意）その他プロジェクトで定義された依存パッケージ

requirements.txt がある場合はそちらからインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - git clone ... またはプロジェクト配布方法に従う

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ない場合は最低限以下を入れてください:
     - pip install duckdb psutil openai

4. .env 初期設定
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参照して .env を作成
   - 自動ロードはデフォルトで有効（プロジェクトルートにある .env / .env.local を読み込み）
     - 無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題があればエラーメッセージに従って修正
   - --strict を付けると警告も失敗扱いになります

6. DB ディレクトリ作成
   - デフォルトで data/ に SQLite / DuckDB ファイルを格納します。必要に応じてディレクトリを作成してください。
   - monitoring 起動時に必要なテーブルは自動作成されます（init_monitoring_db）

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV（development | paper_trading | live） — 実行環境
  - paper_trading 時は MockBrokerClient を使用し、データは data/paper_trading.db に記録されます
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（ログ出力先ディレクトリ）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番環境での自動クリア制御）

注意: .env は秘密情報を含むため、絶対に Git にコミットしないでください。

---

## 実行例 / 使い方

- ExecutionEngine の起動（実行／ペーパー）
  - KABUSYS_ENV が paper_trading のときは Mock Broker が使われ、ペーパー用 DB に記録されます。
  - 実行:
    - python -m kabusys.run_execution
  - 停止フラグ:
    - プロジェクトルート/data/stop_requested.flag を作成すると起動中のループは安全に停止します。
    - Kill Switch が発動すると data/kill.flag が作成され、次回 Execution 起動時は起動しない仕組みがあります。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視ログは本番 DB に記録）。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式で作成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると失敗（exit 1）になります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db オプションで指定可能。

- AI 機能（プログラム呼び出し例）
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - どちらも DuckDB 接続と target_date、必要な場合は api_key を渡して呼び出します。

---

## 停止・Kill / フラグファイル

- stop_requested.flag
  - run_execution.py / run_monitoring.py が参照する停止フラグ（デーモン的に動作中の外部停止指示）
  - 作成するとループは安全に終了します。

- kill.flag
  - KillSwitch の評価により作成される Execution 停止フラグ
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）

---

## ロギング

- 共通ロギングユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）を設定
  - デフォルトログディレクトリ: logs/
  - LOG_DIR 環境変数で変更可

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py — .env 対話式ウィザード（CLI）
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - execution/ — 発注・実行関連（BrokerFactory, ExecutionEngine, OrderManager 等）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py — システム状態監視
    - trade_monitor.py — 発注ログ監視（省略）
    - risk_monitor.py — ドローダウン・ポジション監視
    - monitoring_engine.py — 監視の統括
    - kill_switch.py — 停止フラグ生成
    - alert_manager.py — 通知管理（LINE など、省略）
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/（実行時生成・DB 格納）
  - logs/（ログ出力先、デフォルト）

---

## 開発メモ / 注意点

- .env を利用する設計なので、本番シークレットは適切に管理してください。
- DuckDB / SQLite のパスは環境変数で指定できます。monitoring は環境に関係なく SQLITE_PATH を参照します（監視ログは隔離すべき、設定で調整してください）。
- OpenAI を利用する機能は API 呼び出しの失敗時に安全なフォールバック（例: スコア 0.0）を実装していますが、API キー管理とレート制限には注意してください。
- run_execution と run_monitoring は stop_requested.flag を見て安全に停止する仕組みです。運用時はこのファイルの有無で起動／停止を制御してください。
- validate_config.py で config/*.yaml の存在や YAML パースをチェックします（PyYAML が必要）。config ファイルは scripts/generate_config.py 等で生成される想定です（環境により異なります）。

---

この README はコードベースの主要ポイントを抜粋してまとめたものです。詳細は各モジュールの docstring やソースを参照してください。必要であれば、README に使い方のコマンド例やシステムアーキテクチャ図、環境変数完全一覧などを追加します。どの情報を拡張したいか教えてください。
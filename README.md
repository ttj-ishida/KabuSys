# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買 / 研究支援フレームワークです。本リポジトリは実行エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI）などのモジュールを含みます。

以下はコードベース（src/kabusys）に基づく README です。

---

## プロジェクト概要

- 日本株の自動売買システムのコアライブラリ群。
- 実行エンジン（ExecutionEngine）と監視（Monitoring）を分離し、監視側から Kill Switch による停止を行える設計。
- DuckDB / SQLite をデータストアとして用い、研究用ファクター計算やポートフォリオ構築関数を提供。
- OpenAI を使ったニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）を実装（API キー必須）。
- Paper Trading（ペーパートレード）用に本番 DB と分離されたデータパスと Mock ブローカをサポート。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により挙動を切替）
  - run_monitoring.py: SystemMonitor のポーリングループを実行（MONITOR_POLL_INTERVAL で調整可能）
- 設定管理
  - config.py: 環境変数 / .env 自動読み込みと Settings クラス
  - config_setup.py: .env の対話的生成ウィザード
  - validate_config.py: 起動前の設定検証 CLI
- 監視・アラート
  - monitoring/*: system/trade/risk モニタ、kill switch、monitoring engine、監視 DB 永続化
  - monitoring_db.py: SQLite によるテーブル作成・永続化 API
- 実行
  - execution/*: Broker factory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等（起動スクリプトから組立）
- ポートフォリオ構築（純粋関数）
  - portfolio/*: 候補選定、重み計算、ポジションサイズ、セクター制約、レジーム乗数
- 研究用モジュール
  - research/*: ファクター計算（momentum/value/volatility）、特徴量探索、IC 計算等（DuckDB 経由）
- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事をまとめて LLM に渡し銘柄単位のセンチメントを ai_scores に書込む
  - ai/regime_detector.py: ETF の MA とマクロニュース（LLM）による日次レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を集計して PASS/FAIL レポートを出力

---

## 依存関係（主要）

少なくとも以下が必要です（バージョンはプロジェクト要件に合わせて調整してください）:

- Python 3.9+
- duckdb
- psutil
- openai
- (任意) PyYAML — validate_config の YAML 検証に使用

例（pip）:
pip install duckdb psutil openai PyYAML

※ requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動。

2. 仮想環境作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール:
   pip install duckdb psutil openai PyYAML

4. 環境変数設定 (.env)
   - 対話ウィザードで作成:
     python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参照してください）。主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - LOG_DIR（ログ出力先、デフォルト: logs/）
     - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）

5. 設定検証（推奨）:
   python -m kabusys.validate_config
   厳格モード:
   python -m kabusys.validate_config --strict

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）:
  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録して本番 DB と分離します。
  - ExecutionEngine は data/execution.pid に PID を書きます。
  - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。

- Monitoring を起動（ポーリング）:
  python -m kabusys.run_monitoring

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用して monitoring DB を初期化します。
  - 停止は data/stop_requested.flag の作成でポーリングループが検知して終了します。

- .env の対話作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  （--strict を付けると警告も失敗扱い）

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

## 停止・Kill 操作

- graceful stop（外部）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して停止します。

- Kill Switch（監視側からの停止要求）:
  - KillSwitch は閾値（ドローダウン超過、ポジション上限等）に達した場合に data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に Settings.kill_flag_clear_on_start を確認して kill.flag を自動クリアするか決めます（デフォルトはクリアしない。本番では 0 推奨）。

---

## ログ

- ログ構成は kabusys.utils.logging_setup.setup_logging により統一されます。
- デフォルトログディレクトリ: logs/
- アプリ別ログ:
  - logs/execution.log
  - logs/monitoring.log
  - （その他 app_name を渡して作成可能）
- 環境変数:
  - LOG_LEVEL（例: INFO）
  - LOG_DIR（例: /var/log/kabusys）

---

## 開発メモ / 注意点

- .env 自動読み込み:
  - 起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込みします（.env.local は上書き）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。

- AI 機能:
  - OpenAI API を利用するモジュール（ai/news_nlp.py, ai/regime_detector.py）は OPENAI_API_KEY を必要とします。
  - API 呼び出しはリトライ・バックオフ処理を実装しているものの、API キー設定と料金・利用制限に注意してください。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db はテーブル作成と簡易マイグレーション（カラム追加）を行います。既存 DB の互換性に配慮しています。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- __version__ = "0.1.0"

- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- validate_config.py         — 設定検証 CLI
- config_setup.py            — .env 対話式ウィザード
- config.py                  — Settings（環境変数読み取り・自動 .env ロード）

- utils/
  - logging_setup.py         — ログ設定ユーティリティ
  - process_priority.py      — プロセス優先度設定ユーティリティ
  - __init__.py

- monitoring/
  - monitoring_db.py         — SQLite テーブル作成・永続化 API
  - system_monitor.py        — システム状態／データ鮮度監視
  - trade_monitor.py         — 発注ログ／滞留注文監視（存在）
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — kill.flag の書き込み・管理
  - monitoring_engine.py     — 各モニタを束ねるエンジン
  - alert_manager.py         — アラート送信管理（存在）

- execution/
  - execution_engine.py      — 実行エンジンコア（EngineConfig 等）
  - broker_factory.py        — BrokerClientFactory（Mock / Real 切替）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - portfolio_builder.py     — 候補選定・重み計算
  - position_sizing.py       — 発注株数計算
  - risk_adjustment.py       — セクター上限・レジーム乗数
  - __init__.py

- research/
  - factor_research.py       — momentum/value/volatility 等
  - feature_exploration.py   — forward returns, IC, summary
  - __init__.py

- ai/
  - news_nlp.py              — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
  - regime_detector.py       — 市場レジーム判定（MA + macro sentiment）
  - __init__.py

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
  - __init__.py

（上記以外に data/, logs/ 等のランタイムディレクトリを想定）

---

## よくある質問 / トラブルシュート

- Q: .env を読み込まない／設定が反映されない
  - A: KABUSYS_DISABLE_AUTO_ENV_LOAD を確認。プロジェクトルートが .git または pyproject.toml によって特定されない場合、自動ロードはスキップされます。config_setup で .env を作成してください。

- Q: OpenAI 呼び出しで失敗するとき
  - A: OPENAI_API_KEY の設定、ネットワーク、API 利用制限を確認。モジュール側はリトライを実装していますが、最終的に失敗すると該当処理はスキップ（フェイルセーフ）されます。

- Q: ログファイルが作成されない
  - A: LOG_DIR の書込権限とディレクトリ作成の成否を確認。logging_setup は作成に失敗した場合はコンソール（stdout）のみで継続します。

---

## 参考コマンドまとめ

- 環境作成・依存インストール:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML

- .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

---

この README はソースコードのヘッダコメント・関数ドキュメントに基づいてまとめています。実際の運用や機能拡張にあたっては各モジュールの実装詳細（引数・戻り値・例外など）を参照してください。質問や追記の希望があれば教えてください。
# KabuSys

日本株向けの自動売買システム骨組み。信号生成・ポートフォリオ構築・発注管理・監視・リサーチ・AIによるニュースセンチメント評価などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような役割を担うコンポーネント群で構成されています。

- 発注実行エンジン（ExecutionEngine）
  - 実際のブローカー接続またはペーパートレード（モック）で注文を送信・管理
- 監視コンポーネント（Monitoring）
  - システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期チェック
  - 異常時に kill.flag を書き込む Kill Switch 機能
- ポートフォリオ構築（Portfolio）
  - 銘柄選定、重み計算、ポジションサイズ決定、セクター制限、レジーム乗数
- リサーチ（Research）
  - ファクター計算、特徴量探索、IC 計算
- AI モジュール（AI）
  - OpenAI を用いたニュースの NLP スコアリング、市場レジーム判定
- ユーティリティ
  - 環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定など

設計方針として、本番 DB とペーパートレード DB を分離し、ルックアヘッドバイアスを避けるため日付参照を直接呼ばない等の安全策が多く組み込まれています。

---

## 主な機能一覧

- 実行
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて実ブローカー / MockBroker を切替）
  - 発注ログを SQLite（monitoring DB または paper_trading DB）に保存
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループを実行
  - system_status / trade_logs / risk_logs / dashboard / positions の管理
  - Kill Switch により異常時に ExecutionEngine を安全停止
- 環境管理
  - config_setup.py: 対話式 .env ウィザード（.env の初期作成・更新）
  - validate_config.py: .env と config/*.yaml の検証 CLI
- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析し検証レポートを出力
- リサーチ & AI
  - research: momentum/volatility/value 等のファクター計算、IC 等の統計ツール
  - ai.news_nlp / ai.regime_detector: OpenAI を使ったニュースセンチメント / レジーム判定

---

## 必要条件（例）

- Python 3.9+
- pip で必要パッケージをインストール（duckdb, psutil, openai, PyYAML など）

（requirements.txt はこのリポジトリに含まれていないため、実行環境に合わせて必要パッケージを追加してください。）

---

## セットアップ手順

1. リポジトリをクローン／展開し、仮想環境を作成して有効化します。

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール（例）:

   pip install duckdb psutil openai PyYAML

   ※ 実際に使用する機能に応じてパッケージを追加してください。

3. 対話式ウィザードで .env を作成（推奨）:

   python -m kabusys.config_setup

   このウィザードにより J-Quants トークンや kabu API パスワード等を .env に保存できます。
   .env は絶対に Git にコミットしないでください。

4. 設定検証:

   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict

5. 必要に応じてデータディレクトリを作成（多くは自動作成されます）:

   mkdir -p data logs

---

## 環境変数（代表的なもの）

（.env に設定する主要なキー）

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- KABUSYS_ENV: 実行環境（development | paper_trading | live。デフォルト: development）
  - paper_trading のとき、Execution は MockBrokerClient を使い data/paper_trading.db を使用
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBroker 挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0|1）

その他詳細は kabusys.config.Settings に実装されています。

---

## 使い方（代表コマンド）

- 環境設定ウィザード（.env 作成）

  python -m kabusys.config_setup

- 設定検証

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動（常駐プロセスを想定）

  python -m kabusys.run_execution

  注意:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行プロセスは PID ファイル（data/execution.pid デフォルト）を作成します。
  - 起動時にプロセス優先度を high に設定しようとします（権限により失敗する場合あり）。

- Monitoring を起動（ポーリング）

  python -m kabusys.run_monitoring

  オプション（環境変数）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # ポーリング間隔を上書き
  - 監視は環境にかかわらず（KABUSYS_ENV に依存せず）本番の SQLITE_PATH を使用します。

  停止方法:
  - data/stop_requested.flag を作成するとループが検知して終了します（外部スクリプトや手動で作成）。
  - kill.flag は Kill Switch によって ExecutionEngine を停止させるために用いられます（path は Settings.kill_flag_path）。

- Paper Trading 検証レポート

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能（指定がなければ環境変数 PAPER_TRADING_SQLITE_PATH を参照）。

- AI 関連（ニューススコア / レジーム判定）
  - OPENAI_API_KEY を設定して使用します。API 呼び出しはネットワークエラー等に対してリトライやフェイルセーフを備えています。
  - 必要に応じてモジュール内の関数をスクリプトやジョブから呼び出してください（例: kabusys.ai.score_news）。

---

## 運用上の注意

- 本番環境で KABUSYS_ENV=live を使う際は .env の設定（特に通知・kill flag 関連）を慎重に確認してください。validate_config は本番向けチェックを行います。
- .env は絶対に Git へコミットしないでください。
- ロギングはログディレクトリ（デフォルト logs/）に日次ローテーションで保存されます。ログディレクトリの作成に失敗した場合はコンソール出力のみで動作します。
- Execution/Monitoring 起動スクリプトはプロセス優先度設定や PID ファイルの管理を行いますが、権限によっては設定が無視されることがあります。
- AI モジュールは OPENAI_API_KEY が未設定だと動作しないか、呼び出し時に例外を送出します（関数により挙動は異なります）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理
- config_setup.py                — .env 対話ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

subpackages:
- monitoring/
  - monitoring_db.py             — SQLite 永続化層（テーブル定義・CRUD）
  - system_monitor.py            — システム状態 / データ鮮度監視
  - trade_monitor.py             — （注文）監視ロジック
  - risk_monitor.py              — ドローダウン / ポジション上限監視
  - kill_switch.py               — kill.flag 書き込みロジック
  - monitoring_engine.py         — 各 Monitor を束ねるエンジン
  - alert_manager.py             — （通知）アラート送信ロジック（実装想定）
- execution/
  - execution_engine.py          — ExecutionEngine（起動ロジック）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py           — 市場レジーム判定（OpenAI + ETF MA）
- tools/
  - paper_verification_report.py — Paper Trading レポート生成
- utils/
  - logging_setup.py             — ログ初期化ユーティリティ
  - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ

その他:
- data/                          — デフォルトの DB / フラグ / PID を格納（runtime）
- logs/                          — ログ出力先（デフォルト）

---

## 開発者向けメモ

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行われます。テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB は分析用途に使われ、research や ai のデータ参照に用います。SQLite は軽量なトランザクション・ログ用途（監視・注文ログ）に用いられます。
- AI モジュールの API 呼び出しは外部ライブラリ（openai）経由で行われます。ユニットテスト時は内部の _call_openai_api を patch して外部依存を取り除けるように設計されています。
- run_execution/run_monitoring は stop_requested.flag（data/stop_requested.flag）による外部停止トリガを監視します。外部管理ツール（systemd / cron / supervisor 等）と併用してください。

---

README はここまでです。必要であれば、README に含めるインストール用 requirements.txt の例や systemd サービスファイルのテンプレート、より詳細な構成図・ER 図・API 仕様なども作成します。どれを追加しますか？
README — KabuSys
===============

概要
---
KabuSys は日本株向けの自動売買／リサーチ／監視を目的とした軽量な Python コードベースです。
主な目的は次のとおりです。

- 市場データ（DuckDB）を使ったファクター計算・リサーチ
- 発注エンジン（ExecutionEngine）による発注・約定管理（本番 / ペーパートレード対応）
- 監視サブシステム（Monitoring）によるシステム健常性・リスク監視と Kill Switch
- OpenAI を利用したニュース NLP（センチメント）やレジーム判定の補助機能
- ペーパートレードの検証レポート作成ツール

機能一覧
--------
- 環境設定ウィザード: .env の対話式生成（kabusys.config_setup）
- 設定検証 CLI: .env と config/*.yaml の事前チェック（kabusys.validate_config）
- 実行エンジン起動スクリプト: run_execution.py（本番 / paper_trading 切替）
  - KABUSYS_ENV=paper_trading のときは MockBroker を用い、本番 DB と分離して data/paper_trading.db を使用
- 監視ループ起動スクリプト: run_monitoring.py（SystemMonitor を定期ポーリング）
  - MONITOR_POLL_INTERVAL でインターバル変更可（デフォルト 60 秒）
- 監視データの永続化: SQLite ベース（monitoring_db）
- リスク監視（ドローダウン・ポジション上限）と Kill Switch（data/kill.flag）
- ロギングユーティリティ: コンソール + 日次ローテートファイル（logs/）
- ポートフォリオ構築: 候補選定、重み計算、リスク調整、ポジションサイズ計算（pure functions）
- リサーチ: モメンタム・ボラティリティ・バリューなどのファクター計算（DuckDB 前提）
- AI 関連:
  - ニュースを LLM（OpenAI）でセンチメント化し ai_scores へ保存
  - レジーム判定モジュール（MA200 とマクロニュースの合成）
- ペーパートレード検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提:
- Python 3.10+（typing, match 等が必要ないが型アノテーションを有効にするため新しめ推奨）
- SQLite（Python 標準の sqlite3 を使用）
- DuckDB（duckdb Python パッケージ）
- psutil（プロセス優先度・CPU 情報）
- OpenAI SDK（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行いたい場合。任意）

推奨インストール例:
1. 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # Windows は .venv\Scripts\activate

2. 必要パッケージをインストール
   pip install duckdb psutil openai PyYAML

（プロダクションで requirements.txt を用意する場合は上記パッケージを列挙してください）

環境変数 / .env
- プロジェクトルートに .env を置くと自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要な環境変数（デフォルトや用途）:
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live) — default: development
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL: kabu API ベース URL（default: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH: monitoring SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレード時の約定モード (instant|partial|never|reject) — default: instant
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...） — default: INFO
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1） — 本番では 0 推奨

.env を対話式で作る:
- python -m kabusys.config_setup
  対話ウィザードで .env を生成 / 更新します。

設定検証:
- python -m kabusys.validate_config
  --strict を付けると警告を FAIL 扱いにします。

使い方
------
主要なエントリポイントと実行例:

- 監視ループを起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可。
  - run_monitoring は Monitoring 用の SQLite（settings.sqlite_path）と DuckDB を開き SystemMonitor を繰り返し実行します。
  - data/stop_requested.flag を作成するとループは終了します。

- 実行エンジンを起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 停止は data/stop_requested.flag の作成やプロセスの kill により行います。

- .env の対話作成
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定できます。

AI 機能（OpenAI）
- ニューススコアリングやレジーム判定は OPENAI_API_KEY が必要です。
- API 呼び出しはリトライ・バックオフが実装されており、失敗時はフェイルセーフで処理を継続します。

ログ
- デフォルトでコンソール（stdout）と logs/<app_name>.log（日時ローテーション）に出力します。
- LOG_DIR 環境変数や setup_logging の引数で変更可能。
- 既存ハンドラは再設定時にクリアされ二重出力を防止します。

停止フラグ / Kill Switch
- data/stop_requested.flag: run_monitoring/run_execution が監視する停止フラグ
- data/kill.flag: KillSwitch によって作成される ExecutionEngine 停止トリガ（リスク事象発生時）

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/設定管理（.env 自動ロード含む）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

subpackages:
- utils/
  - logging_setup.py       — 統一的なログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（テーブル初期化 / CRUD）
  - system_monitor.py      — システム稼働率・データ鮮度監視
  - trade_monitor.py       — （発注監視・滞留注文検出等）※実装ファイルあり
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — Kill Switch 書き込みユーティリティ
  - monitoring_engine.py   — 各 Monitor を束ねるループ
  - alert_manager.py       — （通知管理、LINE 等）※実装ファイルあり
- execution/
  - execution_engine.py    — ExecutionEngine 実装（起動 / セッション管理）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py   — 候補選定 / 重み計算
  - position_sizing.py     — 発注株数計算・集計キャップ処理
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — モメンタム/ボラ/バリュー計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- data/                    — 実行時 DB・フラグファイル等（data/*）
- ai/
  - news_nlp.py            — ニュースセンチメント生成（OpenAI）
  - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
- tools/
  - paper_verification_report.py  — ペーパートレード検証レポート生成ツール

注意事項 / 運用上のポイント
-------------------------
- KABUSYS_ENV=live で起動する際は .env の値を慎重に確認してください（validate_config は警告を出します）。
- .env は絶対にリポジトリへコミットしないでください（機密情報が含まれる）。
- run_execution/run_monitoring は process priority を "high" に設定しようとしますが、権限不足で失敗する場合は警告が出ます。
- DuckDB / SQLite のパスは環境変数で簡単に切り替え可能です（ペーパーと本番を分離することを推奨）。
- OpenAI を使う機能は API 利用料とレート制限に注意してください。

貢献
----
- バグ修正や改善提案は Pull Request を歓迎します。
- 新しい機能を追加する際はユニットテスト（可能な限り）を追加してください。

問い合わせ
----------
- プロジェクト内のコードコメント・ドキュメントを参照してください。さらに質問があれば実装者にお問い合わせください。

以上。必要であれば README に具体的な .env.example のテンプレートや requirements.txt のサンプルを追加できます。どの情報を追記しましょうか？
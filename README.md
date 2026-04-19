KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部実装です。
本ドキュメントはコードベース（src/kabusys 以下）を対象に、導入・起動方法、
主要機能やディレクトリ構成を日本語でまとめた README です。

主なポイント
- 実行スクリプト:
  - 実トレード / ペーパートレード実行エンジン: python -m kabusys.run_execution
  - 監視ループ（System / Trade / Risk の定期チェック）: python -m kabusys.run_monitoring
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- 設定は .env（および .env.local）で管理。自動ロード機能あり（無効化可）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して data/paper_trading.db を使用。
- OpenAI を使ったニュース NLP / レジーム検出など AI 機能を含む（OPENAI_API_KEY 必須）。

プロジェクト概要
---------------
KabuSys は以下の要素で構成された自動売買基盤の一部です（リサーチ→ポートフォリオ→発注→監視の流れ）:
- データ処理・ファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ExecutionEngine（ブローカークライアント経由で発注。paper_trading モードあり）
- 監視（システム・発注・リスク監視）と Kill Switch による自動停止
- AI モジュール（ニュースセンチメント、レジーム検出） — OpenAI を呼び出す
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

機能一覧
---------
- run_execution:
  - 実行エンジンの起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用）
  - paper_trading 時は data/paper_trading.db を使用して本番 DB と完全分離
  - 優先度設定（process priority を high に設定）
  - stop フラグ（data/stop_requested.flag）の検出で安全停止
- run_monitoring:
  - SystemMonitor を定期ポーリングして system_status / risk_logs / trade_logs 等へ記録
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を調整（デフォルト 60 秒）
  - stop フラグで停止
- monitoring:
  - SystemMonitor: CPU/MEM/DISK/プロセス生存確認・データ鮮度チェック
  - TradeMonitor: 発注ログの滞留・約定異常検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine 停止をトリガー
  - AlertManager（通知機能）経由で警告/アラート送信（LINE などを設定可能）
- portfolio:
  - 候補選定・重み計算（等金額 / スコア加重）
  - セクターキャップ適用・レジーム乗数
  - ポジションサイズ計算（lot 単位切り上げ、aggregate cap のスケーリング）
- research:
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（forward returns、IC、統計サマリ）
- ai:
  - news_nlp: raw_news を集約して OpenAI でセンチメント評価、ai_scores へ保存
  - regime_detector: ETF (1321) の MA とマクロニュースで日次レジーム判定
- ツール:
  - config_setup: 対話式に .env を作成・更新
  - validate_config: .env と config/*.yaml の簡易検証（--strict オプションあり）
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート生成

セットアップ手順
----------------
前提:
- Python 3.10 以上（型アノテーション（X | Y）や最新パッケージに対応）
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML （config/*.yaml の検証用、任意）
  - （その他：sqlite3 は標準ライブラリ）

例（pip）:
1) 仮想環境作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows

2) パッケージインストール（必要に応じて requirements.txt を用意してください）
   pip install duckdb psutil openai PyYAML

3) 環境変数設定:
   - 対話式で .env を作成:
     python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考に）。主なキーは以下を参照。

4) 設定検証:
   python -m kabusys.validate_config
   # 警告も厳密に扱う場合:
   python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---------------------
（config_setup に定義されている主要項目）
- KABUSYS_ENV: 実行環境: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使うなら必須）

自動 .env ロード
- ライブラリはプロジェクトルート（.git または pyproject.toml を探索）を見つけ、
  .env を自動的に読み込みます（.env.local は .env を上書き）。
- 自動ロードを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（起動・運用例）
--------------------
- 監視ループを起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: MONITOR_POLL_INTERVAL=30）。
  - 停止にはプロジェクトルート/data/stop_requested.flag の作成（ファイル存在検出で終了）。

- 実行エンジンを起動:
  python -m kabusys.run_execution
  - 起動時に process priority を high に設定します（set_process_priority）。
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に書き込みます。
  - 実行停止は data/stop_requested.flag の作成。実行は execution.pid（data/execution.pid）を利用。

- 設定ウィザード（.env 作成）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で別 DB を指定可能（優先: --db > 環境変数 > デフォルト data/paper_trading.db）

- ライブラリ的利用例（スクリプトからインポートして利用）:
  from kabusys.research import calc_momentum
  # DuckDB 接続を渡して利用する形

停止・Kill Switch の仕組み
-------------------------
- run_monitoring/run_execution はプロジェクトルートの data/stop_requested.flag を監視します。ファイルが作成されると安全に停止します。
- KillSwitch（監視側）は条件（ドローダウン超過、ポジション上限超過など）を満たすと data/kill.flag を書き込み、ExecutionEngine 側で検出されれば発注エンジンを停止します。
- KILL_FLAG_CLEAR_ON_START=1 を有効にすると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging で集中管理します。
- デフォルトのログディレクトリ: logs/（環境変数 LOG_DIR で変更可）
- 各アプリケーション名（例: execution, monitoring）ごとに日次ローテーションされ logs/<app_name>.log に出力されます。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み / Settings
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py              — ニュース NLP（OpenAI 経由）
  - regime_detector.py       — 市場レジーム検出
- monitoring/
  - monitoring_db.py         — SQLite 永続化レイヤ
  - system_monitor.py
  - trade_monitor.py         — (存在を参照するが別ファイル)
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py         — (通知機能、実装参照)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

運用上の注意
-------------
- 本番環境（KABUSYS_ENV=live）では .env に機密情報を含めない運用／適切なシークレット管理を推奨します。
- kill.flag や stop_requested.flag の誤操作に注意。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag が自動クリアされてしまいます（本番では 0 推奨）。
- OpenAI を使用するモジュールは API コストやレート制限に注意してください。API キーは OPENAI_API_KEY を .env に設定してください。
- Paper Trading は本番 DB と分離されますが、設定ミスで書き込み先を誤らないよう validate_config を使って事前チェックしてください。

トラブルシュート
----------------
- .env が自動読み込みされない:
  - プロジェクトルートを .git / pyproject.toml から検出してロードします。CWD に依存しないため、配布後の環境でも動作します。
  - 自動ロードを無効にしている場合（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）やルートが見つからない場合は手動で .env を読み込んでください。
- ログファイルが作れない場合:
  - LOG_DIR のディレクトリ作成に失敗するとコンソール出力のみで継続します。権限やパスを確認してください。
- DuckDB / SQLite の接続エラー:
  - パスの親ディレクトリが存在しない場合は警告となることがあります（起動時に自動作成されることもあります）。validate_config で確認してください。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現在 0.1.0）。

以上がこのコードベースの README 相当の概要です。必要であれば以下を追記できます:
- よく使う CLI コマンド集（systemd ユニット例や docker-compose の設定例）
- 詳細な設定項目のテーブル（全環境変数・デフォルト値）
- 開発向けユニットテストの実行方法・カバレッジ方針
# KabuSys (README)

注意: この README はコードベース内の主要モジュール（src/kabusys 以下）を元に作成しています。実行前に .env を作成して必要な環境変数を設定してください。

概要
- KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装したパッケージです。
- 戦略のファクター計算、ポートフォリオ構築、注文発行（ExecutionEngine）、システム監視（Monitoring）、ニュース NLP による AI スコアリングなどの機能を含みます。
- DuckDB と SQLite をデータ永続化に使用します。OpenAI（ニュース評価・レジーム判定）との連携機能も含まれます。

主な機能
- ExecutionEngine 起動スクリプト（run_execution）:
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Paper Trading 時は MockBrokerClient を使用し DB を分離（data/paper_trading.db）
  - プロセス優先度を高く設定、PID 管理、停止フラグ監視
- Monitoring（run_monitoring / monitoring パッケージ）:
  - system / trade / risk の各モニタを統合したポーリングエンジン
  - システム稼働率、データ鮮度、滞留注文、ドローダウン監視
  - Kill Switch（data/kill.flag）により ExecutionEngine を安全に停止可能
- ポートフォリオ構築（portfolio パッケージ）:
  - 候補選定、重み付け（等比率 / スコア比率）、ポジションサイジング（リスクベース）、セクター制限、レジーム乗数
- リサーチ（research パッケージ）:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（ai パッケージ）:
  - ニュース記事を OpenAI（gpt-4o-mini 想定）でスコアリングして ai_scores に書込む機能
  - マクロニュース + ETF MA に基づく市場レジーム判定（regime_detector）
- ユーティリティ:
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
  - 統一ログ設定（utils/logging_setup）、プロセス優先度設定（utils/process_priority）

前提条件
- Python 3.9+（型ヒントや一部の記法を含むため）
- 推奨パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（設定検証で YAML 検証を行う場合に必要）
- インターネット接続（OpenAI を利用する場合）

セットアップ手順（開発環境向け）
1. リポジトリをクローンして移動
   - git clone <repo>
   - cd <repo>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env の作成（ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン、kabuAPI パスワード、DB パス等を対話的に作成します。
   - .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正してください。--strict を付けると警告もエラー扱いになります。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- OPENAI_API_KEY: OpenAI API キー（ai 機能利用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の fill モード（instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1、デフォルト 0)

実行方法（例）
- .env を作成し、必要な鍵を設定した上で実行してください。

1) ExecutionEngine を起動（実際の注文処理 or ペーパートレード）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB を使用し MockBrokerClient が使われます。
  - 起動時に data/execution.pid に PID を書き込み、data/stop_requested.flag / data/kill.flag で停止できます。

2) Monitoring を起動（バックグラウンド監視）
- python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
  - 監視は常に本番 sqlite_path を使用して監視テーブルに記録します（環境に依存しない）。

3) .env を対話的に作る
- python -m kabusys.config_setup

4) 設定検証
- python -m kabusys.validate_config
- 厳密モード: python -m kabusys.validate_config --strict

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

プログラム API（主な関数）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡してニュース NLP スコアを ai_scores に書き込みます。OPENAI_API_KEY を渡すか環境変数を設定してください。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - market_regime テーブルへレジームを書き込みます。
- kabusys.research.calc_momentum / calc_volatility / calc_value
  - DuckDB 接続と日付を渡してファクターを計算します。
- kabusys.portfolio.* の純粋関数群
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

ログ / データファイル
- ログ出力: logs/<app_name>.log（utils.logging_setup が日次ローテーションで管理）
- デフォルト DB:
  - DuckDB: data/kabusys.duckdb
  - Monitoring (SQLite): data/monitoring.db
  - Paper Trading (SQLite): data/paper_trading.db
- Kill / Stop フラグ:
  - kill.flag: Settings.kill_flag_path （デフォルト data/kill.flag） — Execution を停止するために monitoring が書き込む
  - stop_requested.flag: run_monitoring / run_execution で監視される停止フラグ（data/stop_requested.flag）
  - execution.pid: PID ファイル（data/execution.pid）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — （取引監視、コードベースに準拠）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - monitoring_engine.py   — 各モニタを束ねる
    - kill_switch.py         — kill.flag 書込みユーティリティ
    - alert_manager.py       —（アラート送信管理）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — レジーム判定（ETF MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

開発・デバッグのヒント
- .env の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を自動ロードします。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギング:
  - setup_logging(app_name="execution") を各起動スクリプトで呼んで統一的にログを管理します。ログ出力先は LOG_DIR 環境変数または logs/。
- OpenAI 呼び出し:
  - API 呼び出しはリトライ・バックオフやレスポンスバリデーションを実装していますが、API キーや料金、レート制限に注意してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対してカラム追加（例: peak_value, latency_ms）を行います。万が一のため DB のバックアップを推奨します。

最後に
- .env にセンシティブ情報（API キー、パスワード等）を保存する場合は、ファイルの取り扱い（権限・バックアップ・Git 除外）に注意してください。
- 本 README はコードスニペットの公開内容に基づいて作成しています。実際のリポジトリでは追加のモジュール・設定や README の独自拡張があるかもしれません。

必要であれば README を README.md 形式で整形して出力します。追加で記載したい実行例や環境変数のテンプレート（.env.example）を作成することもできます。
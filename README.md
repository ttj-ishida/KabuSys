KabuSys
=======

日本株自動売買システム（ライブラリ + 実行スクリプト群）

このリポジトリは、システム監視・注文実行・ポートフォリオ構築・リサーチ・AI ベースのニュース解析などを含む
日本株向け自動売買システムのコアモジュール群です。ライブラリとして機能を呼び出して組み合わせることも、
付属の起動スクリプトでプロセス単体を実行することもできます。

主な特徴
--------
- ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - KABUSYS_ENV による本番／ペーパートレード切替
  - paper_trading 環境では MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring（監視）起動スクリプト（run_monitoring.py）
  - システム状態、データ鮮度、トレードログ、リスクを定期チェックしログ化
  - Kill Switch（条件を満たしたら data/kill.flag を作成して Execution を停止）
- 監視 DB 層（SQLite）用の永続化ユーティリティ（monitoring_db.py）
- Risk / Trade / System の監視コンポーネント、MonitoringEngine（ポーリングループ）
- ポートフォリオ構築（候補抽出・重み計算・ポジションサイズ計算・セクター制限）
  - portfolio.portfolio_builder, risk_adjustment, position_sizing
- リサーチ用モジュール（DuckDB ベースのファクター計算・特徴量解析）
  - research.factor_research, research.feature_exploration
- AI モジュール（OpenAI を用いたニュース NLP、レジーム判定）
  - ai.news_nlp, ai.regime_detector
- 開発支援スクリプト
  - 環境設定ウィザード：config_setup.py（.env の対話式作成/更新）
  - 設定検証 CLI：validate_config.py（.env / config/*.yaml の事前チェック）
  - Paper Trading 検証レポート生成ツール：tools/paper_verification_report.py
- 共通ユーティリティ
  - ロギング設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
- .env 自動ロード機能（config.py）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込み

必要な依存パッケージ（概略）
----------------------------
主に以下を使用します（環境や利用機能により増減します）:
- Python 3.10+（typing 機能や型注釈の構文に準拠）
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（validate_config の YAML 検証を行う場合）

pip 等でインストールしてください。例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをチェックアウトし、仮想環境を作成
    - Python の仮想環境を用意し、必要なパッケージをインストールしてください。

2. .env の作成
    - 対話式ウィザードを使う（推奨）:
        python -m kabusys.config_setup
      もしくはプロジェクトルートに .env を手動で配置してください。

    - 主要な必須環境変数:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - オプション: KABUSYS_ENV（development / paper_trading / live）
      - OPENAI_API_KEY（AI 機能を使う場合）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）

3. 設定検証（必須ではないが推奨）
    python -m kabusys.validate_config
    - 警告も失敗扱いにする場合:
        python -m kabusys.validate_config --strict

4. データディレクトリ・ログディレクトリ
    - ログディレクトリ（デフォルト: logs/）は自動生成されますがパーミッション等を確認してください。
    - data/ 配下に SQLite DB や PID / flag 用ファイルが配置されます（自動生成もあり）。

使い方（主要スクリプト）
------------------------

- 監視ループを起動（Monitoring）
    python -m kabusys.run_monitoring

    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
      例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

    - 停止方法:
      - キーボード割り込み（Ctrl-C）
      - またはプロジェクトルートの data/stop_requested.flag を作成すると、ループは検知して終了します。

- 発注エンジンを起動（ExecutionEngine）
    python -m kabusys.run_execution

    - KABUSYS_ENV による振る舞い:
      - paper_trading: MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に取引ログを保存します（本番 DB と分離）。
      - live: 本番モード（外部ブローカークライアントが使用されます）。
      - development: ローカル開発用（発注を行わない等の挙動がある想定）
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - 実行中は data/execution.pid に PID を書き出します。

- .env を対話式で作る / 更新
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB パスはオプション --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定

- AI 機能（ライブラリ呼び出し）
    - ニュース NLP（スコア取得）
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key="...")

    - レジーム判定
      from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key="...")

    ※ 直接 CLI スクリプトは用意していませんが、上記関数を小さなラッパーから呼ぶか Python -c / スクリプトで利用できます。

停止フラグ / Kill Switch
-----------------------
- data/stop_requested.flag
  - run_monitoring.py/run_execution.py の外部停止（プロセスが存在するディレクトリの data/stop_requested.flag を作成すると監視ループ/エンジンが安全に終了します）。
- data/kill.flag
  - KillSwitch（監視の一部）が作成するフラグ。ExecutionEngine はこのフラグを検知して停止します。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 を有効にすると起動時に自動でクリアされますが、本番では 0 を推奨します。

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されています。
- デフォルトで stdout（StreamHandler）と logs/<app_name>.log（TimedRotatingFileHandler, 日次ローテーション、30日保持）へ出力します。
- 環境変数 LOG_DIR または引数でログ保存先を変更可能。

ライブラリ利用例（ポートフォリオ / リサーチ）
------------------------------------------
- ポートフォリオ構築関数群:
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

- リサーチ関数群（DuckDB 接続を渡して使用）:
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / .env 自動ロード / Settings
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 起動前設定検証 CLI
- run_monitoring.py              — Monitoring ポーリングループ起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート生成 CLI
- monitoring/
  - monitoring_db.py              — SQLite 永続化層（テーブル作成含む）
  - system_monitor.py
  - trade_monitor.py (参照実装あり)
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py (参照実装あり)
- execution/                      — Execution 関連（Engine / BrokerFactory / order_manager 等）
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
- utils/
  - logging_setup.py
  - process_priority.py
- data/ (実行時に利用／生成される)
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kill.flag, stop_requested.flag, execution.pid など

補足 / 注意事項
---------------
- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml がある場所）を起点に .env と .env.local を自動で読み込みます（OS 環境変数を上書きしない挙動）。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV の有効値:
  - development, paper_trading, live
  - live を使う際は本番設定（API トークン、LINE 通知設定など）を慎重に確認してください。
- AI 機能を利用する場合は OPENAI_API_KEY の設定が必須です。また API 呼び出しエラー時はフォールバックやリトライ処理が組まれていますが、コストとレート制限に注意してください。
- DuckDB / SQLite のパスは Settings で指定できます。monitoring は常に本番 sqlite_path を参照する設計の箇所があるため（run_monitoring など）、実行前に .env のパス設定を確認してください。

貢献・拡張のヒント
-------------------
- ExecutionEngine や Broker クライアントは抽象化されているため、新しいブローカー実装を追加して組み込めます。
- position_sizing の lot_size を銘柄別に拡張する等、細かな取引ルールのカスタマイズが想定されています。
- validate_config の config/*.yaml 検証には PyYAML が必要です。CI に組み込むと本番設定ミスを早期に検出できます。

ライセンス / バージョン
-----------------------
- パッケージバージョン: src/kabusys/__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE ファイルを参照してください（存在する場合）。

お問い合わせ / サポート
-----------------------
- 実装や挙動に関する質問があれば、実装ファイル（特に config.py、run_*.py、monitoring/*.py）を参照してください。
- 起動時の問題は logs/<app_name>.log を確認すると原因特定がしやすいです。

以上がこのリポジトリの概要と基本的な使い方です。README に書かれていない細かな挙動は各モジュールの docstring / コメントを参照してください。
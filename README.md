KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。  
本READMEはコードベースから主要な使い方・設定・ディレクトリ構成を抜粋して日本語でまとめた開発者向けの入門ドキュメントです。

概要
----
KabuSys は以下の責務を持つモジュール群で構成されています（主に純粋関数群・監視・実行エンジン・リサーチ・AI連携など）:

- 発注エンジン（ExecutionEngine）と注文管理、リスク管理
- 監視（Monitoring）：システム状態、滞留注文、ドローダウン等のチェックとアラート / Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算、特徴量探索）
- AI連携（ニュースのNLPスコアリング、レジーム判定） — OpenAI API を使用
- 補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート生成）

主な機能一覧
-------------
- 環境設定ウィザード: python -m kabusys.config_setup による .env の対話的作成・更新
- 設定検証: python -m kabusys.validate_config で .env や config/*.yaml の検証（--strict オプションあり）
- Execution エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番DBと分離）
  - プロセス優先度を "high" に設定
  - data/execution.pid を利用
  - 起動中に data/stop_requested.flag を置くことで停止
- Monitoring 起動: python -m kabusys.run_monitoring
  - SystemMonitor のポーリングループ（デフォルト間隔 60 秒）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能
  - 監視用 SQLite（デフォルト data/monitoring.db）へログ永続化
- Kill Switch: 条件（ドローダウン超過、ポジション上限超過 等）で data/kill.flag を書き込み ExecutionEngine を停止
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
  - PAPER_TRADING_SQLITE_PATH を参照（デフォルト data/paper_trading.db）
  - 稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定
- AI連携機能:
  - kabusys.ai.news_nlp.score_news（OpenAI を用いたニュースセンチメントの算出・ai_scores への書込み）
  - kabusys.ai.regime_detector.score_regime（ETF MA 乖離と LLM によるマクロセンチメントを合成して市場レジーム判定）
  - OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で渡す

セットアップ手順
----------------

前提
- Python 3.8+（若干の機能により 3.9/3.10 を想定）
- SQLite は標準ライブラリで利用
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行う場合）
  - （必要に応じて）その他 execution/broker 系の依存

例: 仮想環境と依存インストール
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール（requirements.txt があればそちらを使用）
  - pip install duckdb psutil openai pyyaml

.env の作成
- 推奨: 対話式ウィザードで作成
  - python -m kabusys.config_setup
- もしくは .env を手動で作成（.env.example を参照）
- 自動ロード:
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロードします
  - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

重要な環境変数（主要項目）
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時の専用 DB）デフォルト: data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、既定 60）
- PAPER_FILL_MODE: paper_trading 時の MockBroker の fill モード ("instant" | "partial" | "never" | "reject")
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0 or 1。production は 0 推奨）

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して行われます
- デフォルト出力:
  - コンソール（stdout）
  - ログファイル: logs/<app_name>.log（日次ローテーション、30世代保持）
- ログディレクトリは LOG_DIR 環境変数またはデフォルト "logs"

使い方（主要コマンド）
--------------------

1) 環境ウィザード（.env 作成）
- python -m kabusys.config_setup
  - 対話的に .env を生成・更新します

2) 設定検証
- python -m kabusys.validate_config
- 厳密モード（WARNING を FAIL 扱いにする）:
  - python -m kabusys.validate_config --strict

3) Execution エンジン起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合: MockBrokerClient を用い data/paper_trading.db に記録（本番 DB とは分離）
  - 起動前に data/stop_requested.flag が存在すると起動せず終了
  - 実行中に data/stop_requested.flag を置くと停止します
  - PID ファイル: data/execution.pid（設定で変更可）

4) Monitoring 起動
- python -m kabusys.run_monitoring
  - デフォルトポーリング間隔: 60 秒
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（1 秒以上）
  - 監視は監視用 SQLite（settings.sqlite_path）に永続化（monitoring は常に本番 sqlite_path を使用）
  - 停止: data/stop_requested.flag を作成するとループを終了

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db /path/to/paper_trading.db（あるいは環境変数 PAPER_TRADING_SQLITE_PATH）

6) AI 機能（コード経由）
- news_nlp.score_news(conn, target_date, api_key=None)
  - conn: duckdb connection（DuckDBPyConnection）
  - target_date: 日付（date オブジェクト）
  - api_key: 省略時は OPENAI_API_KEY を参照
- regime_detector.score_regime(conn, target_date, api_key=None)

停止フラグ / Kill Switch
- data/kill.flag: ExecutionEngine を停止させるためのフラグファイル（KillSwitch が作成）
- KillSwitch はリスクアラート等で条件を満たすと kill.flag を書き込みます
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合、自動的に kill.flag を削除します（本番では 0 推奨）
- data/stop_requested.flag: 実行中の run_monitoring / run_execution を即時終了させるためのフラグ（運用用の外部停止指示）

データベースとスキーマ
- monitoring_db.init_monitoring_db(conn) により以下のテーブルを作成（冪等）:
  - system_status, trade_logs, positions, risk_logs, dashboard
- DuckDB は時系列・価格データや各種マスタを格納・分析に利用（デフォルト data/kabusys.duckdb）
- ペーパートレード用の独立 SQLite（PAPER_TRADING_SQLITE_PATH）により本番 DB と分離

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 以下の主要なモジュールの概要（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       —（滞留注文・約定異常などの監視）※実装ファイルあり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 monitor の束ね
    - alert_manager.py       —（通知管理）※実装ファイルあり
  - execution/
    - execution_engine.py    — ExecutionEngine（実行本体）※実装ファイルあり
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 等重・スコア重み
    - risk_adjustment.py     — セクター制限・レジーム乗数
    - position_sizing.py     — 数量計算 / aggregate cap / lot 単位処理
  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py            — ニュース NLP スコア（OpenAI）
    - regime_detector.py     — レジーム判定（MA + LLM 合成）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成ツール

実運用上の注意点
----------------
- KABUSYS_ENV は慎重に設定してください。live 設定時は本番口座に実際に発注されます。
- .env は決してリポジトリにコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- OpenAI キーや API トークンなどのシークレットは OS 環境変数で管理するか .env に格納してください（.env は Git 管理下に置かないこと）。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソールのみになります。監視運用時は logs/ に書き込み権限があることを確認してください。
- MONITOR は監視専用の DB（SQLITE_PATH）に常に書き込む設計なので、Monitoring と Execution の DB が分離されているか設定を確認してください（paper_trading モード時 Execution は paper_sqlite_path を使います）。

開発者向けヒント
----------------
- 各処理は副作用を最小化するよう設計されています。AI API 呼び出し部分は比較的独立しており、テスト時は _call_openai_api をパッチして振る舞いを模擬できます（news_nlp.py / regime_detector.py の実装参照）。
- DuckDB 接続を渡して純粋関数的にファクター計算を行うため、データを準備すればローカルで再現検証が容易です。
- validate_config.py は設定不備を起動前に検出するため CI の前段やデプロイ前チェックに組み込むと安全です。

参考コマンド一覧（まとめ）
------------------------
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

この README はコードベースの主要ポイントをまとめたものです。詳細な設計（StrategyModel.md、PortfolioConstruction.md 等）や追加の運用手順は別途ドキュメントにまとめてください。必要であれば README に追記する項目（例: デプロイ手順、Dockerfile、systemd ユニット例、CI 設定例）を教えてください。
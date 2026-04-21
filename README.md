KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株の自動売買を想定した小規模なフレームワークです。本プロジェクトは以下の主要機能を含みます。
- 発注実行エンジン（ExecutionEngine）
- 監視 / リスク管理（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- ニュース NLP（OpenAI を用いたセンチメントスコアリング）
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading レポート等）

設計方針のポイント:
- 設定は .env（環境変数）で管理。プロジェクトルートの .env / .env.local を自動ロード（必要なら無効化可）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離し、モックブローカーを利用して data/paper_trading.db に記録します。
- DuckDB を分析用途に利用、SQLite を監視・トレードログ等の永続化に使用。
- OpenAI を利用する AI モジュールは API キー（OPENAI_API_KEY）が必要。失敗時はフェイルセーフ動作を実装。

主な機能一覧
--------------
- 実行（run_execution.py）
  - ExecutionEngine を起動。KABUSYS_ENV によって本番または paper_trading を切り替え。
  - 起動時にプロセス優先度を高（high）に設定、PID ファイルを書き込み。
  - 停止は data/stop_requested.flag（プロジェクトルート/data/stop_requested.flag）や kill.flag によって制御。

- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、監視ログとアラート管理を行う。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔の上書き（デフォルト 60 秒）。
  - 監視 DB（SQLite）は環境に関係なく本番 sqlite_path を使用して初期化。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（select_candidates）、等金額／スコア加重（calc_equal_weights / calc_score_weights）。
  - ポジションサイズ算出（calc_position_sizes）：リスクベース、等分配等に対応。単元株丸め・利用可能現金によるスケーリングを実装。
  - セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。

- 研究（kabusys.research）
  - ファクター計算（momentum, volatility, value）: DuckDB の prices_daily/raw_financials を用いた純粋関数。
  - 将来リターン、IC 計算、統計サマリーなどのユーティリティ。

- AI（kabusys.ai）
  - news_nlp: ニュース記事を集約して OpenAI でスコアリングし ai_scores テーブルへ書き込み。
  - regime_detector: ETF の MA 乖離＋マクロニュースセンチメントを合成して market_regime を書き込み。

- ツール（kabusys.tools）
  - paper_verification_report: Paper Trading の稼働率 / 注文成功率 / レイテンシ等を集計してレポート出力。

セットアップ手順
----------------
1. 必要な Python バージョンを用意（3.9+ を想定）。
2. 依存パッケージをインストール（例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt は本リポジトリに含まれていないため、上記をプロジェクトの要件に合わせて管理してください。

3. プロジェクトルートに移動して環境変数を用意:
   - 対話式ウィザードで .env を作成できます:
       python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成してください。

4. 設定検証:
       python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. 初回起動時のディレクトリ／DBファイル作成:
   - SQLite / DuckDB のデフォルトパスは data/ 配下です（下記参照）。
   - ログは logs/ に出力されます（logs/ 作成は logging_setup が自動で試みます）。

主な環境変数（要・推奨事項）
--------------------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）

- データベース:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (Paper Trading 用: data/paper_trading.db)

- AI:
  - OPENAI_API_KEY

- ログ:
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR（デフォルト: logs/）

- 監視関連:
  - MONITOR_POLL_INTERVAL（秒。run_monitoring のポーリング間隔を上書き）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1）

- Paper Trading:
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- 自動 .env ロード無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方
-------
- 実行エンジン起動（本番 / paper_trading を .env の KABUSYS_ENV で制御）:
    python src/kabusys/run_execution.py
  - 起動時に data/execution.pid が使われます。停止は data/stop_requested.flag（または kill.flag による）を立てる方法があります。

- 監視ループ起動:
    python src/kabusys/run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定できます（例: MONITOR_POLL_INTERVAL=30）。

- .env 初期作成（対話式）:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを --db で指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を利用します。

- AI モジュール利用:
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、OpenAI API キーが必要です。
  - 直接 CLI は用意していませんが、import してスクリプトやスケジューラから呼び出す想定です。

停止・Kill Switch に関する注意
------------------------------
- 手動停止指示:
  - プロジェクトルート/data/stop_requested.flag を作成すると run_execution / run_monitoring のループを終了します（run_execution は起動時にもチェック）。
- Kill Switch:
  - risk_monitor の判定等により data/kill.flag が書き込まれると ExecutionEngine 側で検知して停止します（KILL_FLAG_CLEAR_ON_START=1 のとき起動時に自動クリアする挙動に注意。live 環境では 0 推奨）。

ディレクトリ構成（抜粋）
-----------------------
以下は主要ファイルを抜粋した構成（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA）

  - monitoring/
    - monitoring_db.py        — SQLite 操作用ラッパー（テーブル初期化含む）
    - system_monitor.py       — システム状態・データ鮮度チェック
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - trade_monitor.py        — 取引ログ監視（滞留注文等）※詳細はソース参照
    - monitoring_engine.py    — 各 monitor を束ねるエンジン
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - alert_manager.py        — アラート送信管理（実装参照）

  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py       — ブローカークライアント生成（Mock/実 API 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - data/                     — データ処理 / pipeline 等（DuckDB 用 SQL 取得など）
  - tools/
    - paper_verification_report.py

ログ・DB のデフォルトパス
-------------------------
- ログ: logs/<app_name>.log（日次ローテーション）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID / フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag

開発上のヒント
---------------
- 自動 .env ロードは Settings モジュールでプロジェクトルート（.git / pyproject.toml）を探索して行われます。テスト等で自動読み込みを抑えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API の呼び出しは外部ネットワークに依存するため、テスト時は該当関数（_call_openai_api 等）を patch してモック化する設計になっています。
- DuckDB への executemany はバージョンに依存する挙動があるため、ai モジュール内で空のパラメータを避ける配慮がされています。

ライセンス・バージョン
---------------------
パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

その他
-----
- 本 README はコードベースから抽出できる情報に基づいて作成しています。実運用や本番接続の前に config/*.yaml や .env の中身を十分に検証してください（python -m kabusys.validate_config を推奨）。

必要であれば、実際の運用手順（systemd / cron / Docker Compose でのサービス化例）、CI 用のテスト実行手順、また各モジュールの設計ドキュメント（API 仕様や DB スキーマ詳細）を別途作成します。どの情報を追加したいか教えてください。
README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主要な責務は次のとおりです。

- 注文実行エンジン（ExecutionEngine）: ブローカークライアント経由で注文管理と約定処理を行う（paper_trading モード時は MockBroker を使用し、本番 DB と分離）。
- 監視（Monitoring）: システム稼働状況、データ鮮度、注文ログ、リスク指標などを定期ポーリングして永続化・アラート・Kill Switch 判定を行う。
- ポートフォリオ構築・サイズ計算（portfolio）: 候補選定、重み算出、セクター制約の適用、発注株数計算などの純粋関数群。
- リサーチ（research）: ファクター計算（Momentum / Volatility / Value 等）、将来リターン・IC 計算、統計サマリ。
- AI（ai）: ニュース NLP によるセンチメント集約（OpenAI）や市場レジーム判定のロジック（LLM を利用）。
- ユーティリティ（utils）: ロギング設定、プロセス優先度設定など。

主な設計方針:
- データベースは DuckDB（分析用）と SQLite（監視・発注履歴用）を併用。
- 本番環境と paper_trading を明確に分離（paper_trading 用 DB は data/paper_trading.db）。
- 外部 API 呼び出し（OpenAI 等）はリトライ・フォールバックを実装しフェイルセーフに運用可能。

主な機能一覧
--------------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading DB に記録
  - PID ファイルと停止フラグでプロセス制御
- 監視ループ起動スクリプト: run_monitoring.py
  - システムリソース、プロセス存否、データ鮮度監視
  - MONITOR_POLL_INTERVAL でポーリング間隔を設定可能（デフォルト 60 秒）
- 設定ウィザード: config_setup.py
  - .env を対話式に生成・更新
- 設定検証 CLI: validate_config.py
  - .env や config/*.yaml の簡易検証（--strict で警告を失敗扱い）
- Paper Trading 検証レポート生成: tools/paper_verification_report.py
  - paper_trading DB から稼働率、注文成功率、レイテンシ等を出力
- AI モジュール:
  - news_nlp.score_news(): raw_news を集約して OpenAI でセンチメントを算出して ai_scores に書き込み
  - regime_detector.score_regime(): ETF MA とマクロ記事の LLM センチメントを合成して market_regime に書き込み
- ポートフォリオ関係:
  - 候補選定、等金額／スコア加重、ポジションサイズ計算、セクター上限適用、レジーム乗数
- ロギング／プロセス関連ユーティリティ:
  - logs/<app>.log に日次ローテーションで出力（TimedRotatingFileHandler）
  - プロセス優先度設定、CPU affinity 設定（psutil ベース）

準備（依存関係）
----------------
推奨 Python バージョン: 3.9+

必須パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（config YAML のパースと validate_config の一部チェックに利用。無くても動く）

pip での一例:
pip install duckdb psutil openai PyYAML

（必要に応じて仮想環境を作成してからインストールしてください）

設定（.env）
-----------
プロジェクトルートに .env を置くか、環境変数で設定します。自動ロードはデフォルトで有効（プロジェクトルートを判定して .env / .env.local を読み込み）。

重要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABUSYS_ENV           : 実行環境 (development | paper_trading | live)（デフォルト development）
- OPENAI_API_KEY        : OpenAI API キー（ai モジュールを使う場合）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE       : paper_trading の約定挙動（instant|partial|never|reject）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL : 監視ループのポーリング間隔（秒） — run_monitoring.py で参照

.env の作成（対話式ウィザード）:
python -m kabusys.config_setup
ウィザード実行後に .env を保存できます。

設定検証:
python -m kabusys.validate_config
--strict を付けると警告も失敗扱いになります。

セットアップ手順（概要）
---------------------
1. リポジトリをクローンしてワークディレクトリをプロジェクトルートにする
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（duckdb, psutil, openai, PyYAML など）
4. python -m kabusys.config_setup で .env を作成（または環境変数を設定）
5. python -m kabusys.validate_config で設定を検証
6. データディレクトリを作成（必要なら）:
   mkdir -p data logs

使い方（起動・ツール）
--------------------

実行エンジンを起動:
- 通常（バックグラウンド管理は OS のサービスや supervisor 等で実行してください）:
  python -m kabusys.run_execution

- 挙動:
  - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録し、MockBroker を用いる
  - 起動時に data/stop_requested.flag が存在すると起動せず終了
  - 実行中は data/execution.pid を使用（PID ファイル）
  - 停止は stop flag / kill.flag により制御（下記参照）

監視ループを起動:
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
- 監視プロセスは Settings.sqlite_path を使用して system_status / trade_logs / risk_logs 等を永続化する（Monitoring は環境にかかわらず本番 sqlite_path を使用）

Paper Trading 検証レポート:
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

AI 系関数（プログラム呼び出し）:
- OpenAI API キーを設定（OPENAI_API_KEY）
- 例: news_nlp.score_news(conn, target_date, api_key=None) を呼び出す（DuckDB 接続を渡す）
- regime_detector.score_regime(conn, target_date, api_key=None) で市場レジーム判定・書き込み

停止と Kill Switch / Stop Flag
------------------------------
- 一時停止（監視/実行ループを安全に停止）:
  - data/stop_requested.flag を作成すると run_monitoring と run_execution のループが検知して終了します。
  - 監視ループは stop_requested.flag の存在を見てループ終了します。
- Kill Switch:
  - monitoring の判定（ドローダウン超過やポジション上限超過）により data/kill.flag が書き込まれると ExecutionEngine は停止されます（ExecutionEngine 側で kill.flag を検出して engine.stop() を呼ぶ設計）。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動で削除します（本番では 0 推奨）。

ロギング
--------
- 共通の setup_logging() を使用し、stdout と logs/<app_name>.log（日次ローテーション）に出力します。
- ログディレクトリ作成に失敗した場合、ファイル出力はスキップしてコンソールのみ出力されます。

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクトの src/kabusys 以下のおおまかな構成:

- kabusys/
  - __init__.py                    — パッケージ定義、バージョン
  - config.py                      — 環境変数・設定管理（Settings クラス）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py                  — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py           — 市場レジーム判定（LLM + ETF MA）
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 発注株数計算・集計上限の処理
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - research/
    - factor_research.py           — モメンタム / ボラティリティ / バリュー等の計算
    - feature_exploration.py       — 将来リターン計算、IC、統計サマリ
  - monitoring/
    - monitoring_db.py             — SQLite テーブル作成・永続化 API
    - system_monitor.py            — システム・データ鮮度監視
    - trade_monitor.py             — （注文ログ監視、該当ファイルに実装）
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — kill.flag の作成操作
    - monitoring_engine.py         — 各 monitor を束ねるランナー
  - execution/
    - （エンジン、オーダー管理、ブローカーファクトリ等）
  - data/                           — 既定のデータ格納先（データベース、flags 等）
  - logs/                           — ログ出力先（自動作成）

注意事項・運用上のヒント
-----------------------
- 本番（KABUSYS_ENV=live）運用時は .env の内容・キー管理に十分注意してください。.env は Git にコミットしないでください。
- KILL_FLAG_CLEAR_ON_START の取り扱いに注意。誤って 1 にすると本番で Kill Switch を自動クリアしてしまうリスクがあります。
- OpenAI 呼び出しを行う AI モジュールは API コストとレート制限に注意して運用してください。失敗時はフォールバックが働きますが、期待通りのデータが得られない可能性があります。
- ロギングディレクトリのパーミッションやディスク容量監視は導入時に確認してください。

ライセンス・バージョン
---------------------
パッケージバージョン:
- kabusys.__version__ = 0.1.0

（ライセンス情報はリポジトリに含めてください）

お問い合わせ・拡張
-----------------
- モジュールは比較的疎結合に設計されています。たとえば別のブローカークライアントを実装して BrokerClientFactory に登録すれば実際の発注連携を差し替えられます。
- AI 関連の実装は API 呼び出し部をモック化しやすいようにレイヤー化されています。ユニットテストの作成や API 呼び出しの差替えが容易です。

以上が本リポジトリの概要と基本的な使い方です。必要であれば、各モジュールの使い方や API の呼び出し例、運用手順を別途詳細ドキュメントとして作成できます。
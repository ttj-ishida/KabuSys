KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を支援する Python ベースのシステムです。本リポジトリは次の主要機能を含みます。

- 発注実行エンジン（ExecutionEngine）：本番 / ペーパートレード両対応
- 監視コンポーネント（Monitoring）：プロセス/リソース/注文/リスク監視、Kill Switch
- ポートフォリオ構築ライブラリ：候補選定・重み算出・ポジションサイズ計算・セクター制限
- リサーチ機能（DuckDB を使ったファクター計算・特徴量解析）
- AI 補助モジュール：ニュースセンチメント（OpenAI）・市場レジーム判定
- 運用ツール：.env ウィザード、設定検証、ペーパートレード検証レポート生成 等

主な特徴
---------
- 環境分離：KABUSYS_ENV により development / paper_trading / live を切替。ペーパートレードは本番 DB と分離して専用 SQLite に記録。
- フェイルセーフ設計：監視 → kill.flag による ExecutionEngine 停止、例外を握り潰して継続する設計箇所あり。
- ロギング：統一的な logging 設定（コンソール + 日次ローテートファイル）。
- OpenAI 統合：ニュースセンチメント・レジーム判定（gpt-4o-mini を想定）。API 呼び出しはリトライ/バリデーション実装済み。
- DuckDB を分析用 DB として利用し、リサーチ処理は SQL / Python ベースで実行。

セットアップ
-----------
前提
- Python 3.8+（プロジェクトの実環境に合わせてください）
- 必要ライブラリのインストール（例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - pyyaml（設定ファイル検証を行う場合）
例:
  pip install duckdb psutil openai pyyaml

初期設定手順（推奨）
1. リポジトリルートへ移動し、データ / ログディレクトリを作る:
   mkdir -p data logs

2. .env を対話式で作成:
   python -m kabusys.config_setup
   - ウィザードに従って必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。
   - .env は絶対に Git にコミットしないでください。

3. 設定検証:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

4. （AI 機能を使う場合）OpenAI API キーを設定:
   - 環境変数 OPENAI_API_KEY を .env に設定するか、関数呼び出し時に渡します。

主要環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live。デフォルト development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...。デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）

主要スクリプト／使い方
--------------------

1) ExecutionEngine（発注エンジン）起動
- 本番 / ペーパートレード切替は KABUSYS_ENV で制御。paper_trading の場合は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録されます。
- 起動:
  python -m kabusys.run_execution
- 実行中は data/execution.pid に PID（設定により変わる）が作成されます。
- 停止方法:
  - 監視プロセス経由で kill.flag が作成されると ExecutionEngine は安全に停止します。
  - 手動停止はプロセスに SIGINT 等を送るか、data/stop_requested.flag を作成すると run_execution のループが終了します。

2) Monitoring（監視プロセス）起動
- 監視ループは SystemMonitor / TradeMonitor / RiskMonitor をポーリングします。
- 起動:
  python -m kabusys.run_monitoring
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
- 監視は常に sqlite_path（デフォルト data/monitoring.db）を使用します（環境に無関係）。

3) 設定ウィザード / 検証
- .env 作成: python -m kabusys.config_setup
- 検証: python -m kabusys.validate_config [--strict]

4) ペーパートレード検証レポート
- データベース（ペーパートレードの SQLite）から期間を指定してレポートを生成します。
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- または DB パスを指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定できます。

5) AI 機能
- news_nlp.score_news: raw_news を集約して OpenAI でセンチメントを評価し ai_scores テーブルへ書込む。OpenAI API キーが必要。
- regime_detector.score_regime: ETF（1321）MA200 やマクロニュースを合成して market_regime テーブルへ書込む。OpenAI API キーが必要。
- これらはライブラリ API として呼び出すか、運用バッチを作成して定期実行してください。

挙動・運用上の注意
------------------
- 監視と実行はファイルフラグで制御:
  - data/kill.flag: Kill Switch が作成されると ExecutionEngine に停止シグナルを送ります（監視側で作成）。
  - data/stop_requested.flag: run_monitoring / run_execution のループを外部から終了させるために使われています。
- ログ:
  - デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）とコンソール出力。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等にテーブル作成・簡易マイグレーションを行います（カラム追加等）。
- ペーパートレード:
  - KABUSYS_ENV=paper_trading の場合、実際のブローカー接続は MockBrokerClient を使い、紙上での約定をシミュレートします（PAPER_FILL_MODE による挙動制御）。

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主なファイル・モジュール（src/kabusys 以下）抜粋です。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                  — 環境変数/.env の自動読み込みと Settings クラス
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py         (省略)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         (省略)
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

（注）実際のリポジトリには上記の他にも execution/、data/、strategy/ 等のモジュールが存在する想定です。プロジェクト全体の構成はパッケージ化された配布物やリポジトリのルートを参照してください。

トラブルシューティング
----------------------
- .env が読み込まれない:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていると自動ロードをスキップします。
  - config._find_project_root() がプロジェクトルート（.git または pyproject.toml）を見つけられない場合も自動ロードをスキップします。
- OpenAI 呼び出しで失敗する:
  - API キーが未設定の場合は ValueError を返します。
  - 一時的なエラー（429, ネットワーク等）はリトライしますが、上限到達時はスキップしてフェイルオープンします（システムは継続）。
- ログファイルや DB のパーミッションエラー:
  - logs/ や data/ の所有者・書き込み権限を確認してください。

ライセンス・貢献
----------------
- この README はコードベースの概要と使い方を簡潔にまとめたものです。実際のライセンス・コントリビュート方法についてはリポジトリの LICENSE / CONTRIBUTING ファイルをご確認ください。

補足
----
- 本 README はコード内のドキュメント文字列（docstring）と設定コードから主要点を抜粋して作成しています。細かな実装や追加モジュールの詳細は該当ソースファイルの docstring を参照してください。質問や具体的な使い方（例: ExecutionEngine の設定項目や Broker 実装の切替方法）が必要であれば、対象モジュール名を指定して教えてください。
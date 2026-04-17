README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのサブコンポーネント群です。本リポジトリは、以下を中心に実装しています。
- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視用モジュール群（SystemMonitor / TradeMonitor / RiskMonitor など）
- ポートフォリオ構築・ポジションサイズ計算ロジック
- 研究用ファクター計算・特徴量解析モジュール（DuckDB を使用）
- ニュース NLP（OpenAI）を用いたセンチメントスコアリング
- Paper Trading 用検証レポート生成スクリプト
- .env 対話ウィザード / 設定検証ツール

本プロジェクトは設計上、本番 DB とペーパートレード DB を明確に分離しており、環境変数によって挙動を切り替えます。

主な機能
--------
- ExecutionEngine 起動（KABUSYS_ENV に応じて実ブローカ or MockBroker を使用）
- 監視ループ（システム状態・データ鮮度・注文異常・リスク検出）
- Kill Switch（条件に応じた停止フラグ書込み）
- ポートフォリオ候補選定・重み付け・ポジションサイズ計算（等金額／スコア／リスクベース）
- 研究用: モメンタム・ボラティリティ・バリュー等のファクター計算
- ニュース NLP による銘柄別センチメント算出（OpenAI 使用）
- Paper Trading 検証レポート生成（期間指定で指標出力）
- .env の対話式作成（config_setup）と起動前の検証（validate_config）

セットアップ手順
----------------
1. Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML (config 検証を行う場合に推奨)
   - 例:
     - pip install duckdb psutil openai PyYAML

   補足:
   - openai クライアントはニュース NLP / レジーム検出で使用します。API キーが必要です。
   - 追加の内部モジュールに依存がある場合は適宜インストールしてください。

3. .env を作成する
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を手動で作成
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - その他重要な変数（例とデフォルト）:
     - KABUSYS_ENV=development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=（OpenAI を使う場合）
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0  (本番では 0 推奨)

4. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

使い方
------
下記は主要な CLI / モジュールの実行例です。

- ExecutionEngine を起動する
  - 本番/開発/ペーパートレードは KABUSYS_ENV で切替え
  - 例（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 仕様:
    - paper_trading の場合は MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に保存されます。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中に停止するには stop フラグファイルを使う仕組み（Kill Switch による data/kill.flag など）。

- 監視ループ（単体の SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視側は Settings に関わらず本番 sqlite_path を使用して監視ログを保存します。
  - run_monitoring はプロセス優先度を "high" に設定しようとします（psutil によりプラットフォーム依存）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を利用するか、環境変数 PAPER_TRADING_SQLITE_PATH を設定します。

- News NLP / Regime Detector（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数か環境変数 OPENAI_API_KEY で渡す必要があります。

- .env の作成支援
  - python -m kabusys.config_setup
  - ウィザードで入力後、.env が生成されます。生成後は python -m kabusys.validate_config で検証を行ってください。

重要な動作・挙動メモ
--------------------
- 停止フラグ:
  - run_execution / run_monitoring はプロジェクト内の data/stop_requested.flag をチェックして終了します（スクリプトによりパスが参照されます）。
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）に書き込むことで ExecutionEngine に停止シグナルを与えます。実行エンジン側で kill.flag を検知して停止する実装になっています。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- Paper Trading の分離:
  - KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）へ書き込みます。本番 DB（monitoring.db 等）と分離されます。

- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔を秒で指定できます。0以下の値は無効扱いでデフォルトにフォールバックします。

- OpenAI 呼び出し:
  - news_nlp / regime_detector では OpenAI に対するリトライ・バリデーションを実装していますが、API キーが未設定だと例外になります。API 利用時はコスト・レート制限に注意してください。

ディレクトリ構成（抜粋）
---------------------
- src/kabusys/
  - __init__.py
  - config.py              — 環境変数読み込み・Settings クラス
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 起動前チェック CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py           — 銘柄別ニュース NLP（OpenAI）
    - regime_detector.py    — マーケットレジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py      — SQLite 監視ログ CRUD 層
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — 注文滞留・約定異常監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書き込みユーティリティ
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - alert_manager.py      — （アラート送信管理: 実装ファイル）
  - execution/              — ExecutionEngine 周りの実装（OrderManager 等）
  - portfolio/              — portfolio_builder / position_sizing / risk_adjustment
  - research/               — factor_research / feature_exploration
  - utils/
    - process_priority.py   — プロセス優先度・CPU affinity ユーティリティ
  - data/                   — （実行時に使用する既定の DB ファイル等: data/*.db）

例: 主要ファイルの役割
- config.py: Settings クラスを通じて環境変数を扱います。プロジェクトルートの .env/.env.local を自動読み込みします（無効化可）。
- monitoring_db.py: 監視用の SQLite テーブル定義・マイグレーションと簡易 CRUD。
- news_nlp.py / regime_detector.py: OpenAI を使った NLP 処理。API キー必須。

よくあるトラブルシューティング
----------------------------
- OpenAI API キー未設定
  - ニュース NLP / レジーム検出が ValueError を投げます。OPENAI_API_KEY を設定してください。

- psutil による優先度設定失敗
  - 権限不足やプラットフォーム非対応のため警告でスキップされます。正常動作に問題はありません。

- .env が読み込まれない
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）を探索して .env を自動読み込みします。CI 等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発者向けメモ
--------------
- DuckDB 接続を渡して純粋関数群（research/*）でデータ処理を行う設計です。これにより分析処理は発注 API に影響を与えません。
- monitoring/ 内の各モジュールは MonitoringDB を通じて監視ログを永続化します。ログ設計は idempotent（多重実行で安全）を意識しています。
- 単体テスト時は OpenAI 呼び出しや外部副作用関数を patch してください（news_nlp._call_openai_api / regime_detector._call_openai_api 等）。

バージョン
---------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

最後に
------
本 README はコードベースの主要な使い方・設計意図をまとめたものです。詳細な API ドキュメントや実運用手順（デプロイ、監視ポリシー、運用時の手順）は別途作成を推奨します。質問や補足があれば教えてください。
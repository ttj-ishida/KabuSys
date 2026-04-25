KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的としたマイクロサービス風 Python コードベースです。  
主な責務は次のとおりです。

- 注文・実行管理（ExecutionEngine）
- 監視（System / Trade / Risk の定期チェック、Kill Switch）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- 研究用ファクター計算（DuckDB 上の時系列データを利用）
- AI（OpenAI）を使ったニュースセンチメント / レジーム判定
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度設定 等）

この README はリポジトリ内の主要モジュール群（src/kabusys）に基づく簡易ドキュメントです。

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い、paper_trading 用 DB に記録して本番 DB と分離
  - PID ファイル、停止フラグ（data/stop_requested.flag / data/kill.flag）による制御
- 監視ループ（run_monitoring.py / MonitoringEngine）
  - システム資源（CPU/Mem/Disk）・Execution プロセス生存・データ鮮度のチェック
  - トレードログ監視（滞留注文／約定異常）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件に合致すると data/kill.flag を書き込む）
- 監視 DB 永続化（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理・マイグレーション
- ポートフォリオ構築ライブラリ（portfolio パッケージ）
  - 銘柄選定（スコア順）、等金額・スコア加重の重み計算
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（リスクベース、等分配等）、単元株丸め、集約キャップ処理
- 研究モジュール（research パッケージ）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC（情報係数）、統計サマリ
  - DuckDB 接続を受けて SQL と Python で完結
- AI モジュール（ai パッケージ）
  - ニュースのセンチメント解析（OpenAI を利用、JSON レスポンス想定）
  - 市場レジーム判定（ETF ma200 とマクロニュースセンチメントの合成）
- 設定関連ユーティリティ
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env と config/*.yaml の起動前検証
  - config.Settings: 環境変数取得と型チェック（デフォルト値にフォールバック）
- ツール
  - paper_verification_report: ペーパートレード用 DB を解析して検証レポートを生成

セットアップ手順
----------------

前提
- Python 3.10+（typing 機能を利用）
- pip（パッケージ管理）
- ネイティブライブラリ依存: psutil, duckdb, openai（AI 機能を使う場合）、PyYAML（validate_config の YAML 検証に任意）
- データディレクトリ（デフォルト: data/）とログディレクトリ（デフォルト: logs/）に書き込み権限

インストール（例）
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt がない場合は最低限以下を入れる:
     - pip install duckdb psutil openai
     - （オプション）pip install PyYAML

3. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参考に）

必須環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — AI 機能を使う場合に必要
推奨（デフォルト有り）
- KABUSYS_ENV — execution の挙動を切替（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（paper_trading 用）
- LOG_LEVEL / LOG_DIR — ログ設定

設定の検証
- 作成した .env と config/*.yaml（存在すれば）を検証:
  - python -m kabusys.validate_config
  - エラーがあれば起動前に修正してください。--strict を付けると警告でも非ゼロ終了します。

使い方
------

基本コマンド（モジュールとして実行）
- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 挙動: Settings に従い SQLite / DuckDB に接続。KABUSYS_ENV=paper_trading のときは paper_trading 用 DB に記録し MockBroker を使用。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）
  - 停止: data/stop_requested.flag を作成すると起動中スレッドが停止します。Kill Switch が書き込む data/kill.flag で起動を抑止します。

- 監視ループ
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視は常に production の sqlite_path（Settings.sqlite_path）を使用してログを残します（環境に依存せず監視 DB は本番パス）
  - 停止フラグ: data/stop_requested.flag を作ると監視ループが終了します

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code=1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）

AI 機能
- ニューススコアリング / レジーム判定は OpenAI API を利用します（OPENAI_API_KEY 必須）
- API 呼び出しはリトライ・バックオフの仕組みあり。失敗時はフェイルセーフ（多くの場合 0.0 相当で継続）します
- 実行関数（例）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ
- setup_logging により stdout と日次ローテートログ（logs/<app_name>.log）を出力
- LOG_DIR / LOG_LEVEL でカスタマイズ可能

停止用フラグ（Kill / Stop）
- data/stop_requested.flag — 実行中スレッドを穏やかに停止するためのフラグ（run_execution/run_monitoring が監視）
- data/kill.flag — Kill Switch が書き込む（ExecutionEngine を停止させるためのグローバルフラグ）
- Settings.kill_flag_clear_on_start=1 に設定すると起動時に kill.flag を自動クリア（本番では 0 を推奨）

ディレクトリ構成
----------------

主要な src/kabusys 配下の構成（抜粋）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定取得クラス（Settings）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト

  - execution/              — 実行エンジン関連（Engine、OrderManager、BrokerFactory 等）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル作成・CRUD ヘルパ
    - system_monitor.py     — システム状態 / データ鮮度チェック
    - trade_monitor.py      — 取引ログ監視（滞留注文・約定異常など）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - monitoring_engine.py  — 各モニタを束ねるループ
    - kill_switch.py        — Kill Switch 書き込みロジック
    - alert_manager.py      — （通知管理: LINE など。コードベースに依存）
  - portfolio/
    - portfolio_builder.py      — 候補選定・等重/スコア重み
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
    - position_sizing.py        — 株数計算・集約キャップ
  - research/
    - factor_research.py       — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py   — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — レジーム判定（ma200 + マクロニュース）
  - data/                      — データファイル（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
  - logs/                      — ログ出力ディレクトリ（デフォルト）
  - tools/
    - paper_verification_report.py

データベース・ファイルパス（デフォルト）
- DuckDB: data/kabusys.duckdb  (Settings.duckdb_path)
- 監視 SQLite: data/monitoring.db  (Settings.sqlite_path)
- PaperTrading SQLite: data/paper_trading.db  (Settings.paper_sqlite_path)
- PID / フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag

注意点 / 運用メモ
----------------
- .env は絶対にリポジトリへコミットしない（config_setup 生成スクリプト内にも明記）
- 本番環境（KABUSYS_ENV=live）では LINE 通知等の設定を必ず確認すること
- run_monitoring は監視用 DB に常に「本番用 sqlite_path」を使う設計（環境に依存しない監視ログ）
- paper_trading モードは本番 DB と完全分離する意図で設計されている（PAPER_TRADING_SQLITE_PATH）
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）は research / ai モジュールから参照される。適切に ETL / データ反映された DuckDB が必要
- OpenAI を使う機能ではレスポンス形式や JSON のバリデーションが厳格化されているため、API のバージョン変更に注意

追加情報
--------
- コード内ドキュメント（docstrings）に仕様や設計意図が豊富に書かれています。各モジュールを読むことでより詳細な挙動を把握できます。
- テスト・CI やデプロイ手順はこの README に含まれていません。実運用時はプロセス管理（systemd / supervisor / container）やログローテーション、バックアップ戦略を検討してください。

必要であれば、この README を基に「デプロイ手順」「運用 Runbook（起動/停止/トラブルシュート）」「.env の例ファイル」などを追加で作成します。どれが必要か教えてください。
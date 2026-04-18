README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤ライブラリ兼実行フレームワークです。  
主な機能は以下の通りです。

- データ処理・ファクター計算（DuckDB を使用）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- Execution エンジン（本番・ペーパートレード対応）
- 監視（System / Trade / Risk のポーリングと Kill Switch）
- AI ツール（ニュース NLP によるセンチメント評価 / レジーム判定）
- CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート生成）

主要な設計方針：
- 本番とペーパー（paper_trading）を明確に分離（DB 分離など）
- ルックアヘッドバイアスを避ける設計（date.today() 等に依存しない）
- フェイルセーフ（API エラーや欠損データ時に安全にフォールバック）

機能一覧
--------
- 環境管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - config_setup: 対話式ウィザードで .env を生成・更新
  - validate_config: 起動前チェック（必須環境変数、ファイル、YAML パース等）
- 実行スクリプト
  - run_execution: ExecutionEngine 起動（KABUSYS_ENV により実ブローカ or MockBroker）
  - run_monitoring: SystemMonitor のポーリングループ起動（監視ログ保存）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - KillSwitch によるフラグファイル方式の外部停止指示（data/kill.flag）
  - 監視ログは SQLite（data/monitoring.db）に永続化
- ポートフォリオ
  - 候補選定、等配分・スコア配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap、コストバッファ）
- リサーチ
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI 支援
  - news_nlp.score_news: raw_news を LLM（OpenAI）でセンチメント判定し ai_scores に書込
  - regime_detector.score_regime: ETF MA とマクロセンチメント合成で市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB の指標を集計し検証レポート出力

セットアップ手順
----------------

前提
- Python 3.9+（ソースは typing | future 構文を使用しています）
- SQLite（標準ライブラリ）
- ネットワーク（OpenAI, kabuステーション 等を利用する場合）

1. リポジトリをクローン
   - git clone <repo>
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   最低限必要なパッケージ例:
   - duckdb
   - psutil
   - openai
   - PyYAML（config の YAML 検証に必要。任意）
   例:
   - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt）

4. .env を作成
   - 対話式ウィザードを使う：
     - python -m kabusys.config_setup
   - または手動で .env をプロジェクトルートに作成（例は下記）。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます。

6. データディレクトリ等の作成（必要なら）
   - デフォルトで data/、logs/ はコード側で作成されますが、権限に注意してください。

主要な環境変数（抜粋）
---------------------
必須（起動するコンポーネントにより異なる）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用設定
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）

DB 関連
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視/トレードログ SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（paper_trading 時に使用、デフォルト: data/paper_trading.db）

ペーパー取引関連
- PAPER_FILL_MODE — ペーパートレードの約定挙動: instant | partial | never | reject
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、production は 0 推奨）

実行方法（使い方）
-----------------

1) 環境作成・検証
- .env を作成（config_setup を推奨）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - エラーが無ければ OK。--strict を使えば警告も失敗扱いにできます。

2) 監視ループ起動（SystemMonitor）
- デフォルトで MONITOR_POLL_INTERVAL は 60 秒（秒）
- 環境変数で上書き例: export MONITOR_POLL_INTERVAL=30
- 実行:
  - python -m kabusys.run_monitoring
- 停止:
  - 実行中に Ctrl+C、またはプロジェクトルート/data/stop_requested.flag を作成するとループを終了します。
- 備考:
  - run_monitoring は KABUSYS_ENV に関わらず本番（settings.sqlite_path）を監視 DB として使用します。

3) ExecutionEngine（発注エンジン）起動
- ペーパートレード:
  - KABUSYS_ENV=paper_trading に設定すると MockBrokerClient を使い、data/paper_trading.db に結果を記録します。
- 実行:
  - python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成すると、エンジンに停止が伝わります。
- PID ファイル:
  - data/execution.pid に PID を書きます（デフォルト）。Settings.pid_file_path で変更可能。

4) ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

5) AI / レジーム / その他プログラム的 API
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と日付を渡してニュースセンチメントを ai_scores に書き込みます。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジームを評価して market_regime テーブルへ書き込みます。
- これらはライブラリ API として import して利用できます。

停止・Kill Switch（運用）
------------------------
- 外部から ExecutionEngine を即時停止させたい場合は data/kill.flag に理由テキストを書き込むことで Kill Switch が作動します（Monitoring 側で検出して Execution を停止します）。
- KillSwitch は冪等処理を行い、既に存在する場合は上書きしません。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動でクリアしますが、本番環境では 0 を推奨します。

ログ
----
- ログは logs/<app_name>.log に日次ローテーション（30日保持）で出力されます。コンソール出力は stdout に出力されます。
- setup_logging(app_name="execution") 等で統一的に設定されます。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数設定読み込み
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - data/                    — （実行時に使用する DB / ファイル: data/*.db, data/kill.flag 等）
  - logs/                    — ログ出力先（デフォルト）
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信ロジック、コード内で参照）
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

簡単な .env 例
--------------
以下は例示です。実際の値はセキュアに管理してください（.env は Git コミットしないこと）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KILL_FLAG_CLEAR_ON_START=0

注意事項 / 運用メモ
-------------------
- Process priority 設定（高優先度）を行いますが、OS 権限や環境により設定できない場合があります（警告のみで続行）。
- DuckDB / OpenAI / kabuステーション など外部コンポーネントの接続や API キーの管理は適切に行ってください。
- 本番環境（KABUSYS_ENV=live）での起動前に validate_config で警告・注意点を確認してください（LINE 通知設定等）。
- .env に秘密情報を保存する場合は適切に保護し、リポジトリにコミットしないでください。

貢献 / 開発
------------
- コードはモジュール化されており、ユニットテストやモック注入を行いやすい設計です（OpenAI 呼び出し箇所は差し替え可能）。
- 新機能追加時は config/*.yaml や DB マイグレーションに注意してください（monitoring_db.init_monitoring_db は簡単なマイグレーションを含みます）。

ライセンス
----------
（リポジトリに付与されているライセンスに従ってください）

お問い合わせ
-------------
問題・質問・改善提案がある場合は issue を立ててください。
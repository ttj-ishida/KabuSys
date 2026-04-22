KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を行うための小規模フレームワークです。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視コンポーネント、ポートフォリオ構築、ファクター計算、AI（ニュース NLP / レジーム検出）などのモジュール群が含まれます。設計方針としては：

- DB（DuckDB / SQLite）を用いたデータ蓄積・分析
- 実行環境（本番 / ペーパートレード / 開発）を .env で切替可能
- OpenAI を用いたニュースセンチメント・レジーム判定（任意）
- 監視（System / Trade / Risk）と Kill Switch による安全停止

主な機能
--------
- Execution エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading モード時は MockBroker を使用して data/paper_trading.db に記録
  - PID ファイル管理、停止フラグの監視
- Monitoring ポーリング（run_monitoring.py）
  - システム状態・データ鮮度・トレード状況・リスク監視のロギング
  - モニタリング用 SQLite（data/monitoring.db）へ永続化
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御可能
- 設定ウィザード（config_setup.py）
  - 対話式に .env を生成 / 更新
- 設定検証 CLI（validate_config.py）
  - .env、config/*.yaml、必須環境変数や DB パスを事前チェック
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB を集計し PASS/FAIL 判定するレポートを出力
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ（kabusys.research）
  - momentum / volatility / value 等のファクター計算、特徴量解析（IC 等）
- AI モジュール（kabusys.ai）
  - news_nlp: OpenAI を使ったニュースセンチメント付与（ai_scores へ書き込み）
  - regime_detector: MA とマクロニュースを組み合わせた市場レジーム判定

セットアップ手順
----------------
前提
- Python 3.10+（typing の | や型注釈を使用）
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - openai  （AI 機能を使う場合）
  - PyYAML （validate_config の YAML 検証時に任意）
- （任意）仮想環境の作成と有効化

例: pip でのインストール（requirements.txt は付属していません）
- pip install duckdb psutil openai pyyaml

.env の作成
1. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
2. 作成後、設定を検証
   - python -m kabusys.validate_config
   - 本番相当の厳密チェックは: python -m kabusys.validate_config --strict

データ・ログディレクトリ
- デフォルトの DB / ファイルパス:
  - DuckDB: data/kabusys.duckdb  (環境変数 DUCKDB_PATH で変更可)
  - Monitoring SQLite: data/monitoring.db (SQLITE_PATH)
  - Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- ログ: logs/<app_name>.log（logs ディレクトリを自動作成）
- PID / フラグ:
  - data/execution.pid（実行エンジン PID）
  - data/stop_requested.flag（run_execution/run_monitoring の外部停止フラグ）
  - data/kill.flag（KillSwitch による ExecutionEngine 停止信号）

使い方（実行例）
----------------

1. 環境の準備
   - .env を作成（config_setup）→ validate_config でチェック

2. 監視プロセス起動（ポーリング）
   - MONITOR_POLL_INTERVAL を指定して起動（秒）
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - デフォルトは 60 秒
   - 停止: data/stop_requested.flag を作成するとループが検出して終了します

3. 実行エンジン起動（発注処理）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB（data/paper_trading.db）を使用
   - 実行中に停止を要求する方法:
     - Monitoring の KillSwitch が条件を満たすと data/kill.flag を書き込み、Execution 側で検出して安全停止します
     - 外部から強制停止したいときは data/stop_requested.flag を作成（起動スクリプトが検出して終了）

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

5. AI 系機能（任意、OpenAI API キー必要）
   - news_nlp.score_news や regime_detector.score_regime を利用するには OPENAI_API_KEY を .env に設定
   - 例（スクリプト呼び出し／モジュール呼び出し）:
     - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); score_news(conn, datetime.date(2026,4,1))"

環境変数（主要）
-----------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL (DEBUG/INFO/...)
- OPENAI_API_KEY（AI 機能利用時）
- PAPER_FILL_MODE（paper_trading 時の約定挙動: instant|partial|never|reject）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒）

監視／停止に関する運用メモ
-------------------------
- stop_requested.flag
  - run_monitoring.py / run_execution.py はプロジェクトルート/data/stop_requested.flag を監視します。
  - ファイルが存在すると起動ループを終了します（グレースフルシャットダウン）。
- kill.flag
  - KillSwitch（監視側）がリスク条件を満たした時に data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - KillSwitch は冪等（既存ファイルがあれば上書きしない）。

ディレクトリ構成（主要）
-----------------------
概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env の読み込み・Settings
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/                — 発注関連（Engine, OrderManager, BrokerFactory, Reconciler, RiskManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 操作ラッパー
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文ログ監視（滞留注文など）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — フラグファイルによる停止シグナル
    - monitoring_engine.py    — 各 Monitor を束ねる
    - alert_manager.py        — (アラート送信管理)
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 発注株数算出 / 集約キャップ処理
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — モメンタム/ボラ/バリュー等の計算（DuckDB 利用）
    - feature_exploration.py  — forward returns / IC / summary 等
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）による銘柄別センチメント
    - regime_detector.py      — マクロ + MA で市場レジーム判定（OpenAI 併用）
  - data/                     — （実行時に利用される DB / フラグ / PID を格納する想定）
  - logs/                     — ログファイル（logs/<app_name>.log）

注意事項 / 運用上のヒント
------------------------
- .env は絶対にリポジトリにコミットしないでください（機密情報を含む）。
- validate_config で不足している項目やプレースホルダ値を早期に検出してください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0（自動クリア OFF）にすることを推奨します。
- AI（OpenAI）を使用する処理は外部 API に依存するため、API 制限やコストに注意してください。API 呼び出しはリトライとフォールバックを備えていますが、失敗時は安全側にフォールバックする設計です。
- DuckDB を使ったリサーチは本番 DB の参照のみで副作用を持たないよう設計されていますが、実運用時はバックアップ等の運用手順を確立してください。

ライセンス・バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリに同梱されていない場合があるため、必要に応じて追記してください。

---

その他、README に追加したい項目（実装詳細、API 仕様、開発ガイド、ユニットテストの実行手順など）があれば指示ください。README を用途（運用向け / 開発者向け）に合わせて分割して作成できます。
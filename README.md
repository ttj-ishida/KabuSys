README
====

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。  
モジュール群は主に以下を提供します。

- 注文実行エンジン（ExecutionEngine、paper_trading 対応）
- 監視（System / Trade / Risk のポーリングと Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・サイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI 補助（ニュース NLU によるセンチメント／レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

ライブラリは DB（SQLite / DuckDB）へアクセスし、OpenAI API を使った NLP 処理や psutil を使ったシステム監視などを行います。

主な機能
-------
- Execution:
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory 経由でブローカークライアントを切り替え
  - リスク管理（最大ポジション比率、利用率、ドローダウン等）

- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留やドローダウン監視（ログ格納）
  - KillSwitch: 閾値超過時に data/kill.flag を書き込み Execution を停止
  - MonitoringEngine / run_monitoring.py による定期ポーリング（MONITOR_POLL_INTERVAL）

- Portfolio:
  - 候補選定（スコア降順）、等配分・スコア重み配分
  - セクター制約・レジーム乗数適用
  - ポジションサイズ計算（単元株丸め、aggregated cap のスケーリング）

- Research:
  - ファクター計算（モメンタム/バリュー/ボラティリティ 等）
  - 将来リターン計算、IC（情報係数）、統計サマリー

- AI:
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメント集約と ai_scores への書込
  - regime_detector: MA200 とマクロ記事センチメントを合成して市場レジーム判定

- ツール:
  - config_setup: 対話式に .env を生成・更新
  - validate_config: .env と config/*.yaml を起動前に検証
  - paper_verification_report: ペーパートレード DB から運用検証レポートを生成

セットアップ手順
--------------
前提
- Python 3.10 以上（typing の構文や型ヒントで | を使用）
- システムに依存するパッケージ: duckdb, psutil, openai, PyYAML（任意。設定検証の YAML チェックで使う）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - ない場合の目安:
     - pip install duckdb psutil openai PyYAML

4. 初期設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または .env.example をコピーして編集（リポジトリに存在する場合）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - 実行スクリプト（run_execution / run_monitoring）が内部で必要テーブルを生成します（init_monitoring_db）。
   - DuckDB/SQLite ファイルはデフォルトで data/ 配下に作成されます。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード用）
- LOG_LEVEL: DEBUG/INFO/...
- LOG_DIR: ログ保存先（default: logs）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector などで必要）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
- PAPER_FILL_MODE: instant | partial | never | reject （ペーパートレードの約定モード）

使い方
-----
実行スクリプト
- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで即時ループ終了

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ保存されます
  - 起動時に data/stop_requested.flag が存在する場合は起動しません
  - 実行中に停止させたい場合は data/stop_requested.flag を作成するか、監視側の KillSwitch により data/kill.flag が書き込まれると ExecutionEngine が停止します

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い

ツール
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ライブラリ利用（インポート例）
- ポートフォリオ構築関数:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
- ファクター計算:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
- AI ニューススコアリング:
  - from kabusys.ai import score_news
  - DuckDB 接続と target_date を渡して呼び出す（api_key を引数で渡せる）

ログ
---
- logging_setup.setup_logging を全起動スクリプトで呼んでおり、標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）へ出力します。
- デフォルトで 30 日分を保持します（TimedRotatingFileHandler）。

Kill Switch / 停止フラグ
---------------------
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine 側はこのファイルの存在を検知して停止します（KillSwitch は RiskMonitor の結果等を評価して書き込み）。
- data/stop_requested.flag: 手動停止用フラグ。run_monitoring.py / run_execution.py はこれを監視して即時終了します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合、kill.flag を自動クリアする設定があるため本番では 0 を推奨します。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数/.env の読み込みと Settings クラス
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
- run_execution.py          — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py  — ペーパートレード検証レポート生成
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP -> ai_scores 書き込み
  - regime_detector.py      — 市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite テーブル管理 / 永続化 API
  - monitoring_engine.py    — 各 Monitor 集約（ポーリング）
  - system_monitor.py       — CPU/メモリ/データ鮮度監視
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 書き込みユーティリティ
  - (trade_monitor 等が存在)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py
- execution/                 — Execution 系の実装（OrderManager, Engine, BrokerFactory 等）

注意事項 / 運用上のヒント
------------------------
- 本番環境 (KABUSYS_ENV=live) では LINE 通知の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config にて警告が出ます。
- .env は絶対にバージョン管理にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- OpenAI API を使う処理はレート制限や一時的エラーを考慮してリトライ実装がありますが、API キー管理には注意してください。
- logs ディレクトリや data ディレクトリは起動スクリプトで自動作成されますが、ディスクパスや権限を事前に確認してください。
- ペーパートレード用 DB は本番 DB と分離（設定により paper_trading モード時は PAPER_TRADING_SQLITE_PATH を使用）されています。

ライセンス・貢献
----------------
- 本 README ではライセンス情報は含めていません。リポジトリの LICENSE ファイルを参照してください。
- バグ報告・改善提案は Issue / PR を通じてお願いします。

以上。README の追加要望（例: 実運用例、systemd 設定サンプル、Dockerfile など）があれば追記します。
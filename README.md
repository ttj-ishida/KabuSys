KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株の自動売買・研究・監視を行うための軽量なフレームワークです。
戦略生成、ポートフォリオ構築、発注（実運用／ペーパートレード）、監視・アラート、AI を用いたニュース評価などの機能を含みます。

主な特徴
-------
- Strategy / Research
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン・IC 計算、特徴量探索用ユーティリティ
- Portfolio Construction
  - 候補選定、等金額／スコア加重、リスクベースの単元株数決定
  - セクターキャップ、レジーム乗数などリスク調整ロジック
- Execution
  - 実ブローカー／MockBroker を切り替え可能（KABUSYS_ENV に依存）
  - 発注の管理、リスク制御、再整合処理
- Monitoring
  - システム稼働状態監視（CPU / メモリ / ディスク / プロセス）
  - 発注ログ・リスクログ・ダッシュボード永続化（SQLite）
  - Kill Switch（条件により ExecutionEngine を停止）
- AI / NLP
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント集計（銘柄別スコア）
  - マクロニュースと ETF MA200 を合成した市場レジーム判定
- 運用ツール
  - .env 対話式ウィザード、設定検証 CLI、Paper Trading 検証レポート出力

必要な依存（代表例）
-----------------
最低限の主要パッケージ（一例）：
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config YAML 検証を行う場合）

インストール例:
$ python -m pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそれを利用してください）

セットアップ手順
-------------
1. リポジトリをクローン／配置
   - プロジェクトルートには src/ 以下にパッケージが置かれます。

2. .env の準備（対話式ウィザード推奨）
   - 下記コマンドで .env を対話的に作成できます:
     $ python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な設定:
     - KABUSYS_ENV: development | paper_trading | live
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）

3. 設定検証
   - 自動検証スクリプトで設定をチェックできます:
     $ python -m kabusys.validate_config
   - 警告を厳密扱いにする場合:
     $ python -m kabusys.validate_config --strict

4. データディレクトリ等の作成
   - .env に指定したパスの親ディレクトリが存在するか確認してください（通常は自動作成されます）。
   - ログディレクトリ（デフォルト logs/）は自動生成されます。

使い方（主要コマンド）
-------------------

1. ExecutionEngine の起動（発注エンジン）
   - 本番または paper_trading を切り替えるには KABUSYS_ENV を設定:
     - 本番:
       $ export KABUSYS_ENV=live
       $ python -m kabusys.run_execution
     - ペーパートレード:
       $ export KABUSYS_ENV=paper_trading
       $ python -m kabusys.run_execution
       （paper_trading 時は MockBrokerClient を使い、data/paper_trading.db を使用します）
   - 動作中は data/execution.pid が生成され、停止要求は data/stop_requested.flag で行います。
   - 起動時に data/stop_requested.flag が存在すると起動しません。

2. Monitoring の起動（監視ループ）
   - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
     $ export MONITOR_POLL_INTERVAL=30
     $ python -m kabusys.run_monitoring
   - 監視は常に本番用 sqlite_path を使って monitoring DB を更新します。
   - 停止は data/stop_requested.flag を作成するか、Ctrl+C（KeyboardInterrupt）で行います。

3. Paper Trading 検証レポート
   - ペーパートレード DB に対する検証レポートを生成:
     $ python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

4. AI / レジーム判定・ニュース評価（プログラム的に呼び出し）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - DuckDB 接続を渡して実行します。失敗時はフェイルセーフで継続する設計。

運用上の注意点
--------------
- Kill Switch / stop フラグ
  - KillSwitch はリスクルール（例: ドローダウン超過）を検出すると data/kill.flag を書き込み、
    ExecutionEngine に停止信号を送ります（ExecutionEngine は起動時に kill.flag の自動クリア設定を確認します）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では 0 を推奨します。
- DB 分離
  - paper_trading モードは paper_trading 用 SQLite DB（data/paper_trading.db）を使用し、本番データと分離します。
- ログ
  - 標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- プロセス優先度
  - 起動スクリプトはプロセス優先度を high に設定しようとします（psutil を使用）。権限がない場合は警告が出ます。

ディレクトリ構成（概観）
---------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数 / .env オートロード・Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - Monitoring ポーリングループ起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py        — ニュース NLP による銘柄別スコア
  - regime_detector.py — マクロ + MA200 によるレジーム判定
- monitoring/
  - monitoring_db.py   — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py  — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py   — 発注ログ監視（滞留注文、約定異常 等）
  - risk_monitor.py    — ドローダウン・ポジション上限監視
  - kill_switch.py     — kill.flag 管理
  - monitoring_engine.py — 各 Monitor を束ねてポーリング
  - alert_manager.py   — （アラート送信の抽象レイヤ、LINE等の実装を想定）
- execution/
  - execution_engine.py — 発注エンジン本体（EngineConfig / run_session 等）
  - broker_factory.py   — ブローカークライアント生成（Mock / 実ブローカー）
  - order_manager.py, order_repository.py, risk_manager.py, reconciler.py, ...
- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数決定・単元丸め・aggregate cap
  - risk_adjustment.py      — セクター上限・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（momentum/value/volatility）
  - feature_exploration.py  — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - logging_setup.py     — ログ設定ユーティリティ
  - process_priority.py  — プロセス優先度・CPU affinity ユーティリティ
  - そのほかユーティリティ群

よくある運用フロー（例）
-----------------------
1. .env を作成（config_setup）、必要な API キー等を設定
2. 設定検証を実行（validate_config）
3. DuckDB / SQLite にデータをロード（prices_daily, raw_news, raw_financials 等）
4. ペーパートレードで一日分の処理を回して結果を確認
   - ExecutionEngine（paper_trading）を起動
   - Monitoring を起動して監視・アラートを検証
   - 運用後、tools/paper_verification_report で評価
5. 本番運用に移行する際は KABUSYS_ENV=live に切り替え、kill_flag の取り扱いに注意

開発者向けメモ
--------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- DuckDB 接続は research / ai / regime など多くのモジュールで使用します。大量データの照会は DuckDB 側で最適化してください。
- OpenAI 呼び出しはリトライ・バックオフを入れて堅牢化してありますが、API 利用制限やコストに注意してください。

ライセンス / バージョン
---------------------
パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース参照）。
ライセンス情報が別ファイルにある場合はそちらを参照してください。

問い合わせ / 変更履歴
--------------------
- 実装や設定に不明点があれば、README を更新するかコード内の docstring を参照してください。
- 主要な動作説明は各モジュールの docstring に記載されています（monitoring/*.py, ai/*.py, research/*.py など）。

以上がこのコードベースの概要と運用・セットアップ手順です。必要であれば、README に入れたい追加のコマンド例や設定テンプレート（.env.example 形式）を作成します。どの部分を詳しく書き起こしましょうか？
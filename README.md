README
=====

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。本リポジトリは以下の主要コンポーネントを含みます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行うランタイム
- 監視（Monitoring）: システム状態、注文状況、リスクを定期監視してアラート・Kill Switch を発動
- ポートフォリオ構築（portfolio）: 候補選定、重み付け、リスク調整、ポジションサイズ計算
- リサーチ（research）: ファクター計算、特徴量探索、IC（Information Coefficient）計算等
- AI 補助（ai）: ニュースセンチメント（OpenAI）に基づくスコアリング、レジーム判定
- ユーティリティ（utils）: ロギング設定、プロセス優先度設定、環境設定ローダ等
- 各種ツール（tools）: Paper Trading の検証レポート生成など

特徴
----
- 明確に分離された開発 / ペーパートレード / 本番モード（KABUSYS_ENV）
- Paper Trading 環境では本番 DB と分離された専用 SQLite（data/paper_trading.db）を使用
- ローカルでの .env ウィザード（config_setup）と検証 CLI（validate_config）を提供
- DuckDB を用いた分析・ファクター計算（prices_daily / raw_financials）
- OpenAI を用いたニュース NLP スコアリングと市場レジーム判定（フェイルセーフな設計）
- Monitoring コンポーネントにより稼働率、滞留注文、約定異常、ドローダウンなどを監視し kill.flag を書き込み停止をトリガー
- ロギングは stdout と日次ローテートファイル出力を統一的に設定

セットアップ手順
----------------
1. Python（3.9+ 推奨） をインストールします。

2. 依存パッケージをインストールします（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）。最低限必要となる主なパッケージ例:

   - duckdb
   - psutil
   - openai
   - (オプション) PyYAML（config/*.yaml の検証用）

   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

3. .env を作成します（推奨: 対話式ウィザード）:
   ```
   python -m kabusys.config_setup
   ```
   もしくはプロジェクトルートに .env を直接作成します。.env.example がある場合は参照してください。

   重要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - OPENAI_API_KEY (AI 機能を使う場合必須)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (監視用デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 時の DB: data/paper_trading.db)
   - LOG_LEVEL (DEBUG/INFO/...)
   - LOG_DIR (ログの出力先ディレクトリ)
   - MONITOR_POLL_INTERVAL (監視ループのポーリング間隔 秒、デフォルト 60)

4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。

使い方
------

共通注意
- ログ: kabusys.utils.logging_setup.setup_logging を各起動スクリプトで使っています。ログファイルは既定で logs/<app_name>.log に日次ローテートで出力されます。LOG_DIR で変更可能です。
- 停止制御:
  - run_monitoring.py / run_execution.py はプロジェクトの data/stop_requested.flag を参照してループを終了します（それぞれのスクリプトで参照）。
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine 側で停止をトリガーする仕組みです。
  - ExecutionEngine の PID ファイルは data/execution.pid（設定で変更可）です。

起動スクリプト
- 監視ループを起動する:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関係なく production sqlite_path（SQLITE_PATH）を使用します（監視ログは本番 DB に残す設計）。

- 実行エンジン（ExecutionEngine）を起動する:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）に記録します。本番 DB とは完全に分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。

ツール
- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで SQLite パスを指定できます。デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。

AI 関連
- ニュース NLP スコアリング:
  - kabusys.ai.score_news を用いて raw_news / news_symbols を集約し、OpenAI に問い合わせて ai_scores テーブルに書き込みます。
  - OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で与えてください。
  - レートリミット・ネットワーク障害・5xx を考慮して指数バックオフでリトライします。失敗時は安全にスキップする設計です。

停止・Kill Switch 操作
- 手動で監視 / 実行を停止したい場合:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します。
- KillSwitch が発動した場合:
  - data/kill.flag が書き込まれます（存在すると ExecutionEngine の停止トリガーになる設計です）。
- 実行開始時の Kill Flag 自動クリア:
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

ディレクトリ構成
----------------
（重要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化 / CRUD ヘルパ
    - system_monitor.py      — システム状態・データ鮮度チェック
    - trade_monitor.py       — 注文／約定監視（省略ファイルあり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の作成/管理
    - monitoring_engine.py   — 各 monitor を束ねるエンジン
    - alert_manager.py       — 通知管理（省略ファイルあり）
  - execution/
    - execution_engine.py    — 実行エンジン（EngineConfig/run_session 等）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化
    - risk_manager.py        — リスク管理ロジック
    - reconciler.py          — ブローカ状態と DB の整合
    - broker_factory.py      — BrokerClient の生成（Mock/実ブローカー切替）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数計算・単元丸め・資金配分
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Value/Volatility 計算（DuckDB）
    - feature_exploration.py — 将来リターン/IC/統計サマリー
  - ai/
    - news_nlp.py            — ニュースセンチメントの OpenAI 連携
    - regime_detector.py     — マクロ＋MA200 でレジーム判定（OpenAI 併用）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

データ / ログ
- data/ (既定)
  - monitoring.db            — 監視用 SQLite（SQLITE_PATH）
  - paper_trading.db         — Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）
  - kill.flag                — Kill Switch フラグ（作成: KillSwitch）
  - stop_requested.flag      — 実行ループ停止フラグ（手動用）
  - execution.pid            — ExecutionEngine の PID ファイル（既定）
- logs/
  - execution.log, monitoring.log, ... 日次ローテートで出力

開発上の注意・トラブルシュート
----------------------------
- psutil の処理優先度設定は権限により失敗する場合があります（AccessDenied）。その場合はログで警告が出ますが処理は継続します。
- DuckDB パスや SQLite パスの親ディレクトリが存在しない場合、validate_config は警告を出します。起動スクリプトは必要に応じてディレクトリを作成しますが、書き込み権限が必要です。
- OpenAI の API 呼び出しは外部サービスに依存するため、API キーやレート制限に注意してください。news_nlp.py / regime_detector.py はリトライ・フォールバック（失敗時に 0.0）を実装しています。
- .env は絶対にバージョン管理にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。

貢献・拡張
----------
この設計はモジュール化されており、BrokerClient の差し替え、ポートフォリオ設計の変更、AI モデルの切替、監視閾値の調整などを比較的容易に行えます。テストを追加する際は、外部 API 呼び出し（OpenAI, ブローカー等）をモックすることを推奨します。

ライセンス / バージョン
---------------------
パッケージバージョン: __version__ = 0.1.0（src/kabusys/__init__.py）

最後に
-------
まずは .env を作成し、python -m kabusys.validate_config で設定を検証してください。ローカル検証・ペーパートレードで動作確認を行ってから live 環境での運用を開始することを強く推奨します。必要があれば README を更新してプロジェクト固有の起動手順や運用フローを追記してください。
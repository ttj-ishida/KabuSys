KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視のための軽量フレームワークです。本コードベースは以下の主要機能群を含みます:

- 発注実行エンジン（ExecutionEngine）
- モニタリング / Kill Switch / アラート
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- ニュース NLP（OpenAI を使ったセンチメントスコアリング）
- ペーパートレード検証用レポート生成ツール
- 環境設定ウィザード・設定検証 CLI

主な特徴
--------
- 環境変数 / .env による設定管理（config_setup による対話式作成）
- development / paper_trading / live の実行モード切替
  - paper_trading 時は MockBrokerClient を利用し、本番 DB と分離（デフォルト: data/paper_trading.db）
- DuckDB（分析用）と SQLite（監視・トレードログ）を併用
- OpenAI（gpt-4o-mini）によるニュースセンチメント・レジーム判定（API キー必須）
- モニタリングはプロセス優先度設定、PID/フラグファイル連携、ログとリスクイベントの永続化を備える
- ペーパートレード向けの検証レポート（稼働率、注文成功率、レイテンシ等）

必要な依存（代表例）
------------------
主に次のパッケージが利用されます（環境に合わせてインストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証で optional）

セットアップ手順
--------------
1. リポジトリをクローン / 展開する
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
     （必要なものだけ選んでください）
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主な環境変数:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等
     - PAPER_FILL_MODE（paper_trading の約定振る舞い: instant|partial|never|reject）
5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いしたい場合: python -m kabusys.validate_config --strict

使い方
------

起動関連
- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録する（本番 DB と完全分離）。
    - プロセスは起動時に優先度を high に設定します。
    - data/stop_requested.flag が存在すると自動で停止します。
    - PID ファイルは data/execution.pid（設定で変更可）に書き込まれます。

- モニタリングループを起動:
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用します（監視 DB は常に本番設定の path）。
    - デフォルトでプロセス優先度を high に設定し、SystemMonitor / TradeMonitor / RiskMonitor をポーリングします。

ツール
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が優先され、なければ data/paper_trading.db）

AI 機能
- ニュース NLP（センチメント集計）:
  - kabusys.ai.score_news を呼び出す（内部で OpenAI API を利用）
  - OPENAI_API_KEY が必要
  - 実行例（Python 内から）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="…")
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime 同様に OPENAI_API_KEY 必須

監視・Kill Switch
- Kill Switch は条件（ドローダウン超過、ポジション上限超過等）に達したとき data/kill.flag を書き込みます。
- ExecutionEngine は起動時に kill.flag を検査し、存在すれば起動をスキップします。
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で有効（本番では 0 を推奨）。

ログ / DB / フラグファイル
- データディレクトリの例: data/
  - data/kabusys.duckdb（DuckDB、分析用）
  - data/monitoring.db（SQLite、監視用）
  - data/paper_trading.db（ペーパートレード用、paper_trading モード）
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（手動停止用フラグ）
  - data/kill.flag（Kill Switch 発動時に書き込まれる）

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                   — 環境変数 / .env 自動読み込みと Settings
- config_setup.py             — .env 作成ウィザード（対話式）
- validate_config.py          — 起動前設定検証 CLI

- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — SystemMonitor ポーリング起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                — ニュース記事を OpenAI でスコアリング
  - regime_detector.py         — マクロ+MA200 で市場レジーム判定

- monitoring/
  - monitoring_db.py           — SQLite による監視ログ永続化層
  - system_monitor.py          — システム状態・データ鮮度監視
  - trade_monitor.py           — 注文滞留・約定異常監視
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - monitoring_engine.py       — 各 Monitor を束ねるループ
  - kill_switch.py             — Kill Switch（flag ファイル操作）
  - alert_manager.py           — （アラート送信管理：未掲示の実装部分）

- execution/                   — 発注関連（OrderManager, ExecutionEngine 等）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
  - execution_engine.py
  - order_record.py
  - order_repository.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
  - __init__.py

- utils/
  - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ
  - __init__.py

補足 / 運用上の注意
-------------------
- .env は機密情報（API トークン等）を含むため絶対に Git にコミットしないでください。
- 本番運用（KABUSYS_ENV=live）時は設定を慎重に確認してください（validate_config が guard を出します）。
- OpenAI API を使う機能はコスト・レイテンシが発生します。キーやリトライ設定を運用要件に合わせて調整してください。
- モニタリングは監視 DB のパス（SQLITE_PATH）を参照します。複数環境で DB を分離したい場合は適宜パスを設定してください。
- run_monitoring はデフォルトで本番の monitoring.db（settings.sqlite_path）を使います。テストで別 DB を使いたい場合は環境変数を調整してください。

ライセンス / バージョン
-----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ に定義されています（現状 "0.1.0"）。

お問い合わせ・拡張
-----------------
- 新しいブローカーの追加は execution/broker_factory.py を拡張してください。
- アラート送信先（LINE 等）は config の LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を設定し、alert_manager を実装してください。
- 解析 / レポート機能は research と tools に機能追加する形で拡張できます。

以上。必要であれば README に追加したいコマンド例や .env のサンプルテンプレート（.env.example 形式）を作成します。どの内容を詳しく載せたいか教えてください。
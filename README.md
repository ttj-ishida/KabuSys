KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。戦略・ポートフォリオ構築、発注エンジン、監視、研究ツール、AI（ニュース NLP / レジーム判定）などを含むモジュール群を提供します。本リポジトリは実運用を想定した設計（監視・ログ・Kill Switch・ペーパートレード分離等）になっています。

主な特徴
--------
- ExecutionEngine / Broker クライアントによる発注処理（本番 / ペーパートレード切替）
- Monitoring（System / Trade / Risk）による定常監視とアラート、Kill Switch
- モジュール化されたポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制限
- Research ツール（DuckDB を使ったファクター計算・特徴量探索）
- AI モジュール：ニュースのセンチメントスコアリング（OpenAI）、市場レジーム判定
- 設定ウィザード（.env 生成）と起動前の設定検証ツール
- Paper Trading 検証レポート生成スクリプト

必要条件（例）
--------------
- Python 3.10+（型アノテーションの Union 表記等を使用）
- 追加ライブラリ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の検証を行いたい場合）
例: pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリをプロジェクトルートにする。

2. 仮想環境を作成・有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

4. 環境変数（.env）作成:
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - 生成後、設定の検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります

設定の自動読み込み
------------------
- 起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）から
  .env と .env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効にする:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- PAPER_FILL_MODE（ペーパートレードの約定モード: instant/partial/never/reject、デフォルト: instant）

起動・使い方
------------

1. 監視ループ（Monitoring）
   - 目的: システム状態（CPU/メモリ/ディスク）、データ鮮度、取引ログの監視、Kill Switch 評価など
   - 起動:
     - python -m kabusys.run_monitoring
   - オプション:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
   - 停止:
     - プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

2. 実行エンジン（ExecutionEngine）
   - 目的: ブローカーと連携して注文を出す実行エンジン（本番／ペーパートレード切替対応）
   - 起動:
     - python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて data/paper_trading.db に記録（本番 DB と分離）
     - 起動時に data/stop_requested.flag が既に存在する場合は起動をスキップ
     - 実行中は data/execution.pid に PID を書きます
     - 停止は data/stop_requested.flag を作成するか、実行エンジンの API/管理手段により行います

3. 設定ウィザード / 検証
   - .env 作成:
     - python -m kabusys.config_setup
   - 設定検証:
     - python -m kabusys.validate_config
     - 厳密モード: python -m kabusys.validate_config --strict

4. Paper Trading 検証レポート
   - 目的: ペーパートレード DB を解析して稼働率・注文成功率・レイテンシ等をレポート出力
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
     - DB 指定: --db PATH （省略時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

AI 機能
-------
- ニュース NLP（kabusys.ai.news_nlp.score_news）:
  - raw_news / news_symbols テーブルから記事を集約し、OpenAI にバッチ送信して銘柄ごとに -1.0～1.0 のスコアを算出し ai_scores テーブルへ保存します
  - 使用には OPENAI_API_KEY が必要
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）:
  - ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成し、bull/neutral/bear の判定を行い market_regime テーブルへ記録
  - こちらも OPENAI_API_KEY が必要

監視・Kill Switch
-----------------
- kill.flag（デフォルト: data/kill.flag）を書き込むことで ExecutionEngine に停止信号を送る Kill Switch ロジックを提供します（監視ルール: ドローダウン超過、ポジション上限等）。
- stop_requested.flag（data/stop_requested.flag）を作成すると run_monitoring / run_execution のループが終了します。

ログ
---
- ログは標準出力（stdout）とログファイル（デフォルト logs/<app_name>.log、日次ローテーション）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一管理されます。

内部データ / DB
----------------
- デフォルト DuckDB: data/kabusys.duckdb
- デフォルト 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db
- 監視 DB スキーマ / 永続化ロジックは kabusys.monitoring.monitoring_db に実装

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys をプロジェクトの Python パッケージルートとした構成の抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視 DB 永続化層
    - system_monitor.py
    - trade_monitor.py       — （トレード監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート配信ロジック）
  - execution/
    - execution_engine.py    — ExecutionEngine 実装
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

開発・運用上の注意
------------------
- .env は秘密情報を含むため絶対に Git にコミットしないこと（config_setup はその旨を明記して .env を生成します）。
- KABUSYS_ENV を live にすると本番モードになります。validate_config は live 時に追加の注意を促します（LINE通知設定や Kill Switch 設定等）。
- Monitoring は本番用の sqlite_path を環境にかかわらず参照します（run_monitoring 内の動作）。
- Paper trading は DB を分離しているため、本番 DB に影響を与えません（run_execution 内の切替）。
- AI 機能は外部 API（OpenAI）使用に伴うコストとレート制限に注意してください。リトライやバッチ処理ロジックは実装されていますが、API キーの管理は運用者の責任です。

トラブルシューティング（簡易）
-----------------------------
- 設定検証でエラーが出る:
  - python -m kabusys.validate_config を実行してメッセージを確認
- ログファイルが作成されない:
  - logs/ ディレクトリの作成権限を確認。ログディレクトリ作成に失敗した場合はコンソール出力のみになります
- AI 機能が OpenAI に接続できない:
  - OPENAI_API_KEY を設定しているか、ネットワーク接続と API 利用制限を確認

ライセンス / 貢献
-----------------
（この README にライセンス情報は含めていません。実際のリポジトリでは LICENSE を追加してください。）

最後に
------
この README はコードベースの主要なポイントをまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。質問や補足があれば教えてください。
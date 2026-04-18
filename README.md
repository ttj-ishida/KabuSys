KabuSys — 日本株自動売買システム (README)
====================================

概要
--
KabuSys は日本株向けの自動売買／リサーチ基盤です。価格・財務データを DuckDB/SQLite に保持し、シグナル生成、ポートフォリオ構築、発注エンジン、監視、リスク管理、ニュースNLP によるセンチメント評価などのコンポーネントを備えます。本リポジトリはパッケージ化された Python モジュール群として実装されています（src/kabusys/*）。

主な機能
--
- ExecutionEngine（発注実行）
  - 本番／ペーパートレード両対応（KABUSYS_ENV に依存）
  - ブローカークライアントの抽象化と注文管理、リスク管理、照合処理
- Monitoring（監視）
  - システム状態（CPU/メモリ/ディスク）、プロセス生存、データ鮮度のポーリング
  - トレードログ・リスクログの永続化（SQLite）
  - Kill Switch（閾値違反で停止フラグを書き込み）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分／スコア加重、ポジションサイズ計算、セクター上限適用、レジーム乗数
- Research（ファクター算出・特徴量解析）
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB 上で SQL 実行）
  - IC（Information Coefficient）や将来リターンの算出ユーティリティ
- AI（ニュース NLP / レジーム判定）
  - OpenAI API を用いたニュースセンチメントスコアリング（ai_scores テーブルへ保存）
  - ETF + マクロニュースを合成した市場レジーム判定（market_regime への書き込み）
- ツール
  - .env 対話式セットアップウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
- 共通ユーティリティ
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度・CPU affinity の設定ユーティリティ

セットアップ手順
--
1. リポジトリをクローン／取得し、仮想環境を作成・有効化します（例）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（プロジェクトに requirements ファイルがあればそれを使用）。
   - pip install duckdb psutil openai
   - （YAML 検証を利用する場合）pip install pyyaml

   注: 実運用では kabuステーション API クライアント等の依存モジュールが別途必要になる場合があります。

3. 環境変数の設定
   - プロジェクトルートに .env を置くことで自動読み込みされます（.env は Git にコミットしないでください）。
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 必須環境変数例:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
   - 主要な環境変数（デフォルト値を併記）
     - KABUSYS_ENV: development | paper_trading | live （default: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: INFO
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で利用）
     - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定振る舞い）

4. データディレクトリ
   - data/（デフォルト）
     - monitoring.db（SQLite, 監視ログ）
     - paper_trading.db（ペーパートレード時の分離 DB）
     - kill.flag（Kill Switch 用）
     - stop_requested.flag（手動停止用フラグ）
     - execution.pid（ExecutionEngine の PID 管理）
   - logs/（デフォルトでログファイルを保存）

5. DB 初期化
   - run_execution / run_monitoring の起動時に monitoring DB の初期化 (init_monitoring_db) が行われます。事前に手動で作成する必要はありません。

使い方（主要スクリプト・CLI）
--
- 環境ウィザード（.env の対話式作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告をエラー扱いにするには --strict を付与:
    - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録します（本番 DB と分離）。
  - 停止: data/stop_requested.flag を作成すると実行中のエンジンが段階的に停止します。Kill Switch により data/kill.flag が書かれると起動を阻止する場合があります。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は monitoring DB（Settings.sqlite_path）へ書き込みます（KABUSYS_ENV に依らず本番 sqlite_path を使用する動作に注意）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI/レジーム関連（ライブラリ API として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、内部で ai 書き込みを行います。OPENAI_API_KEY を環境変数または引数で与えてください。

- ログ設定
  - 全起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出して統一的ログ管理を行います（stdout + 日次ローテーションファイル）。

停止フラグ・Kill Switch
--
- stop_requested.flag（data/stop_requested.flag）
  - 管理者が作成すると run_execution / run_monitoring のループが検知して安全に終了します。
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）
  - Monitoring の KillSwitch によりリスク閾値超過時に書き込まれ、ExecutionEngine の起動を阻止したり停止を促します。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動削除されますが、本番では 0 推奨。

ディレクトリ構成（主要ファイル）
--
- src/kabusys/
  - __init__.py
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト
  - config.py — Settings クラス（環境変数読み込み、自動 .env ロード）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で銘柄別センチメント算出
    - regime_detector.py — レジーム判定（ETF MA + マクロセンチメント合成）
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py — （取引ログ監視、該当ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込み・評価
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py —（アラート送信ロジック）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・単元丸め・キャップ処理
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/（実行時に生成・利用）
    - *.db, *.pid, kill.flag, stop_requested.flag 等

設計上の注意点 / 運用上のポイント
--
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- KABUSYS_ENV による挙動差分:
  - paper_trading: 発注はモック（MockBrokerClient）、DB は paper_trading.db に分離されます。
  - live: 本番挙動（外部 API 呼び出し・実際の発注）
- Monitoring は環境に依らず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（設計上の挙動なので注意）。
- OpenAI を用いる機能は API の安定性に依存します。API キー、レート制限、エラーハンドリング（内部的にリトライ実装あり）を確認してください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗したときはコンソールのみ出力にフォールバックします。

トラブルシュート
--
- validate_config によって起動前に設定不備（未設定の必須環境変数やファイルパスの親ディレクトリがない等）を検出できます。まずこれを実行してください。
- run_execution / run_monitoring が即終了する場合、data/stop_requested.flag や data/kill.flag の存在を確認してください。
- DuckDB / SQLite のパスは Settings（環境変数）から確認できます（DUCKDB_PATH/SQLITE_PATH）。

開発者向けメモ
--
- DuckDB 接続を受け取ってデータを処理するパターン（research, ai）は単体テストしやすい設計です。
- LLM/API 呼び出し部分は個別の _call_openai_api をモックすることでユニットテスト可能です。
- monitoring_db.init_monitoring_db() は冪等なので起動時に常に呼んで問題ありません（マイグレーション処理を含む）。

ライセンス・貢献
--
（ここにライセンス・貢献の指針を追記してください）

以上。初期セットアップや運用に関して質問があれば、どの点を詳しく知りたいか教えてください。
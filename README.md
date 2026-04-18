KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買 / 監視 / 研究を目的とした小規模なフレームワークです。  
主な要素は ExecutionEngine（発注実行）, Monitoring（稼働・取引監視）, Portfolio / Position sizing / Risk 管理, Research（ファクター計算）, AI 支援（ニュース NLP / レジーム判定）などです。

概要
----
KabuSys は複数の独立コンポーネントで構成されます:

- 実行（Execution）
  - Market API（kabuステーション）またはモック（ペーパートレード）を使って発注を行う ExecutionEngine
  - Order 管理・リスクチェック・reconciler などを含む
- 監視（Monitoring）
  - システム稼働、データ鮮度、滞留注文、ドローダウン等を定期チェックして SQLite にログを残す
  - アラート発行や Kill Switch（停止フラグ）作成
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- 研究（Research）
  - DuckDB 上の価格・財務テーブルを参照してファクターや将来リターン、IC 等を計算
- AI（OpenAI）
  - ニュースを LLM でスコアリング（news_nlp）
  - マクロニュース + ETF MA を用いて市場レジーム判定（regime_detector）
- ユーティリティ / ツール
  - .env ウィザード（config_setup）、設定検証（validate_config）、ペーパートレード検証レポート生成ツール（paper_verification_report） 等

主な機能一覧
--------------
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper 用 DB（data/paper_trading.db 等）に分離して記録
- Monitoring ポーリングループ（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング周期を変更可能（デフォルト 60 秒）
  - 監視ログは SQLite（settings.sqlite_path）に永続化（monitoring_db.init_monitoring_db）
- 設定ウィザード（python -m kabusys.config_setup）
  - .env の生成／編集を対話式で支援
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env や config/*.yaml の存在・整合性チェック（--strict オプションで警告も失敗扱い）
- Research / Feature modules
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic 等
- AI モジュール
  - news_nlp.score_news（OpenAI API を用いたニュースセンチメント）
  - regime_detector.score_regime（マクロセンチメント + MA によりレジーム判定）
- MonitoringDB（SQLite）永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
- ツール: paper_verification_report（ペーパートレード検証レポート出力）

セットアップ手順
----------------
以下は基本的なセットアップ手順の例です。実行環境 (OS/パッケージ) に応じて調整してください。

1. Python
   - Python 3.10+ を推奨（ソースは型ヒント等を使用）
2. 仮想環境の作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリのインストール
   - 必須（コードから読み取れる主要依存）:
     - duckdb, psutil, openai
   - オプション:
     - PyYAML（config/*.yaml の構文チェック用）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （リポジトリに requirements.txt があればそれを利用）
4. プロジェクトルートで初期ディレクトリ作成
   - mkdir -p data logs
5. .env の準備
   - python -m kabusys.config_setup を実行して対話的に .env を作成するのが簡単です。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env を Git にコミットしないでください（README 内でも強調）
6. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は指示に従って修正

主要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行モード:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: 発注はモック、paper_sqlite_path を使用
    - live: 本番発注（注意して使用）
- DB / ログ:
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB, デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite）
  - LOG_LEVEL（DEBUG/INFO/...）
  - LOG_DIR（ログ出力先）
- AI:
  - OPENAI_API_KEY（news_nlp / regime_detector で使用）
- その他:
  - PID_FILE_PATH（実行時の pid ファイル path）
  - KILL_FLAG_PATH（kill.flag の場所）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング周期（秒））

使い方（実行例）
----------------

1. .env を作成・設定
   - python -m kabusys.config_setup
   - 設定後、python -m kabusys.validate_config でチェック

2. 監視プロセスを起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL を任意秒数に設定可能（例: export MONITOR_POLL_INTERVAL=30）
   - run_monitoring は監視 DB 接続と DuckDB 接続を作成し SystemMonitor のポーリングを開始します
   - 停止: data/stop_requested.flag を作成するとループが終了します（または Ctrl+C）

3. Execution Engine を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_sqlite_path に書き込むので本番 DB と分離されます
   - 停止: data/stop_requested.flag を作成するか、ExecutionEngine が内部で kill.flag を検知すると停止します

4. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db でデータベースパスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

5. AI モジュール実行（プログラムから呼ぶ）
   - news_nlp.score_news(duckdb_conn, target_date, api_key=...)
   - regime_detector.score_regime(duckdb_conn, target_date, api_key=...)
   - OPENAI_API_KEY が必要（引数で渡すことも可）

停止 / Kill Switch
------------------
- Stop flag (run_* の停止ループ用)
  - data/stop_requested.flag を存在させると run_monitoring / run_execution のループが検知して停止します
- Kill Switch（ExecutionEngine 停止シグナル）
  - kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を書くと ExecutionEngine に停止シグナルを送ります
  - KillSwitch クラスは risk monitor の結果に基づき kill.flag を書きます（ドローダウンやポジション上限など）
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動で kill.flag をクリアします（本番では 0 推奨）

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では設定ミスが致命的になり得るため validate_config の警告を必ず確認してください
- OPENAI API キー（商用 LLM）はコスト・レイテンシと結果の不確実性に注意して使用してください
- ログ出力は logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリのディスク容量を監視してください
- プロセス優先度設定（psutil 経由）や CPU affinity など実行環境依存の箇所は権限により失敗することがあります（警告を出してスキップ）

ディレクトリ構成（抜粋）
------------------------
（ソースは src/kabusys 以下に配置される前提）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数の抽象化、.env 自動ロードなど
  - config_setup.py
    - .env の対話式作成ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py — システム・データ鮮度チェック
    - trade_monitor.py — (取引監視: 滞留注文・約定異常等) ※ファイル内に実装あり
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 monitor を束ねるエンジン
    - alert_manager.py — 通知（LINE 等）管理（実装箇所あり）
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
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
  - monitoring/ (上に記載)
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足（開発者向け）
-----------------
- DuckDB を用いた分析処理はメモリ上で高速に実行できます。prices_daily / raw_financials 等のテーブル設計に従ってデータをロードしてください
- テストを書いてモック化する際は、AI 呼び出し部分（_call_openai_api）や外部プロセス影響部分（psutil）をパッチすることを想定しています
- データベースのマイグレーションは monitoring_db.init_monitoring_db 内でも簡易サポートされています（カラム追加等）

ライセンス / バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）
- ライセンス情報はリポジトリルートに LICENSE ファイルを置いてください（本 README には含めていません）

最後に
------
この README はソースコードから読み取れる設計意図と実行フローを基に作成しています。実運用前には必ずローカルでの動作確認、設定検証（python -m kabusys.validate_config）、およびステージ環境での試運転を行ってください。必要であれば README に追記してほしい項目（詳しい設定例、systemd ユニット、Dockerfile 例など）を教えてください。
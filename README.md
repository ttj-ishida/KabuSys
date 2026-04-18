KabuSys
=======

日本株向けの自動売買・研究プラットフォーム（軽量版）。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視システム（Monitoring）、研究・ファクター計算、ポートフォリオ構築、AI（ニュースNLP / レジーム判定）などの主要コンポーネントを含むモジュール群で構成されています。

概要
----
KabuSys は以下の責務を持つモジュール群から成ります。

- Execution: 発注ロジック、注文管理、リスク管理、ブローカークライアントの抽象化
- Monitoring: システム状態・注文状態・リスクを定期的に監視し、kill flag を書く等でエンジン停止を誘導
- Research: DuckDB 上の時系列データに対するファクター計算・将来リターン分析・IC 計算
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限など純粋関数群
- AI: OpenAI を用いたニュースのセンチメント付与（news_nlp）・市場レジーム判定（regime_detector）
- Tools: ペーパートレード検証レポート生成などのユーティリティスクリプト
- Utils: ロギング設定、プロセス優先度設定、環境設定読み込みなど共通ユーティリティ

主な機能
--------
- ExecutionEngine
  - 本番/ペーパートレード切替（KABUSYS_ENV）
  - リスク管理（最大ポジション率、利用率、ドローダウンなど）
  - BrokerClientFactory によるブローカー実装切替（paper_trading では Mock を使用）
- Monitoring
  - CPU / メモリ / ディスク / プロセス生存チェック
  - 注文滞留、約定異常、リスクイベントのログ化（SQLite）
  - Kill Switch による安全停止（data/kill.flag）
  - MONITOR_POLL_INTERVAL によるポーリング間隔調整
- Research / Portfolio
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 経由）
  - ポートフォリオ候補選定・重み付け・株数決定・セクターキャップ等
- AI
  - OpenAI（gpt-4o-mini想定）を用いたニュースセンチメント付与
  - マクロ記事 + ETF MA200 を合成した市場レジーム判定
  - APIエラーに対するリトライ・フェイルセーフ設計
- Tools
  - ペーパートレード検証レポート生成スクリプト（Paper Trading の評価基準を出力）

必須要件（概略）
----------------
- Python 3.9+
- 以下主要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml のパース検証に使用）
- SQLite（Python 標準ライブラリの sqlite3 を利用）
- ネットワーク接続（本番で API を使う場合）

セットアップ手順
----------------

1. リポジトリをクローン / 展開
   - この README と同じ階層に src/ 配下のパッケージが存在することを想定しています。

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（例）
   ```
   pip install duckdb psutil openai
   # 開発時は PyYAML も:
   pip install pyyaml
   ```

4. データ・ログディレクトリ作成
   ```
   mkdir -p data logs
   ```

5. 環境変数設定
   - .env を使う場合はプロジェクトルートに .env を配置します。`.env` は絶対にコミットしないでください。
   - 対話式ウィザードで .env を生成する:
     ```
     python -m kabusys.config_setup
     ```
   - 主要な必須環境変数
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - その他（任意／デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
     - LOG_LEVEL — デフォルト INFO
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番通知用（任意）
     - PAPER_FILL_MODE — paper_trading の約定挙動（instant / partial / never / reject）
     - MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring 用、デフォルト 60）

6. 設定検証（起動前の推奨ステップ）
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにする:
   python -m kabusys.validate_config --strict
   ```

使い方（実行例）
----------------

- ExecutionEngine を起動（デフォルトは設定された KABUSYS_ENV に従う）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動中に data/stop_requested.flag を作成するとエンジンは停止します。
  - PID ファイルは data/execution.pid（デフォルト）に書き出されます。

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番の sqlite_path を使用して監視ログを記録します（KABUSYS_ENV に関係なく）。
  - 停止フラグ: data/stop_requested.flag を作成するとループを終了します。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB パスは data/paper_trading.db。--db で上書き可能。
  ```

- AI 機能（スクリプト経由または Python から呼び出し）
  - news_nlp.score_news / ai.score_news を Python から呼ぶ（DuckDB 接続を渡す）
  - regime_detector.score_regime も同様に呼び出せます
  - 例（簡略）:
    ```
    import duckdb, datetime
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, datetime.date(2026,4,1), api_key='sk-...')
    ```

重要なファイル / フラグ
---------------------
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine がこれを見て停止）
- data/stop_requested.flag — run_*.py スクリプトが監視している停止フラグ（即時プロセス終了に使用）
- data/execution.pid — ExecutionEngine の PID ファイル
- logs/<app_name>.log — 日次ローテーションされるログ（logs ディレクトリ）

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys 配下）
- __init__.py
- config.py — 環境変数 / Settings 管理（自動 .env ロードロジック含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリング起動スクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py — ニュースの LLM によるセンチメント付与
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py
- execution/ (発注に関する実装群)
- portfolio/
  - portfolio_builder.py, risk_adjustment.py, position_sizing.py
- research/
  - factor_research.py, feature_exploration.py
- utils/
  - logging_setup.py — 統一的ログ設定
  - process_priority.py — プロセス優先度／CPU affinity 設定
- tools/
  - paper_verification_report.py

注意事項 / トラブルシュート
-------------------------
- .env は決してリポジトリにコミットしないでください（秘密鍵やトークンを含みます）。
- Monitoring は sqlite_path（デフォルト data/monitoring.db）を使用します。paper_trading 時にも監視 DB は共有される点に注意してください（run_execution は paper_trading 時に paper_sqlite_path を使って注文履歴を分離します）。
- process_priority の適用には OS 権限が必要な場合があります（psutil の AccessDenied などの例外は警告扱いでスキップされます）。
- OpenAI 関連は API キーとネットワーク接続が必須。API のレスポンス形式変更や料金に注意してください。
- DuckDB / psutil / openai の各外部ライブラリはインストールしてください。config の YAML 検証に PyYAML を使います（無くても動作しますが検証はスキップされます）。

開発・拡張のヒント
------------------
- research / portfolio モジュールは副作用がない純粋関数中心の設計なので単体テストを書きやすいです。
- AI モジュールの API 呼び出しはラップされているため unittest.mock で差し替えてテスト可能です（コード中にテストフレンドリーな注記あり）。
- データベーススキーマ変更は monitoring_db.init_monitoring_db 内で後方互換的にマイグレーション処理を行っています。新カラム追加時は同様のガードを追加してください。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"
- ライセンス情報は本リポジトリの LICENSE を参照してください（プロジェクトに含めてください）。

補足
----
この README はコードベースから抽出した設計意図・使い方の簡易ガイドです。各モジュールには docstring と注釈が多く記載されていますので、詳細な挙動やパラメータは該当モジュールファイルを参照してください。
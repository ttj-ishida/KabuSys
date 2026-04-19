README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なシステムです。
主要コンポーネントは次のとおりです。

- ExecutionEngine: 発注ロジックと注文管理（paper_trading モードではモックブローカーを使用）
- Monitoring: システム稼働状況、注文ログ、リスク監視、Kill Switch の評価と通知
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算などの純粋関数群
- Research / AI: DuckDB を用いたファクター計算、LLM を用いたニュースセンチメント／レジーム判定
- Tools: ペーパートレード検証レポート等のユーティリティスクリプト
- 設定管理: .env ウィザード（config_setup）と設定検証ツール（validate_config）

特徴
----
- 環境ごとに挙動を切替可能（development / paper_trading / live）
- paper_trading（ペーパートレード）は本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用 DB として採用し、prices_daily / raw_financials 等のテーブルでファクター計算
- OpenAI（gpt-4o-mini 想定）を利用したニュースセンチメント評価とレジーム判定（API キー必須）
- SQLite（監視用）に稼働ログ・注文ログ・リスクログを永続化
- kill.flag による外部からの停止指示、stop_requested.flag によるプロセス停止制御
- ログ出力は統一的に setup_logging で管理（stdout + 日次ローテートファイル）

必須・推奨依存ライブラリ
-----------------------
主に以下を利用しています（バージョンはプロジェクト側で管理してください）。

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証に任意）
- sqlite3（標準ライブラリ）
- その他：logging, threading, datetime（標準）

インストール例（venv を推奨）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール（例）
  - pip install duckdb psutil openai pyyaml

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境作成・依存関係インストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb psutil openai pyyaml

3. .env を作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードが対話的に .env を生成・更新します。
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 参考: デフォルトの DB パスは
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

4. 設定検証（起動前に必須項目をチェック）
   - python -m kabusys.validate_config
   - 注意: --strict を付けると警告も失敗扱いになります。

使い方（基本コマンド）
--------------------
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作モードは環境変数 KABUSYS_ENV を参照（development / paper_trading / live）。
    - paper_trading: モックブローカーを使用し、PAPER_TRADING_SQLITE_PATH に記録します。
  - プロセス優先度は起動時に "high" に設定されます（可能な場合）。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に上書き可（デフォルト 60 秒）。
  - 監視は .env の環境に依らず production の sqlite_path（デフォルト data/monitoring.db）を使用します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 優先度は --db > 環境変数 > デフォルト）

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を参照して ai_scores を書き込みます。
    - api_key を与えない場合は環境変数 OPENAI_API_KEY を使用。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA 等とマクロ記事の LLM 評価を合成して market_regime テーブルへ書き込む。

停止・Kill Switch
-----------------
- 実行中の ExecutionEngine を外部から停止するには、KillSwitch を使って data/kill.flag を作成します。
  - kill.flag の作成は KillSwitch クラス経由で行います（monitoring コンポーネントが条件評価して書き込みます）。
  - run_execution や run_monitoring は data/stop_requested.flag の存在を検知すると終了します。

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging で統一的に設定されます。
  - stdout（StreamHandler） + 日次ローテートファイル（logs/<app_name>.log）
  - LOG_DIR 環境変数でログディレクトリを変更可
  - LOG_LEVEL 環境変数でログレベルを変更可

設定項目（主な環境変数）
----------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 便利
  - KABUSYS_ENV: development | paper_trading | live（default: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - LOG_DIR: ログ保存先ディレクトリ
  - OPENAI_API_KEY: OpenAI API キー（AI 機能）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

主要ディレクトリ構成
-------------------
（リポジトリのルートに src/ を置く前提の構成）

- src/kabusys/
  - __init__.py
  - config.py                 — .env 自動ロード・Settings 管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (※概要のみ: 注文監視)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (※アラート送信実装)
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                 — ExecutionEngine と注文管理まわりの実装（ブローカーファクトリ等）
  - data/                      — スキーマ・パイプライン関連（DuckDB 関連ユーティリティ等）

設計上の注意点・運用メモ
-----------------------
- paper_trading モードは本番 DB と分離しているため、ペーパートレード結果は data/paper_trading.db に記録されます。
- AI モジュールは OpenAI API に依存します。API 使用時はレート制限・コストを考慮してください。API 呼び出しはリトライやフェイルセーフが組み込まれていますが、API キーの設定は必須です。
- モジュールの多くは DuckDB 接続・SQLite 接続を外部から注入する設計です（テストや部分実行がしやすい）。
- run_execution/run_monitoring は start/stop フラグ（data/stop_requested.flag, data/kill.flag）によって外部制御できます。運用時は .env の KILL_FLAG_CLEAR_ON_START 設定に注意（本番では 0 推奨）。

開発・デバッグ
--------------
- 個別関数は pure な計算関数（portfolio や research）と外部副作用を持つ関数（DB 書き込みや API コール）に分かれています。ユニットテストは純粋関数を中心に書くと良いです。
- AI 呼び出し部分（_call_openai_api 等）はテスト時に patch / mock しやすいよう分離されています。
- DuckDB / SQLite を用いたローカルデバッグが可能です。必要なテーブルやサンプルデータは scripts 等で用意してください。

ライセンス・貢献
----------------
- 本 README ではライセンス情報を記載していません。リポジトリに LICENSE ファイルを追加してください。
- バグ報告や機能改善は Issue / Pull Request を通じてお願いします。

以上が簡易 README です。必要に応じて「セットアップ用 requirements.txt」や「起動/デプロイの systemd unit / docker-compose 例」等の追加ドキュメントを作成できます。どの情報を優先して補足しましょうか？
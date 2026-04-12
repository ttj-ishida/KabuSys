KabuSys — 日本株自動売買システム
===============================

このリポジトリは日本株向けの自動売買システム「KabuSys」のコア実装（注文実行、監視、ポートフォリオ構築、リサーチ、AI ニュース解析など）を含みます。README はコードベース（src/kabusys 以下）を参照して作成しています。

プロジェクト概要
----------------
KabuSys は以下の主要コンポーネントで構成される自動売買フレームワークです。

- Execution: ブローカーとのやり取り、注文生成・送信・状態同期、リコンシリエーション（再起動後復旧）
- Monitoring: システム監視、注文監視、リスク監視、アラート（LINE）およびダッシュボード（Streamlit）
- Portfolio: 銘柄選定、配分（等分・スコア重み）、リスク調整、ポジションサイズ決定
- Research: DuckDB ベースのファクター計算・特徴量分析（モメンタム、ボラティリティ、バリュー等）
- AI: ニュースを LLM（OpenAI）でスコアリングし、レジーム判定を行うモジュール
- Tools: Paper Trading の検証レポート生成スクリプト等

主な特徴
--------
- 実運用 / Paper Trading の環境分離（KABUSYS_ENV により動作モードを切替）
- DuckDB を利用したリサーチ（prices_daily / raw_financials 等）
- SQLite を用いた監視ログ（monitoring.db）および paper_trading 用 DB（data/paper_trading.db）
- OpenAI API を用いたニュースセンチメント評価（フェイルセーフ・リトライ実装）
- LINE Push によるアラート送信（cooldown を保持）
- Streamlit による監視ダッシュボード（read-only で DB を開いて表示）
- PID / kill.flag による実行エンジン監視と外部停止信号

セットアップ手順（開発環境）
--------------------------
以下は最小限のセットアップ例です。プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを優先してください。

1. Python（推奨: 3.10 以上）を用意する

2. 必要パッケージをインストール
   - 最小例:
     pip install duckdb psutil requests openai streamlit

   （プロジェクト固有の追加依存がある場合は pyproject.toml / requirements.txt を参照してください）

3. プロジェクトルートに .env（または .env.local）を配置
   - Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索して決定）から .env を自動読み込みします。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 主要環境変数（代表例）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（任意）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の約定振る舞い（instant | partial | never | reject）
   - PID_FILE_PATH / KILL_FLAG_PATH: 実行管理用ファイルパス
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用）

   例 .env（最低限の雛形）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

初期化・DB
----------
- monitoring DB のテーブル作成は init_monitoring_db() により冪等的に実行されます。run_monitoring.py / run_execution.py が起動時に自動で実行します。
- DuckDB（prices_daily / raw_financials 等）はデータ投入が必要です（リサーチ機能の前提データ）。
- Paper Trading モード（KABUSYS_ENV=paper_trading）では paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番監視 DB とは分離されます。

実行方法
--------
- 実行エンジン（注文実行）
  - 実行コマンド（パッケージとして起動）:
    python -m kabusys.run_execution
  - 説明:
    実際にブローカークライアントを生成して ExecutionEngine を起動します。KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、注文情報は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。

- 監視ループ（SystemMonitor 単体の簡易起動スクリプト）
  - 実行コマンド:
    python -m kabusys.run_monitoring
  - 環境変数:
    MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 備考:
    Monitoring は設定されている環境にかかわらず本番 sqlite_path を使用します（監視ログは常に指定の monitoring DB に保存されます）。

- Streamlit ダッシュボード（監視ビュー）
  - 実行コマンド:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    読み取り専用モードで監視 DB を開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート
  - 実行コマンド:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    または
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 説明:
    指定期間の稼働率・注文成功率・レイテンシ等の集計と PASS/FAIL 判定を標準出力へ出力します。

重要な挙動・運用注意
-------------------
- KABUSYS_ENV により実行モードが変わります。paper_trading は本番 DB とは完全分離されるよう設計されています。
- OpenAI 関連の処理は API キーを要求します。API 呼び出しはリトライやフェイルセーフ（失敗時は中立値で継続）を組み込んでいますが、API キーの保護とコスト管理に注意してください。
- 実行中のプロセス優先度は起動直後に set_process_priority("high") で可能な範囲で高優先化します（プラットフォーム依存・権限により失敗する場合あり）。
- Execution 側の停止トリガーは data/kill.flag の作成（KillSwitch）により行われます。kill.flag は既存の場合は書き換えない（冪等）ため、必要に応じて手動で削除してください。Settings.kill_flag_clear_on_start=1 を設定すると起動時に自動削除できます。
- monitoring では system_status / trade_logs / positions / risk_logs / dashboard を管理します。マイグレーション（カラム追加）は init_monitoring_db() にて簡易的に対応しています。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 以下の主要ファイル・モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込み
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — マーケットレジーム判定（MA200 + LLM）
  - monitoring/
    - monitoring_db.py           — SQLite ベースの監視 DB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - （他：broker_factory, execution_engine, order_repository 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py

（上記はリポジトリの一部抜粋です。実際の全ファイルは src/kabusys 以下を参照してください。）

開発・貢献
----------
- 新機能追加やバグ修正は Pull Request をお願いします。
- テストは各モジュール単位で行ってください（モックを活用して外部 API 呼び出しを切り離す設計になっています）。
- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから読みます。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス
----------
（ここには実際のライセンス表記を入れてください。例: MIT LICENSE など）

付記（実装に関するメモ）
----------------------
- 多くの関数は「純粋関数」または副作用を限定する設計で書かれており、ユニットテストしやすくなっています。
- DuckDB を用いたリサーチモジュールは SQL と Python を組み合わせて高速に集計・ファクター計算を行います。
- AI モジュールは OpenAI SDK（chat completions）を用います。API レスポンスのバリデーションやリトライロジックが実装されています。

問題や不明点があれば、どのコンポーネント（例: 実行エンジン、監視、AI、リサーチ）についてかを教えてください。具体的な実行コマンドや .env サンプルの作成もお手伝いします。
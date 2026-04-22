KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした軽量な Python コードベースです。  
主な機能はシグナル生成→ポートフォリオ構築→発注（ExecutionEngine）→監視（Monitoring）→ペーパートレード検証・レポート生成、さらに DuckDB を利用したリサーチ/ファクター計算や LLM を使ったニュース NLP によるセンチメント評価を含みます。

主な特徴
--------
- ExecutionEngine（本番 / ペーパートレード切替）
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、data/paper_trading.db に記録
- 監視機能（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた定期チェック
  - Kill Switch（data/kill.flag）で ExecutionEngine を安全に停止
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化
- ポートフォリオ構築（メンバー関数群）
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限・レジーム乗数
- リサーチ（DuckDB）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）連携
  - ニュース記事のセンチメントスコアリング（gpt-4o-mini などを想定）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 運用サポートツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール

セットアップ手順
----------------
1. Python 環境を用意
   - 推奨: Python 3.10+
   - 仮想環境の作成（例）
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 主要依存（明示的な requirements.txt は付属していない想定）
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証に任意で使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動（.git または pyproject.toml を含むルート）
   - 本リポジトリは config.py によりプロジェクトルートを自動検出して .env / .env.local を読み込みます

4. .env の初期作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 主な環境変数（ウィザードで設定される／参照される）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - LOG_LEVEL（DEBUG/INFO/…）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill flag を自動クリアするか: 0/1）
     - PAPER_FILL_MODE（instant/partial/never/reject、ペーパートレードでの fill 挙動）

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

使い方
------
- ExecutionEngine を起動（発注処理）
  - 本番（環境変数で KABUSYS_ENV=live）
    - python -m kabusys.run_execution
  - ペーパートレード
    - KABUSYS_ENV=paper_trading を設定（.env または環境変数）
    - python -m kabusys.run_execution
    - ペーパートレードでは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
  - 実行中の停止方法:
    - data/stop_requested.flag を作成すると run_execution/run_monitoring のループで検知して終了します
    - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は ExecutionEngine 停止を指示するために Monitoring が書き込む用途で使用

- Monitoring を起動（定期チェック）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（設定された SQLITE_PATH）を使用して監視ログを記録します

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で上書き可能、未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db を使用

- AI / リサーチ関数（ライブラリとして利用）
  - ニュース NLP:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
      - DuckDB 接続（duckdb.connect()）を渡して利用
      - api_key を省略すると環境変数 OPENAI_API_KEY が用いられる
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - リサーチ:
    - kabusys.research.calc_momentum / calc_volatility / calc_value
    - kabusys.research.calc_forward_returns / calc_ic / factor_summary 等

- ログ
  - デフォルトでは logs/<app_name>.log に日次ローテーションで保存（30日分保持）
  - setup_logging() を各起動スクリプトが呼び出して統一的に設定

運用上の注意
-------------
- KABUSYS_ENV は development / paper_trading / live のいずれかに設定してください。live は本番扱いのため慎重に。
- .env は絶対に Git 等へコミットしないでください（config_setup のヘッダーにも注意喚起あり）。
- Monitoring と Execution の停止制御は data/stop_requested.flag と data/kill.flag によります。運用時はこれらの扱いに注意してください。
- OpenAI を使う機能は API コストとレート制限に注意（リトライとバックオフは組み込まれているが無制限に安全ではありません）。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み・Settings
- config_setup.py           — .env 対話式ウィザード（CLI）
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト（main）
- run_monitoring.py         — Monitoring 起動スクリプト（main）

src/kabusys/execution/
- broker_factory.py         — ブローカークライアント生成
- execution_engine.py       — 実行エンジン（取引セッション管理）
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py

src/kabusys/monitoring/
- monitoring_db.py          — SQLite 永続化層（テーブル定義・CRUD）
- system_monitor.py         — システム状態 / データ鮮度監視
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- monitoring_engine.py
- alert_manager.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/ai/
- news_nlp.py               — ニュース NLP（OpenAI 呼び出し）
- regime_detector.py        — レジーム判定（MA + マクロセンチメント）
- __init__.py

src/kabusys/tools/
- paper_verification_report.py  — ペーパートレード検証レポート生成 CLI

src/kabusys/utils/
- logging_setup.py          — ログ設定ユーティリティ
- process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ

データ・ログ関連
- data/                      — デフォルトの DB / pid / フラグ保存先（プロジェクトルート直下）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/                      — ログファイルが出力される既定ディレクトリ

補足（開発者向け）
-----------------
- .env 自動読み込み:
  - config.py がプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動でロードします。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等）。
- DB スキーマの更新は monitoring_db.init_monitoring_db() にて冪等的に行われます（必要ならマイグレーション処理を追加）。
- OpenAI 呼び出しは retry/backoff を採用していますが、実運用では API コストやレート制御・キー管理に注意してください。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（本 README には含めていません）。  
- バグ報告や機能要望は Issue を通じてお願いします。

以上。導入時に不明点があれば、どの部分（例: .env の設定、Execution の起動、Monitoring の動作など）について詳しく知りたいか教えてください。
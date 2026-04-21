KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームです。  
主な目的は以下の通りです。

- 市場データを用いたファクター計算と研究（DuckDB を使用）
- ポートフォリオ構築、ポジションサイズ計算、リスク調整
- 発注エンジン（ExecutionEngine）による発注管理（実運用 / ペーパートレード対応）
- 監視コンポーネントによる稼働・取引ログの監視と Kill Switch（強制停止）
- ニュース NLP（OpenAI）を使ったセンチメント評価やレジーム判定
- ペーパートレード検証レポートや環境設定ウィザード等のユーティリティ

主要設計方針:
- データ永続化: DuckDB（分析用）と SQLite（監視・注文ログ）を併用
- 環境依存設定は .env（自動ロード機構あり）で管理
- 本番 / ペーパートレードは明確に分離（paper_trading モードは専用 DB を使用）
- OpenAI 呼び出しはリトライや入力トリミングなどフェイルセーフあり

主な機能
--------
- ExecutionEngine（run_execution.py）
  - ブローカークライアント（実口座 / モック）を使った発注処理
  - リスク管理（ポジション上限・ドローダウン等）
  - 発注・約定ログの記録（SQLite）
- Monitoring（run_monitoring.py + monitoring/*）
  - システム資源・プロセス監視、データ鮮度チェック
  - トレード監視、リスク監視、アラート通知、Kill Switch
- Portfolio（portfolio/*）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限など
- Research（research/*）
  - ファクター計算（Momentum/Value/Volatility 等）、将来リターン、IC 計算
- AI（ai/*）
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector: ma200 とマクロニュースで市場レジーム判定
- ユーティリティ
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. Python 環境を用意
   - 推奨: Python 3.10+（既存コードは modern typing を使用）
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 代表的な依存（プロジェクトに requirements.txt がない場合の例）:
     - pip install duckdb openai psutil PyYAML
   - その他、環境や機能に応じて追加パッケージが必要になる可能性があります。

3. プロジェクトルートに移動（.env の自動読み込みはプロジェクトルート検出を行います）
   - .git または pyproject.toml をプロジェクトルートに置いてください（自動検出に使用）

4. 環境変数設定
   - .env を直接編集するか、ウィザードを使って生成します:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用
     - KABU_API_PASSWORD — kabuステーション API パスワード
   - 重要: OpenAI を使う機能を使う場合は OPENAI_API_KEY を設定してください（news_nlp / regime_detector）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリの準備
   - デフォルトで data/ 以下に各種 DB / フラグファイル / pid ファイルを配置します。
   - logs/ ディレクトリはログ出力用に作成されます（logging_setup が自動作成可）

使い方
------
起動スクリプト
- ExecutionEngine（取引セッション）
  - 本番/開発/ペーパートレードの切替は KABUSYS_ENV により制御:
    - KABUSYS_ENV=development
    - KABUSYS_ENV=paper_trading
    - KABUSYS_ENV=live
  - 実行例:
    - python -m kabusys.run_execution
  - ペーパートレード時は MockBrokerClient が使用され、デフォルト DB は data/paper_trading.db に記録されます。

- Monitoring（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）
  - 監視は常に本番の sqlite_path（data/monitoring.db）を参照します（環境に依らず）

停止・Kill Switch
- 実行中プロセスは以下のフラグファイルを監視します:
  - data/stop_requested.flag — run_execution/run_monitoring がポーリング中に見つけると終了します
  - data/kill.flag — KillSwitch が書き込むと ExecutionEngine 停止のトリガーになります
- ExecutionEngine の PID は data/execution.pid に書き込まれます

報告・補助ツール
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]

プログラム的 API（ライブラリとして）
- 研究用関数:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- AI:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)  # api_key を与えない場合は環境変数 OPENAI_API_KEY を参照
- ポートフォリオ関連:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- OPENAI_API_KEY — OpenAI API（news_nlp / regime_detector 用）
- KABUSYS_ENV — 実行モード（development / paper_trading / live） デフォルト: development
- PAPER_FILL_MODE — ペーパーでの約定モード（instant / partial / never / reject） デフォルト: instant
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログ出力レベル（DEBUG/INFO/…） デフォルト: INFO
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行・Kill Switch の管理
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒）

ディレクトリ構成（抜粋）
-----------------------
（src/kabusys 以下の主なファイル・モジュール）

- src/kabusys/
  - __init__.py                     — パッケージ定義（バージョン等）
  - config.py                       — 環境変数 / 設定管理（.env 自動ロード含む）
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 起動前設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_engine.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在)
  - execution/                       — ExecutionEngine / OrderManager / BrokerFactory 等（起動スクリプトから利用）
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルのみを抜粋しています。実際のツリーにはさらにモジュールや補助ファイルがあります。）

注意事項 / 運用メモ
------------------
- 本番運用時は KABUSYS_ENV=live を設定する前に必須環境変数と config/*.yaml を十分に検証してください（validate_config を使用）。
- .env は決して Git 等にコミットしないでください（config_setup の出力ヘッダにも注意喚起あり）。
- OpenAI API を使う処理は外部 API 呼び出しのため失敗時のフォールバックやレート制御が組み込まれてはいますが、API キーの漏洩やコストには注意してください。
- monitoring は本番の sqlite_path を用いるため、監視と発注の DB 分離について理解した上で運用してください。
- ペーパートレードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を確認）。

トラブルシューティング
----------------------
- ログが出力されない / ファイルハンドラが作れない場合:
  - 権限や LOG_DIR の存在を確認。logging_setup はディレクトリ作成に失敗しても stdout ログは継続します。
- 設定読み込みが期待通りでない場合:
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env を自動ロードします。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。
- OpenAI へ接続できない場合:
  - OPENAI_API_KEY の有無、ネットワーク、SDK バージョンを確認してください。news_nlp と regime_detector はリトライを行いますが、API キー未設定では例外が発生します。

ライセンス・貢献
----------------
- README に含めるべきライセンス情報や貢献ルールが別途ある場合はプロジェクトルートに LICENSE / CONTRIBUTING.md を用意してください。

以上が本コードベースの概要と基本的な導入手順です。必要であれば環境変数のサンプル .env.example や、運用チェックリスト（本番リリース時チェック項目）も作成します。どの情報を追加したいか教えてください。
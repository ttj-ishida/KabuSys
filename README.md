KabuSys
=======

日本株向けの自動売買 / リサーチ基盤のコードベースです。  
このリポジトリは以下の機能群を備え、ローカル開発〜ペーパートレード〜本番運用まで想定した設計になっています。

要点
- Python パッケージ名: kabusys
- デフォルトのデータディレクトリ: data/
- DuckDB と SQLite を併用（DuckDB は分析、SQLite は監視/注文ログ）

プロジェクト概要
--------------
KabuSys は次の役割を持つモジュール群から構成されます（概要）:

- execution: 発注エンジン、Order 管理、リスク管理、Broker クライアントの抽象化（paper_trading では MockBroker を使用）
- monitoring: システム稼働監視、注文監視、リスク監視、Kill Switch、アラート管理
- portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限等のポートフォリオ構築ロジック（純粋関数）
- research: ファクター計算・特徴量解析（DuckDB を用いる）
- ai: ニュース NLP（OpenAI を利用したセンチメント）や市場レジーム判定
- tools: ペーパートレード検証レポート生成などのユーティリティスクリプト
- utils: プロセス優先度や CPU affinity 設定などのユーティリティ

主な特徴（機能一覧）
-----------------
- 環境切替（KABUSYS_ENV）により development / paper_trading / live をサポート
- paper_trading モードでは本番 DB と分離された data/paper_trading.db を使用
- ExecutionEngine と Monitoring の独立したランナー（run_execution, run_monitoring）
- 監視機能:
  - システム稼働率、CPU/メモリ/ディスク使用率
  - 発注滞留（stale order）・約定価格異常（price anomaly）
  - ドローダウン・ポジション上限チェック → Kill Switch（data/kill.flag 書込）
- ポートフォリオ構築: 候補選定、等比配分 / スコア配分、リスクベースのポジションサイズ計算、セクターキャップ適用
- Research: momentum/value/volatility 等のファクター計算、IC/統計サマリー
- AI: OpenAI を用いたニュースセンチメントスコア生成（gpt-4o-mini 想定）
- ツール: ペーパートレード検証レポート（期間指定可能）

セットアップ手順
----------------

1. 必要パッケージをインストール
   - 基本的に次をインストールしてください（プロジェクトに requirements.txt がある場合はそちらを利用）
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML — config/.yaml の検証に使用
   例:
     pip install duckdb psutil openai pyyaml

2. リポジトリをクローンして、Python パスを通す
   - パッケージ内のモジュールは python -m で実行できます。
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

3. 環境変数（.env）を作成
   - 対話式ウィザードで .env を作成・更新できます:
     python -m kabusys.config_setup
   - 主要な環境変数（必須・デフォルト）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動、default: "instant"、有効値: instant|partial|never|reject）
     - OPENAI_API_KEY（AI 機能利用時に必要）
     - LOG_LEVEL（デフォルト: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート通知用）
     - KILL_FLAG_CLEAR_ON_START（0/1、デフォルト 0）

4. 設定検証（任意だが推奨）
   - .env と config/*.yaml の基本チェック:
     python -m kabusys.validate_config
   - 警告もエラーとして扱いたい場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ作成
   - data/ 以下は自動的に作られますが、権限等で必要なら手動で作成してください。
   - デフォルトの DB ファイルパス:
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db (paper_trading 用)

使い方（主要コマンド）
--------------------

- 環境ウィザード（.env の作成/更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動（デフォルトは KABUSYS_ENV に従う）
  python -m kabusys.run_execution
  - paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動を行いません（停止フラグ）。
  - 実行中、data/execution.pid に PID を書きます（設定によりパス変更可）。

- Monitoring（システム監視）を起動
  python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 停止方法: data/stop_requested.flag を作成するとループが終了します（run_execution 側も同フラグを監視して停止）。
  - 監視は常に本番 sqlite_path（settings.sqlite_path）を使用します（環境に関係なく）。

- ペーパートレード検証レポート生成
  python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH を使用
  - 出力: 標準出力に期間の各種指標（稼働率、注文成功率、レイテンシ等）と PASS/FAIL 判定を出力

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news から銘柄別に集約して OpenAI に投げ、ai_scores テーブルへ書き込みます
    - api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 とマクロニュースの LLM 評価を組み合わせて市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに書き込みます

プロセス制御・フラグ
-------------------
- 停止要求:
  - data/stop_requested.flag : run_execution / run_monitoring のループ停止に使用（存在すると起動しない / ループを中断する）
  - data/kill.flag : KillSwitch が検出条件を満たした時に書き込まれる（ExecutionEngine に対する停止シグナル）
- PID ファイル:
  - data/execution.pid（デフォルト、設定により変更可能） — 実行中のエンジン PID を格納
- Kill Switch 条件:
  - ドローダウン（drawdown）閾値超過、ポジション数上限超過などに応じて kill.flag を作成します

設定周りの挙動（重要点）
----------------------
- 自動 .env ロード:
  - パッケージ import 時にプロジェクトルートが検出されれば .env（続いて .env.local）を自動で読み込みます。
  - OS 環境変数は上書きされません。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings クラスで環境変数の取得と基本バリデーションを行います（KABUSYS_ENV の有効値など）。
- Paper Trading:
  - settings.is_paper が True（KABUSYS_ENV=paper_trading）の場合、Execution は paper_sqlite_path を使用して本番 DB と完全分離します。
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます。

ディレクトリ構成
----------------

（主要ファイル・ディレクトリの概観）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し・スコアリング）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・読み書きラッパ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留 / 約定異常検出
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch ロジック（data/kill.flag 書込）
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - alert_manager.py       — （アラート送信の入口：未掲示の実装を含む）
  - execution/               — Execution エンジン周り（OrderManager, RiskManager 等）
  - portfolio/               — ポートフォリオ構築ロジック（builder, sizing, risk_adjustment）
  - research/                — ファクター計算、特徴量探索
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - data/                    — 実行時に使用されるファイル（DB, flag, pid）を配置する想定

注意事項 / 運用上のヒント
------------------------
- 本番（KABUSYS_ENV=live）では LINE 通知等の設定を必ず確認してください。validate_config は live 時に追加の警告を出します。
- Kill Switch（data/kill.flag）を本番で自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0。
- AI 機能を利用するには OPENAI_API_KEY が必要です。API レート制限やエラー時のリトライが実装されていますが、運用上の制御（キー/料金）に注意してください。
- Monitoring は本番 sqlite_path を利用します。環境に依らず監視履歴は本番 DB に書き込まれる点を理解しておいてください。

貢献 / 開発時メモ
-----------------
- テスト／モック:
  - AI 呼び出し部分（_call_openai_api）はテスト時に差し替えやすい設計になっています（unittest.mock.patch 推奨）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存カラムがない場合にカラムを追加する簡易マイグレーションを行います（冪等）。
- ロギング:
  - 各スクリプトは logging.basicConfig(level=logging.INFO) を使って簡易ログ出力します。LOG_LEVEL 環境変数で変更可能。

ライセンス / バージョン
----------------------
- パッケージ内の __version__ は 0.1.0（src/kabusys/__init__.py）。

この README はコードベースの主要機能と運用上のポイントをまとめたものです。実行や運用時には .env と config/*.yaml（必要があれば）を確認し、validate_config でチェックしてください。必要であれば README をプロジェクト固有の運用手順に合わせて拡張してください。
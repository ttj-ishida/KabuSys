KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買および関連データ処理・モニタリングを行う小型フレームワークです。  
主に以下の機能を持ち、実際の発注（kabuステーション）・ペーパートレード・監視・解析・AI（ニュース NLP / レジーム判定）をサポートします。

主な特徴
--------
- 実行エンジン（ExecutionEngine）：ブローカークライアントを介した注文管理・実行（本番／ペーパー分離）
- 監視（Monitoring）：システム稼働状況、滞留注文、リスク（ドローダウン・ポジション数）監視と Kill Switch
- ポートフォリオ構築：候補選定・重み計算・ポジションサイジング・セクター制約等の純粋関数群
- リサーチ：DuckDB を用いたファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー 等）
- AI モジュール：ニュースを LLM でスコアリングし銘柄別スコアを保存／マクロセンチメントを用いたレジーム判定
- ユーティリティ：環境設定ウィザード（.env 作成）、設定検証 CLI、ロギング設定ユーティリティ 等
- 各種ツール：ペーパートレード検証レポート生成スクリプト等

必要要件（例）
--------------
- Python 3.10+
- 主要依存パッケージ（例）：duckdb, psutil, openai  
  ※ 実際の requirements はプロジェクト配布時に合わせてインストールしてください。

セットアップ手順
----------------
1. リポジトリをクローン／展開する。

2. 仮想環境を作成して依存パッケージをインストールする（プロジェクトに requirements.txt がある想定）。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt

3. 環境変数 (.env) を作成する（対話式ウィザード推奨）。
   - 実行:
     - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン・kabuAPI パスワード等を対話式で入力し .env を生成します。
   - 自動ロード: .env（および .env.local）がプロジェクトルートから自動読み込みされます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証を実行する:
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます。

主要環境変数（抜粋）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード

主要な任意／デフォルト:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時に必要）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant | partial | never | reject）

実行方法（代表）
----------------
- ExecutionEngine（取引実行）
  - 本番／ペーパー挙動を切替可能（KABUSYS_ENV）
  - 起動:
    - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）。

- Monitoring（監視ループ）
  - 起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）で間隔を変更可能（デフォルト 60 秒）。
  - 監視は常に Settings.sqlite_path（本番監視 DB）を使用します。

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 環境設定ウィザード:
  - python -m kabusys.config_setup

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

停止／Kill Switch
-----------------
- 実行中プロセスの停止はフラグファイル方式を利用:
  - data/stop_requested.flag — run_execution/run_monitoring の外部停止要求（run スクリプトはこのファイルの存在を検知して安全停止）
  - data/kill.flag — KillSwitch が検出した重大なリスク時に ExecutionEngine を停止させるために書き込まれる
- PID ファイル:
  - data/execution.pid（デフォルト）に ExecutionEngine の PID を書きます

ロギング
--------
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで保存されます（kabusys.utils.logging_setup）。
- 環境変数 LOG_DIR でログディレクトリを変更、LOG_LEVEL でログレベルを指定できます。

簡単なコード呼び出し例（Python REPL）
-----------------------------------
- 設定確認:
  - >>> from kabusys.config import settings
  - >>> print(settings.sqlite_path)
- Paper Trading レポート（プログラムから）:
  - >>> from kabusys.tools.paper_verification_report import generate_report
  - >>> generate_report("data/paper_trading.db", from_date="2026-04-01", to_date="2026-04-11")
- AI ニューススコア（DuckDB 接続が必要）:
  - >>> import duckdb
  - >>> conn = duckdb.connect("data/kabusys.duckdb")
  - >>> from kabusys.ai.news_nlp import score_news
  - >>> score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

注意事項 / 運用上のヒント
------------------------
- KABUSYS_ENV=live は本番運用モードです。LINE 等の通知設定や kill flag の挙動を慎重に確認してください。
- .env はセキュリティ上絶対にリポジトリにコミットしないでください（config_setup のヘッダにも警告あり）。
- ペーパートレード環境は本番 DB と完全分離するように設計されています。PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- OpenAI 等外部 API を利用する機能は API キーと通信回数に注意して運用してください（レート制限・コスト発生）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールと簡単な説明です。

- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（本番/ペーパー切替対応）
- config.py — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- __init__.py — パッケージメタ情報（バージョン等）

サブパッケージ（主要）
- kabusys.utils
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- kabusys.monitoring
  - monitoring_db.py — 監視用 SQLite テーブル初期化・読み書き
  - system_monitor.py — CPU/MEM/DISK/データ鮮度/プロセス監視
  - risk_monitor.py — ドローダウン / ポジション上限の監視
  - trade_monitor.py — （滞留注文・約定異常検出等）
  - kill_switch.py — Kill Switch（flag ファイル管理）
  - monitoring_engine.py — 各モニタの束ね（テスト用 run_once / 本番 run）
- kabusys.execution — 発注／注文管理に関する実行ロジック（Engine / BrokerFactory / OrderManager 等）
- kabusys.portfolio — 銘柄選定・重み計算・リスク調整・ポジションサイジング（portfolio_builder / risk_adjustment / position_sizing）
- kabusys.research — DuckDB を使ったファクター計算・特徴量解析（factor_research / feature_exploration）
- kabusys.ai — AI 関連（news_nlp: ニュース NLP スコア、regime_detector: レジーム判定）
- kabusys.tools — 付帯ツール（paper_verification_report 等）
- data/ — データファイル類（デフォルト位置）
  - data/kabusys.duckdb (DuckDB)
  - data/monitoring.db (SQLite: 監視ログ)
  - data/paper_trading.db (SQLite: ペーパートレード、KABUSYS_ENV=paper_trading 時に使用)
  - data/kill.flag, data/stop_requested.flag, data/execution.pid などのフラグ/制御ファイル

ライセンス / 貢献
----------------
- （プロジェクト配布時に合わせたライセンス表記をここに記載してください）

お問い合わせ
-----------
不具合や改善案、機能追加の提案は Issue を作成してください。README の内容はプロジェクトの実装に合わせて随時更新してください。
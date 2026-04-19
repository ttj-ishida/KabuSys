KabuSys — 日本株自動売買システム
================================

これはリポジトリの簡易 README（日本語）です。プロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムおよびそれを支える監視・リサーチツール群です。主な要素は以下です。

- ExecutionEngine：発注・注文管理・リスク制御を行う実行エンジン
- Monitoring：システム状態・注文状態・リスクを定期監視しアラート／Kill Switch を提供
- Research：DuckDB を使ったファクター計算や特徴量解析
- AI モジュール：OpenAI を使ったニュースセンチメント評価（news_nlp）や市場レジーム判定
- Portfolio：銘柄選定・配分・ポジションサイズ計算などの純粋関数群
- Tools：ペーパートレード検証レポート等のユーティリティスクリプト
- 設定ユーティリティ：.env ウィザード（config_setup.py）と設定検証（validate_config.py）

主な機能一覧
-------------
- 発注処理（本番 / ペーパートレード切替）
  - KABUSYS_ENV=paper_trading で MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）
  - CPU/メモリ/ディスク、データ鮮度、プロセス生存、滞留注文、約定異常、ドローダウンやポジション上限を監視
  - Kill Switch（data/kill.flag）によるエンジン停止シグナル
- アラート通知（LINE トークン設定により通知可能）
- AI を使ったニュースセンチメント（OpenAI）と市場レジーム判定
- DuckDB によるファクター計算・リサーチ（モメンタム / ボラティリティ / バリュー 等）
- ポートフォリオ構築・ポジションサイズ計算（等配分 / スコア重み / リスクベース）
- 各種ツール（Paper Trading 検証レポート生成など）
- 設定ウィザード（.env 生成）と事前検証ツール

前提・依存
-----------
最低限の依存パッケージ（例）：
- Python 3.10+（型ヒントの構文で | を使用）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定検証で YAML 検証を行う場合、任意）
- その他、pip によりインストールされるパッケージ群

セットアップ手順
----------------
1. リポジトリをクローンして仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに配布用の requirements ファイルがあればそれを利用してください）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）

   主要な環境変数（デフォルトを示すものは明記）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - OPENAI_API_KEY (AI 機能を利用する場合)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (ペーパートレード DB, デフォルト: data/paper_trading.db)
   - KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート通知用）
   - KILL_FLAG_CLEAR_ON_START（起動時 kill flag を自動クリアするか、デフォルト 0）

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い

使い方（主要スクリプト）
------------------------
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 実行時に KABUSYS_ENV=paper_trading を設定するとペーパートレード用の MockBrokerClient を使い、データは data/paper_trading.db に記録され本番 DB と分離されます。
  - 実行中は data/execution.pid に PID を書き、data/stop_requested.flag を作成すると停止シグナルとして検出します。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します（環境に関わらず）
  - 停止フラグ: data/stop_requested.flag を作成するとループが終了します

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリは自動作成）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理
- ログ出力先変更: 環境変数 LOG_DIR または setup_logging の引数で指定

停止・Kill Switch・フラグファイル
-------------------------------
- デーモン的に起動するスクリプトは data/stop_requested.flag の存在をチェックして安全終了します（run_execution.py/run_monitoring.py）。
- KillSwitch（監視側）は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path でパス指定可能）。
- 起動時に Kill Flag を自動クリアするかは KILL_FLAG_CLEAR_ON_START で制御（本番では 0 推奨）。

注意点（本番運用の安全策）
-------------------------
- KABUSYS_ENV=live 設定時は LINE 通知設定等を必ず確認してください（validate_config が警告を出します）。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダーにも注記あり）。
- OpenAI API キーやブローカー API の認証情報は安全に管理してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要ファイルと簡易説明です。

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定の事前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - execution/  — 発注周り（ブローカーファクトリ、ExecutionEngine、OrderManager 等）
    （実装ファイルは多数あり、ブローカー抽象化経由で本番/ペーパーを切替）

  - monitoring/
    - monitoring_db.py — SQLite による監視データの永続化層（テーブル初期化含む）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — (滞留注文・約定異常などの監視) ※実装ファイルあり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 制御（flag ファイル）
    - alert_manager.py — アラート送信ラッパ（LINE 等）
    - monitoring_engine.py — 複数 Monitor を束ねるループエンジン

  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・キャップ適用
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — モメンタム・ボラ・バリューの DuckDB ベース計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ等

  - ai/
    - news_nlp.py — OpenAI を使ったニュースセンチメント解析（ai_scores へ書き込み）
    - regime_detector.py — マクロニュース + ETF MA で市場レジーム判定

  - monitoring/monitoring_db.py — 監視用 DB スキーマ定義と永続化 API
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成ツール

  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイルローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

利用上のヒント
--------------
- 開発時は KABUSYS_ENV=development を使用（発注は発生しない挙動を想定）。
- ペーパートレードでロジック検証する場合は KABUSYS_ENV=paper_trading を使用（データ分離）。
- AI 機能を利用するには OPENAI_API_KEY を設定。API 呼び出しはリトライやフォールバック実装が組み込まれていますが、料金とレート制限に注意してください。
- DuckDB は分析用途で利用。prices_daily / raw_financials 等のテーブルが必要です。

問い合わせ・拡張
----------------
- 新しい通知チャネルの追加、ブローカー実装の追加、ポートフォリオ構成ロジックの改定などはモジュール化が進んでいるため比較的容易に拡張できます。
- ドキュメント・設計（PortfolioConstruction.md 等）に準拠して実装／テストしてください。

以上がこのコードベースの簡易 README です。必要であれば、各コンポーネント（ExecutionEngine の起動引数や OrderRepository の振る舞い、monitoring の詳しい設定など）についてさらに詳細な README/ドキュメントを作成します。どの部分を詳細化しますか？
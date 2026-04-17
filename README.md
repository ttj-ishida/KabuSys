KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための小規模フレームワークです。
- 戦略・ポートフォリオ構築（ファクター計算、ポジションサイジング、セクター制限など）
- 注文実行エンジン（本番 / ペーパートレード分離）
- 監視（システム状態、注文滞留、リスク監視、Kill Switch）
- AI（ニュースのセンチメントスコア付与、レジーム判定）連携（OpenAI）
- 各種ツール（ペーパートレード検証レポート生成等）

主な設計方針
- 本番とペーパートレードを明確に分離（DB・ブローカークライアント等）
- ルックアヘッドバイアス回避（日時の扱いに配慮）
- フェイルセーフ（API/DB失敗時は安全に継続する挙動）
- 環境変数 / .env による設定管理、起動前の検証ツールあり

機能一覧
--------
- 環境設定ウィザード (.env 作成) — kabusys.config_setup
- 設定検証 CLI (.env / config/*.yaml の事前チェック) — kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 対応） — run_execution.py
- SystemMonitor ポーリング（監視ログの永続化） — run_monitoring.py
- 監視コンポーネント
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度
  - TradeMonitor：滞留注文・約定異常
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件を満たした場合 data/kill.flag を書き込む
  - AlertManager：LINE によるプッシュ通知（オプション）
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジション数算出、リスク調整）
- リサーチ機能（ファクター計算、Forward Returns、IC 計算、統計サマリー）
- AI モジュール
  - news_nlp.score_news：ニュースを LLM に渡して銘柄別スコアを ai_scores テーブルに書込む
  - regime_detector.score_regime：MA とマクロニュースを合成して日次レジーム判定
- ツール
  - paper_verification_report：ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------
前提
- Python 3.10+（型アノテーションの表記に合わせること）
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - （任意）PyYAML（config/*.yaml の検証を行う場合）

1. リポジトリをクローン
   - ソースは src/kabusys 下に配置

2. 仮想環境作成 & 依存インストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install duckdb psutil requests openai
   - （設定検証で YAML の検証を行う場合）pip install pyyaml

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を用意（ルートに配置）
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要設定例（.env の抜粋）
     - KABUSYS_ENV=development        # development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-xxx           # AI 機能を使う場合
     - LINE_CHANNEL_ACCESS_TOKEN=      # 任意（通知）
     - LINE_USER_ID=                    # 任意（通知）
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL としたい場合：
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（自動作成される場合もあるが明示的に作ると安心）
   - mkdir -p data

使い方
------
起動スクリプト
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と完全分離）。
    - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）
    - 実行中に data/stop_requested.flag を置くと優雅に停止します（run_execution は起動時に stop フラグがある場合は起動しません）。

- SystemMonitor（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依らない）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
      - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 停止フラグ: data/stop_requested.flag を検知するとループ終了

ツール
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数で指定することも可能）
  - 出力: 標準出力に検証サマリ（稼働率・注文成功率・P95 レイテンシ等）を表示

AI 機能（プログラム的利用）
- ニューススコアリング
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定だと例外。
- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)
  - 同様に OPENAI_API_KEY が必要

監視 / Kill Switch
- KillSwitch（data/kill.flag）:
  - リスク条件（ドローダウン、ポジション上限等）を満たすと data/kill.flag を作成して ExecutionEngine 停止シグナルを送出します。
  - Settings.kill_flag_clear_on_start = 1 の場合、起動時に自動クリアされる設定（本番での自動クリアは推奨されません）。
- stop/kill フラグの場所（デフォルト）
  - 停止要求: data/stop_requested.flag
  - Kill Switch: data/kill.flag
  - PID: data/execution.pid

重要な設定（概要）
- KABUSYS_ENV
  - development / paper_trading / live
  - run_execution は paper_trading 時に DB / ブローカーを切り替え
- PAPER_FILL_MODE
  - paper_trading の MockBrokerClient の約定モード
  - 有効値: instant | partial | never | reject
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）
- OPENAI_API_KEY
  - AI 機能を使う際に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - アラート送信（任意）。未設定時は送信をスキップしてログ出力のみ行う。

ディレクトリ構成（主要ファイル）
------------------------------
（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数と .env の自動ロード / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）連携
    - regime_detector.py     — レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py       — monitoring DB スキーマ / 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - execution/                — ExecutionEngine 周り（OrderManager 等）（実装の一部が別ファイル）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/                     — デフォルトで使用する DB ファイル等（実際はプロジェクトルート/data）

補足 / 運用メモ
----------------
- DB 初期化:
  - run_execution/run_monitoring 起動時に monitoring DB のテーブルを冪等的に作成します（init_monitoring_db を実行）。
- 本番運用注意:
  - validate_config で本番用チェック（KABUSYS_ENV=live）を必ず実行して警告を確認してください。
  - KILL_FLAG_CLEAR_ON_START=1 は本番での自動クリアは推奨されません（誤って Kill Switch を無効化する可能性）。
- ログレベルは環境変数 LOG_LEVEL で制御可能。
- psutil によるプロセス優先度設定は権限や OS に依存します。失敗時はログに出力してスキップします。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報・コントリビューション方針はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ
----------
- 実装や仕様に関する質問・改修提案はリポジトリの issue を作成してください。

（以上）
KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・バックオフィス補助を目的とした Python 製のシンプルなフレームワークです。本リポジトリは以下を含みます:

- 注文管理・発注 Engine（ExecutionEngine）
- 監視・アラート機構（MonitoringEngine、LINE Push）
- ポートフォリオ構築ユーティリティ（候補選定、配分、ポジションサイズ計算）
- リサーチ用ファクター計算（DuckDB を利用したファクター群）
- AI を使ったニュースセンチメント / 市場レジーム判定（OpenAI）
- 開発・検証支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な特徴
--------
- 明確に分離された実行環境: KABUSYS_ENV による `development` / `paper_trading` / `live` 切替
  - paper_trading 時は MockBroker を使い、paper 用 SQLite（data/paper_trading.db）に記録
- 監視（Monitoring）機能
  - システム状態（CPU/メモリ/ディスク）、Execution プロセス生存、データ鮮度の追跡
  - 注文滞留・約定異常の検出、ドローダウンやポジション上限の監視、kill.flag による停止制御
  - LINE による通知（AlertManager）
- ポートフォリオ構築：候補選定、等配分/スコア加重、リスク調整（セクター制限、レジーム乗数）、株数決定（単元丸め・aggregate cap）
- DuckDB を用いた時系列・ファクター計算（モメンタム、ボラティリティ、バリュー 等）
- OpenAI（gpt-4o-mini）を用いたニュース NLP とレジーム判定（API 呼び出しは冪等／エラー耐性あり）
- モジュール単位で単純関数化されておりテストや再利用が容易

セットアップ手順
----------------

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ 実環境の requirements.txt がある場合はそれを使用してください。

3. プロジェクトルートに移動して環境変数を設定
   - 推奨は .env に記載しておく方法（リポジトリの config.py が自動ロードします）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（Settings）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（空なら送信はスキップ）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 時の専用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH: 各種ファイルパス（デフォルトは data 配下）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）

使い方
------

前提: src が PYTHONPATH に入っている、あるいはパッケージとしてインストールされていること。

1. 監視プロセス起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 振る舞い:
     - プロセス優先度を high に設定し（可能なら）60 秒間隔で SystemMonitor を実行
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可
     - 停止: data/stop_requested.flag を作成するとループが終了

2. 実行エンジン起動（Execution）
   - python -m kabusys.run_execution
   - 振る舞い:
     - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading 用 DB に記録
     - 実行中は data/execution.pid に PID を書き、data/stop_requested.flag / data/kill.flag により停止可能

3. Streamlit ダッシュボード（監視 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only モードで SQLite を開いてポジション・注文・システムステータスを表示

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数を優先）
   - 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等のレポートと PASS/FAIL 判定

5. AI / リサーチ機能
   - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news をスコアして ai_scores に書込
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime に判定を書込
   - 両関数とも OPENAI_API_KEY（または引数）を必要とします。API 呼び出しはリトライ・フェイルセーフ実装

運用に関するメモ
----------------
- paper_trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine に停止シグナルを送る仕組みがあります。KillSwitch により条件付きで自動書込されることがあります（例: ドローダウン超過）。
- stop_requested.flag（data/stop_requested.flag）を作成すると run_monitoring / run_execution のループが安全に終了します。
- プロセス優先度と CPU affinity は psutil を使って調整を試みますが、権限や OS により失敗する可能性があります（警告ログを出力してスキップします）。
- .env の自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を基準に探索します
  - 自動ロードの順: OS 環境 > .env.local（上書き） > .env（未設定キーのみ）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                      — 環境変数 / Settings
    utils/
      process_priority.py          — プロセス優先度 / CPU affinity
    monitoring/
      __init__.py
      monitoring_db.py             — SQLite テーブル初期化・永続化層
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      order_repository.py
      reconciler.py
      execution_engine.py          — 実行エンジン（主要ロジックはここ）
      broker_factory.py
      broker_api.py
      order_record.py
      order_repository.py
      order_manager.py
      reconciler.py
      /* その他 execution 関連 */
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py
      regime_detector.py
    data/
      pipeline.py                  — DuckDB からの最終価格取得など（参照される）
    tools/
      paper_verification_report.py
    run_monitoring.py
    run_execution.py

（上記は主要ファイルを抜粋した構成です）

テスト・開発時のヒント
--------------------
- DuckDB のテーブル（prices_daily, raw_financials, raw_news など）を事前に準備しておくと research/ai 機能をローカルで動かせます。
- AI モジュールは外部 API を呼ぶため、ユニットテストでは _call_openai_api をモックすることを想定しています（実装中の注釈あり）。
- monitoring_db.init_monitoring_db() は冪等で、既存 DB に対する簡単なマイグレーション（カラム追加）にも対応します。

例: 最小 .env テンプレート
--------------------------
# KABUSYS 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

# API keys / tokens
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# DB パス（必要に応じて）
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
DUCKDB_PATH=data/kabusys.duckdb

よくある質問 (FAQ)
-----------------
Q. paper_trading で本番 DB に影響はありますか？
A. いいえ。paper_trading モードでは paper 用 SQLite を使用し本番 DB と分離する設計です。

Q. 自動的に .env を読み込みたくない場合は？
A. 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q. MONITOR の間隔を変えたい
A. 環境変数 MONITOR_POLL_INTERVAL に秒数を設定してください（正の整数、デフォルト 60）。

貢献・拡張
-----------
- 新しい broker 実装を追加する場合は execution/broker_factory.py を拡張してください。
- AI 周りのモデルやプロンプト調整は kabusys/ai/*.py を編集して対応できます。API 呼び出しの堅牢性（リトライ・クリップ・検証）は既に実装されていますが、ユースケースに応じてパラメータを調整してください。

---

この README はコードヘッダ・docstring から取得した情報を基に作成しています。実運用前に .env の設定や DB 初期化、必要な権限（プロセス優先度変更等）を確認してください。もし README に追加したい運用手順や例があれば教えてください。
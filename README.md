README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を支援する内部ライブラリ群です。本リポジトリには以下の主要機能が含まれます。

- 注文発行・状態管理／実行エンジン（ExecutionEngine / OrderManager）
- 監視基盤（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- AI 支援機能（ニュースの NLP スコアリング、レジーム検出）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

この README はコードベースに基づいて、セットアップ方法・実行方法・ディレクトリ構成をまとめたものです。

主な機能一覧
--------------
- 設定管理
  - kabusys.config.Settings：.env / 環境変数読み込み、自動ロード機能（.env, .env.local）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能

- 監視（monitoring）
  - SystemMonitor：CPU/メモリ/ディスク・プロセス生存確認・データ鮮度チェック
  - TradeMonitor：滞留注文（stale orders）・約定価格異常（price anomaly）検出
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボード更新、リスクログ記録
  - KillSwitch：kill.flag ファイルを用いた ExecutionEngine 停止シグナル生成
  - AlertManager：LINE Messaging API によるプッシュ通知（クールダウン管理）
  - MonitoringEngine：上記モニタをまとめてポーリング
  - monitoring_db：SQLite ベースの監視ログ永続化（テーブル初期化・マイグレーション含む）
  - streamlit_dashboard：監視用の Streamlit ダッシュボード

- 実行（execution）
  - run_execution.py：ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper DB に記録）
  - Reconciler：起動時の注文・ポジション突合（自動復旧）
  - OrderManager / OrderRepository：注文状態遷移・永続化
  - RiskManager：発注前のリスク評価（設定に基づくパラメータ）

- ポートフォリオ（portfolio）
  - portfolio_builder：候補選定、等配分・スコア配分の重み計算
  - risk_adjustment：セクターキャップ、レジーム乗数
  - position_sizing：株数計算・単元丸め・aggregate cap 処理

- リサーチ（research）
  - factor_research：momentum / volatility / value 等のファクター計算（DuckDB 使用）
  - feature_exploration：将来リターン計算、IC（情報係数）、統計サマリー

- AI（ai）
  - news_nlp.score_news：raw_news を OpenAI に送り銘柄ごとのセンチメントスコアを ai_scores に書き込み
  - regime_detector.score_regime：ETF（1321）MA とマクロニュースを合成して日次レジーム判定を行い market_regime に書き込み

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の | やその他の構文を利用）
- SQLite（標準ライブラリ）、DuckDB（duckdb Python パッケージ）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS)
   - .venv\Scripts\activate (Windows)

3. 必要パッケージのインストール
   代表的な依存：
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit (ダッシュボード利用時)

   例:
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

4. 環境変数 / .env の準備
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env や .env.local を置くと自動で読み込まれます。
   自動ロードを無効化する場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）
- KABUSYS_ENV: 起動環境（development, paper_trading, live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: paper trading の fill モード（instant | partial | never | reject） デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用
- PID_FILE_PATH / KILL_FLAG_PATH など（監視関連）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

例 .env（最低限の設定）
- JQUANTS_REFRESH_TOKEN=xxxxx
- KABU_API_PASSWORD=xxxxx
- OPENAI_API_KEY=sk-xxxxx
- KABUSYS_ENV=development

使い方
------
- 監視ループの起動
  - デフォルトのポーリング間隔は 60 秒。環境変数で変更可能。
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（data/monitoring.db）を用いる点に注意：monitoring は環境にかかわらず本番 sqlite_path を使用します（設計上の仕様）。

- 実行エンジン（取引実行）の起動
  - KABUSYS_ENV により動作が変わります。
    - paper_trading: MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と完全分離）
    - live: 実際のブローカークライアントを使用（設定に依存）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開くため起動前に MonitoringEngine を走らせることを推奨。

- Paper Trading 検証レポート（コマンドラインツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで別 DB を指定可能（デフォルト: data/paper_trading.db）

- AI 機能の利用（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡してニューススコアを ai_scores に書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None) — レジーム判定を market_regime に書き込み
  - 注意: API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定

- その他ユーティリティ
  - portfolio.*: 候補選定・重み計算・ポジションサイズ計算（純粋関数。単体テストやシミュレーションで利用）
  - research.*: DuckDB を渡してファクター計算・IC 計算・統計集計を実行

運用上の注意 / トラブルシューティング
- process priority（優先度）設定は psutil を使用。OS によっては権限不足で設定できない場合があります（警告でスキップ）。
- Monitoring は監視用 DB（sqlite_path）を使います。paper_trading 時も監視 DB は本番パスを参照するため意図的に分離したい場合は環境変数でパスを変更してください。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるためコードは空チェックを行っていますが、DuckDB のバージョンによって挙動が異なる点に注意してください。
- OpenAI API 呼び出しは RateLimit / ネットワークエラー / 5xx をリトライする設計ですが、API キーや料金プランの制限により失敗する可能性があります。失敗時はフェイルセーフで「スコア未更新」や「0.0」判定を行う実装です。

ディレクトリ構成（主要ファイル）
----------------------------
src/
  kabusys/
    __init__.py                    — パッケージ定義（バージョン等）
    config.py                      — 環境変数/.env 読み込みと Settings
    run_monitoring.py              — SystemMonitor ポーリング用エントリポイント
    run_execution.py               — ExecutionEngine 起動スクリプト

    ai/
      __init__.py
      news_nlp.py                  — ニュース NLP（OpenAI）で ai_scores 書き込み
      regime_detector.py           — レジーム判定（MA + マクロニュース）

    monitoring/
      __init__.py
      monitoring_db.py             — SQLite テーブル初期化・永続化 API
      system_monitor.py            — システム状態・データ鮮度監視
      trade_monitor.py             — 注文滞留・約定異常監視
      risk_monitor.py              — ドローダウン・ポジション上限監視
      kill_switch.py               — kill.flag 管理
      alert_manager.py             — LINE Push 通知
      monitoring_engine.py         — 各 Monitor を束ねるエンジン
      streamlit_dashboard.py       — Streamlit ダッシュボード

    execution/
      reconciler.py                 — 起動時リコンシリエーション
      order_manager.py              — 注文状態遷移の外向き API
      order_repository.py           — (存在するがここでは一部のみ) 永続化レイヤ
      execution_engine.py           — 実行エンジン（起動スクリプト run_execution が利用）

    portfolio/
      portfolio_builder.py          — 候補選定・重み計算
      risk_adjustment.py            — セクター制限・レジーム乗数
      position_sizing.py            — 株数算出・丸め・aggregate cap

    research/
      factor_research.py            — ファクター計算（momentum/volatility/value）
      feature_exploration.py        — 将来リターン・IC・統計サマリー

    tools/
      __init__.py
      paper_verification_report.py  — Paper Trading 検証レポート生成 CLI

    utils/
      __init__.py
      process_priority.py           — プロセス優先度・CPU affinity ユーティリティ

付録：よく使うコマンド例
------------------------
- 監視の起動（ポーリング間隔 60 秒）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Python REPL から AI スコアリングを呼び出す（例）
  - python -c "import duckdb, datetime; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1), api_key='YOUR_KEY'))"

最後に
------
この README はコードベースに基づく概要・操作ガイドです。プロダクション運用する場合は環境（APIキー、DB の場所、権限、監視アラート先など）を慎重に構成し、テスト環境で十分な検証を行ってください。追加のドキュメント（設計資料や運用手順）があればそれに従ってください。
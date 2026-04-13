KabuSys
======

日本株向けの自動売買 / 監視フレームワークの小規模なコードベースです。  
この README はリポジトリ内の主要モジュール群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助など）を概説し、セットアップと起動方法、ディレクトリ構成を示します。

概要
----
KabuSys は以下の責務を持つモジュール群で構成されています。

- Execution: ブローカーとのインタフェースを通じて注文を発行・管理するエンジン（ExecutionEngine）。
- Monitoring: システム状態、注文滞留、リスク（ドローダウン・ポジション上限）を定期的にチェックし、ログ・アラートを出す。
- Portfolio: 候補選別、重み付け、ポジションサイズ計算、セクターキャップ等の純粋関数群（DB 非依存）。
- Research: DuckDB 上の履歴データを用いたファクター計算・特徴量解析。
- AI: ニュース NLP によるセンチメント付与・市場レジーム判定（OpenAI API を使用）。
- Tools: Paper Trading 検証レポート生成スクリプト、Streamlit ダッシュボード等。

主な設計方針:
- 本番環境と Paper Trading を明確に分離（KABUSYS_ENV による切替）。
- DuckDB を時系列/ファクターデータ参照に、SQLite を監視ログ / 注文ログに使用。
- 外部 API 呼び出し（OpenAI など）は失敗時にフォールバックやリトライを行いフェイルセーフ化。

主な機能一覧
------------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と分離。
  - 起動時にプロセス優先度を "high" に設定。
  - リコンシリエーション（再起動後の注文・ポジション突合）機能有り。

- 監視エンジン（run_monitoring.py / MonitoringEngine）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度を監視し system_status に記録。
  - TradeMonitor: 注文滞留（stale orders）や約定価格の異常を検出して risk_logs に記録。
  - RiskMonitor: ドローダウン・ポジション上限を監視して dashboard を更新し、必要に応じてリスクイベントを発行。
  - KillSwitch: 条件により data/kill.flag を書き込んで ExecutionEngine 停止シグナルを送信。
  - AlertManager: LINE Messaging API による一方向通知（クールダウン管理付き）。
  - Streamlit ダッシュボード（読み取り専用）で監視情報を可視化可能。

- ポートフォリオ構築
  - 候補選定（スコア降順）、等重/スコア重み配分、リスクベースの株数計算（単元株丸め、aggregate cap 処理）。
  - セクター上限適用、レジーム乗数（bull/neutral/bear の乗数決定）。

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で SQL と Python で計算。
  - 将来リターン、IC（スピアマン相関）やファクター統計要約。

- AI（OpenAI 使用）
  - ニュースを銘柄ごとに集約し LLM でセンチメント（-1.0〜1.0）を算出して ai_scores テーブルに書込。
  - マクロニュースと ETF MA200 乖離を組み合わせて市場レジーム（bull/neutral/bear）判定し market_regime に書込。
  - 429/ネットワーク断/5xx 等に対する指数バックオフのリトライ実装。

セットアップ手順
---------------
前提:
- Python 3.10+ を推奨（typing | None 型記法や型注釈に依存）。
- DuckDB, sqlite3 はローカル DB ファイルを利用。
- OpenAI を利用する機能は OPENAI_API_KEY が必要。
- 実行ホストに pip install できる権限があること。

基本手順（例）
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （ローカル開発用）pytest 等を追加することも可

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用。

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（OS 環境変数が優先）。
   - 主要な環境変数の一覧（最小構成）:

     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の SQLite）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PID_FILE_PATH, KILL_FLAG_PATH など（デフォルト値あり）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）

   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=yyyyyyyy
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=paper_trading
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

4. データベース初期化
   - 監視 DB は run_monitoring / run_execution 実行時に自動で init_monitoring_db() が呼ばれてテーブルが作成されます。
   - DuckDB 用の履歴データ（prices_daily 等）は別途用意してください（CSV インポートや別 ETL）。

使い方
------
起動スクリプト
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で秒単位に上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を参照します（KABUSYS_ENV に依らず）。

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）と Mock ブローカーが使われ、本番 DB と完全に分離されます。

Streamlit ダッシュボード（監視表示）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で、監視 DB（SQLite）を URI read-only モードで開きます。

Paper Trading 検証レポート
- スクリプト:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先）。

AI 機能
- kabusys.ai.score_news(target_date) / kabusys.ai.regime_detector.score_regime(...) を呼ぶとそれぞれ ai_scores / market_regime に書き込みます。OpenAI API キーが必須です。
- API 呼び出しはリトライ・バリデーションを行い、失敗時はフェイルセーフ（スコア 0.0 など）で継続します。

重要な挙動メモ
- プロセス優先度: run_* スクリプトは起動時に set_process_priority("high") を試みます（権限次第でスキップされることがあります）。
- Kill flag: KillSwitch は条件を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine 側はこのファイル存在を確認して停止する設計です（実装により動作）。
- DB マイグレーション: init_monitoring_db() は必要なカラムがなければ ALTER TABLE による追加入力（冪等）を行います。

ディレクトリ構成
----------------
概略（src/kabusys 以下を抜粋）:

- kabusys/
  - __init__.py         — パッケージ情報（__version__ 等）
  - config.py           — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
  - run_monitoring.py   — SystemMonitor ポーリングループ起動
  - run_execution.py    — ExecutionEngine 起動
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py   — SQLite テーブル初期化・読み書きラッパー
    - system_monitor.py  — CPU/メモリ/ディスク/データ鮮度・プロセス監視
    - trade_monitor.py   — 注文滞留 / 約定異常検出
    - risk_monitor.py    — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるループ（run / run_once）
    - kill_switch.py     — kill.flag の管理
    - alert_manager.py   — LINE Push 通知（クールダウン管理）
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - reconciler.py      — 再起動時リコンシリエーション
    - order_manager.py   — 注文状態遷移とブローカー呼び出しの高レベル API
    - order_repository.py, order_record.py, ... （注文 DB/レコード関連）
    - broker_factory.py, broker_api.py 等（ブローカー抽象）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py   — 株数計算・aggregate cap 等
    - risk_adjustment.py   — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py   — Momentum / Volatility / Value ファクター
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py          — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py   — マクロ + ETF MA200 によるレジーム判定
  - data/ (想定)
    - kabusys.duckdb      — DuckDB データベース（prices_daily, raw_financials 等）
    - monitoring.db       — SQLite 監視 DB（system_status, trade_logs, positions, risk_logs, dashboard）
    - paper_trading.db    — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading 時）

開発・運用に関する注意
---------------------
- 機微な取引ロジック・ブローカー API 連携部分は十分なテストと検証を行ってください。実環境での利用は自己責任です。
- OpenAI API にキーを設定する際は漏洩に注意し、使用量・料金管理を行ってください。
- プロセス優先度 / CPU アフィニティ変更は権限によって失敗することがあり、失敗時はログに警告が出ますが処理は継続します。
- Paper Trading モードは本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。

ライセンス・コントリビューション
--------------------------------
本リポジトリのライセンス情報やコントリビュート手順はこの README に含まれていません。必要に応じて LICENSE / CONTRIBUTING ファイルを追加してください。

補足・問い合わせ
----------------
不明点や追加で README に欲しい情報（テスト方法、CI、具体的な設定例など）があれば教えてください。README を拡張して必要なコマンド例やトラブルシュート手順を追記します。
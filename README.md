README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視を目的とした小規模なシステムです。
主な機能は注文発行・リスク管理・監視ログの永続化・ポートフォリオ構築・ファクター計算・
ニュースを使った AI スコアリング・市場レジーム判定などです。  
（パッケージのバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0"）

主な設計方針
- 本番と Paper Trading（検証）を分離可能（環境変数 KABUSYS_ENV）。
- DB は軽量な SQLite と解析向けの DuckDB を併用。
- 外部 API（kabuステーション, J-Quants, OpenAI）への接続を抽象化してあり、テスト / モック運用が容易。
- 監視はプロセス監視・データ鮮度・注文滞留・ドローダウン等を自動記録・アラート可能。

機能一覧
--------
- Execution
  - ExecutionEngine（注文発行・セッション実行）
  - OrderManager / OrderRepository（状態管理、SQLite 保存）
  - RiskManager（ポジション上限・利用率等のルール）
  - Reconciler（起動時の自動リコンシリエーション）
- Monitoring
  - SystemMonitor（CPU, メモリ, ディスク, プロセス状態, データ鮮度）
  - TradeMonitor（滞留注文・約定異常価格検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じた停止フラグ生成）
  - AlertManager（LINE Push による通知）
  - MonitoringEngine（各 Monitor の統合ポーリングループ）
  - Streamlit ベースの監視ダッシュボード
- Portfolio（銘柄選定・重み付け・サイズ算出）
  - 等分配・スコア重み・リスクベースの発注株数算出
  - セクターキャップ適用 / レジーム乗数
- Research
  - factor_research（Momentum / Volatility / Value 等のファクター計算）
  - feature_exploration（将来リターン計算・IC、統計サマリ）
- AI
  - news_nlp（ニュース記事を OpenAI でセンチメント評価、ai_scores へ保存）
  - regime_detector（MA 乖離 + マクロニュースの LLM センチメントを合成してレジーム判定）
- Tools
  - paper_verification_report（Paper Trading の検証レポート生成）

セットアップ手順
----------------
1. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（代表パッケージ）
   - pip install duckdb psutil requests openai streamlit
   - もし requirements.txt がある場合: pip install -r requirements.txt

   補足:
   - sqlite3 は標準ライブラリで提供されます。
   - streamlit は監視ダッシュボード用です。LINE 通知は requests を使用します。

3. 環境変数の設定
   - 必須（実際に接続する機能に依存）:
     - JQUANTS_REFRESH_TOKEN (J-Quants API)
     - KABU_API_PASSWORD (kabuステーション API)
   - OpenAI を利用する場合:
     - OPENAI_API_KEY
   - 実行モード:
     - KABUSYS_ENV = development | paper_trading | live
       - paper_trading の場合、専用の paper DB（data/paper_trading.db）を使用します
   - 主なその他の設定（Settings 参照）:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, PAPER_FILL_MODE, LOG_LEVEL など

   自動 .env ロード:
   - プロジェクトルートに .env / .env.local があれば自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

4. データディレクトリ
   - data/ 配下に DB や flag、pid などを格納します。例:
     - data/monitoring.db
     - data/paper_trading.db
     - data/kabusys.duckdb
     - data/execution.pid
     - data/kill.flag
     - data/stop_requested.flag

使い方
------
起動系
- ExecutionEngine（取引エンジン）を起動
  - 簡易:
    - export KABUSYS_ENV=paper_trading    # または live/development
    - python -m kabusys.run_execution
  - 特記事項:
    - paper_trading モードでは MockBroker を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。
    - プロセス起動時に data/execution.pid を書きます。停止は kill.flag でシグナルを送れます（KillSwitch または kill_switch モジュール経由）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使う設計（KABUSYS_ENV に依存せず本番 DB に書き込む点に注意）

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI / 研究系
- ニューススコアリング（プログラム的呼び出し）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=...)
  - OpenAI API キーが未設定だと ValueError を送出します。

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=...)

監視・停止制御
- stop_requested.flag:
  - run_monitoring.py はプロジェクトルート/data/stop_requested.flag の存在を検知するとループを終了します。
- kill.flag:
  - KillSwitch（デフォルト: Settings.kill_flag_path → data/kill.flag）により ExecutionEngine 停止シグナルを書き込みます。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 で起動時に既存 kill.flag を自動で削除する挙動を制御できます。

設定のヒント
- PAPER_FILL_MODE: paper_trading の注文約定挙動（instant|partial|never|reject）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- PID / flag の挙動は Settings にてパスを変更可能

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定ロード
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — SystemMonitor 起動スクリプト

パッケージ別
- ai/
  - news_nlp.py                    — ニュースの LLM によるセンチメント付与
  - regime_detector.py             — 市場レジーム判定（MA + マクロセンチメント）
- execution/
  - execution_engine.py            — 実行エンジン（メインロジック）
  - order_manager.py               — 注文作成・キャンセル等の外向き API
  - order_repository.py            — SQLite 保存層
  - reconciler.py                  — 起動時の復旧処理
  - broker_factory.py              — ブローカークライアント生成
  - ...                            — BrokerAPI 抽象など
- monitoring/
  - monitoring_db.py               — SQLite のスキーマ・DB 操作ラッパ
  - system_monitor.py              — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py               — 注文滞留・約定異常監視
  - risk_monitor.py                — ドローダウン・ポジション数監視
  - kill_switch.py                 — 停止フラグ管理
  - alert_manager.py               — LINE へ通知送信
  - monitoring_engine.py           — 各 Monitor の統合ループ
  - streamlit_dashboard.py         — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py           — 候補選定・重み付け
  - position_sizing.py             — 株数決定ロジック
  - risk_adjustment.py             — セクター上限・レジーム乗数
- research/
  - factor_research.py             — ファクター計算（momentum/value/vol）
  - feature_exploration.py         — 将来リターン・IC・統計
- tools/
  - paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/                            — 実行時に利用する DB / flags / pid（プロジェクトルート直下）

運用上の注意
-------------
- Paper Trading と本番 DB を混同しないこと。paper_trading モードは専用 DB を利用するよう設計されていますが、設定ミスに注意してください。
- OpenAI API を呼ぶ処理（news_nlp, regime_detector）はレート制限・ネットワーク障害を想定してリトライ・フォールバックを実装していますが、API キー管理とコストには注意してください。
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（デフォルト data/monitoring.db）を使用します。検証用に監視を動かす場合は適切にパスを分けてください。
- 実運用でのプロセス優先度設定は set_process_priority("high") を行いますが、権限や OS により失敗する場合があります（ログに警告が出ます）。

貢献 / 開発
-----------
- コードは src/kabusys 以下にまとまっています。モジュールはできるだけ純粋関数／副作用を明確に分離する設計です。
- テストを書く場合、外部 API 呼び出しはモック可能なように設計されています（例: OpenAI 呼び出し関数を差し替え可能）。

ライセンス / 著作権
------------------
（この README にライセンス情報は含まれていません。プロジェクトに適切な LICENSE を追加してください。）

以上。必要に応じて README に追加すべき点（例: 具体的な環境変数の一覧、requirements.txt、データベース初期化手順など）があれば教えてください。
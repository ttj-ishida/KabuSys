KabuSys — README
=================

概要
----
KabuSys は日本株自動売買を想定したモジュール群です。取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算・研究（Research）、AI を使ったニュース解析（News NLP / Regime Detector）などの機能を含みます。設計方針としては、テスト容易性・フェイルセーフ性・ルックアヘッドバイアス回避を重視しており、DB は SQLite / DuckDB を利用します。

主な特徴
--------
- Execution
  - 注文の生成→送信→状態同期を行う OrderManager（状態遷移管理、重複防止）
  - ブローカー抽象化と Reconciler（起動時の自動復旧・ポジション照合）
  - Paper Trading モード（本番 DB と分離された data/paper_trading.db を使用し MockBroker を利用可能）
- Monitoring
  - SystemMonitor: プロセス稼働・CPU/メモリ/ディスク/データ鮮度を監視、ログを SQLite に永続化
  - TradeMonitor: 注文滞留・約定異常価格を検出しリスクログに記録
  - RiskMonitor: ドローダウン、ポジション上限などを評価しアラート/kill flag を生成
  - AlertManager: LINE Push による一方向通知（トークン未設定時はログ出力で代替）
  - Streamlit ベースの監視ダッシュボード（read-only で監視 DB を閲覧）
- Portfolio Construction
  - 候補選定、等金額／スコア加重の重み計算、ポジションサイズ決定（単元丸め、上限・スケーリング）
  - セクター集中制限やレジーム乗数の適用
- Research
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC（情報係数）・統計サマリ等のユーティリティ
- AI
  - ニュースを LLM（OpenAI）でスコアリングして ai_scores に書き込む機能（batch / retry / validation 実装）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（regime_detector）
- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成（期間指定可）

前提 / 推奨環境
---------------
- Python 3.10 以上（型注釈に Python 3.10 の機能を使用）
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite は標準ライブラリで利用

セットアップ手順
----------------
1. リポジトリをクローンして Python 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（requirements.txt がない場合は最低限以下をインストール）:
   - pip install duckdb psutil requests openai streamlit

3. 環境変数の設定:
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知に使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant/partial/never/reject）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH — kill flag ファイル（デフォルト data/kill.flag）
- KABUSYS_ENV — 起動環境: development | paper_trading | live
- LOG_LEVEL — ログレベル

使い方
------
- 監視ループの起動:
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor をポーリングして monitoring DB にログを記録します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。不正値はデフォルトにフォールバックします。
  - 監視側は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（安全のため）。

- 実行エンジンの起動:
  - python -m kabusys.run_execution
  - 説明: ExecutionEngine を起動してトレード処理を行います。
  - KABUSYS_ENV=paper_trading の場合、MockBroker を利用し data/paper_trading.db を使用して本番 DB と分離します。
  - 実行開始時に pid ファイルを書き、kill.flag による停止シグナルを監視します。

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用モードで monitoring DB を可視化します。DB が存在しない場合は MonitoringEngine を先に起動してください。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD — レポート開始日
    - --to YYYY-MM-DD — レポート終了日
    - --db PATH — SQLite DB パス（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを標準出力にレポートします

- AI / 研究機能（ライブラリ的に利用）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - Research API（例）:
    - calc_momentum(conn, target_date)
    - calc_volatility(conn, target_date)
    - calc_value(conn, target_date)
    - calc_forward_returns(conn, target_date, horizons=[1,5,21])
    - calc_ic(...), factor_summary(...)

注意事項 / 運用メモ
------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。見つからない場合は自動ロードをスキップします。
- .env の優先順位: OS 環境変数 > .env.local > .env
- Monitoring の DB 初期化は init_monitoring_db() にて冪等に行われ、既存 DB に対する簡単なマイグレーション（カラム追加など）も含まれます。
- Execution と Monitoring は異なる DB を使うことがあります（paper_trading モードでは execution が paper DB を使用）。
- kill.flag の存在は ExecutionEngine 停止のシグナルです。KillSwitch は冪等にファイルを書き込み、存在確認・削除メソッドを提供します。
- OpenAI を使う機能は API レート制限や一時エラーを考慮して exponential backoff を実装していますが、API キーの管理と利用料に注意してください。
- プロセス優先度や CPU affinity は utils/process_priority.py 経由で設定します（psutil に依存）。権限不足等で設定に失敗した場合は警告が出ますが継続します。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py                 — パッケージ定義・バージョン
- config.py                   — 環境変数 / 設定管理（.env 自動ロード）
- run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py            — ExecutionEngine 起動スクリプト

- monitoring/
  - __init__.py
  - monitoring_db.py          — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py         — システム状態・データ鮮度監視
  - trade_monitor.py          — 注文滞留・約定異常監視
  - risk_monitor.py           — ドローダウン・ポジション上限監視
  - kill_switch.py            — kill.flag 書き込み / 監視ロジック
  - alert_manager.py          — LINE 通知（クールダウン管理）
  - monitoring_engine.py      — 各モニタを束ねるループ
  - streamlit_dashboard.py    — streamlit を用いたダッシュボード

- execution/
  - order_manager.py          — 注文作成 / 送信の高レベル API
  - order_repository.py       — Orders DB 操作（SQLite）
  - reconciler.py             — 再起動時の状態同期
  - reconciler, broker_* etc. — ブローカー抽象層

- portfolio/
  - portfolio_builder.py      — 候補選定・重み計算
  - position_sizing.py        — 発注株数計算
  - risk_adjustment.py        — セクター制限・レジーム乗数

- research/
  - factor_research.py        — Momentum / Volatility / Value 計算
  - feature_exploration.py    — 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py               — ニュースの LLM スコアリング
  - regime_detector.py        — 市場レジーム判定（MA + LLM）

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

- utils/
  - process_priority.py       — プロセス優先度・CPU affinity 設定ユーティリティ

テスト・開発
-------------
- モジュールは純粋関数と副作用のある部分を分離して設計されています（テスト容易性）。
- DuckDB / SQLite を使うため、ユニットテストではインメモリ DB を使うことで高速に実行できます。
- OpenAI 呼び出し部はテスト中にモックしやすいように構造化されています（_call_openai_api をパッチ可能）。

ライセンス・貢献
----------------
- （リポジトリにライセンスがあればここに記載してください）

以上

必要であれば README にサンプル .env.example、requirements.txt、起動例の systemd ユニットや Dockerfile のサンプルも追加できます。追加希望があれば教えてください。
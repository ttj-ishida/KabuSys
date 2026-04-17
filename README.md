# KabuSys

日本株向け自動売買システムの軽量モジュール群（リサーチ・ポートフォリオ構築・実行エンジン・監視・AI支援）。  
このリポジトリは、戦略リサーチ用のファクター計算、ポートフォリオ構築、注文管理・実行、監視・アラート、及びニュース NLP / レジーム判定などの機能を提供します。

---

## プロジェクト概要

- DuckDB / SQLite を用いた時系列データ処理・ログ保存
- 研究用モジュール（factor / feature exploration）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限、レジーム調整）
- 実行エンジン周辺（OrderManager、Reconciler、ExecutionEngine 起動スクリプト）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor、アラート送信、ダッシュボード）
- OpenAI を用いたニュースセンチメント / マクロ判定（AI モジュール）
- 各種ユーティリティ（プロセス優先度設定、.env ロード等）

設計方針の特徴：
- DuckDB をデータ分析に、SQLite を監視・トレードログに使用
- 本番とペーパートレードを分離（ペーパートレード用 DB を使用）
- ルックアヘッドバイアスを避ける設計（日時参照の扱いに注意）
- フェイルセーフ：外部 API 失敗時は安全側にフォールバック

---

## 主な機能一覧

- リサーチ
  - モメンタム / ボラティリティ / バリュー ファクター計算（kabusys.research）
  - 将来リターン計算、IC（Information Coefficient）等の統計ツール

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（select_candidates）
  - 等配分・スコア配分（calc_equal_weights / calc_score_weights）
  - ポジションサイズ決定（calc_position_sizes）
  - セクター上限適用・レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- 実行周り（kabusys.execution）
  - OrderManager（注文作成・同期）
  - Reconciler（再起動時の同期）
  - ExecutionEngine 起動スクリプト（run_execution.py）

- 監視（kabusys.monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor（metrics ログ・リスク判定）
  - MonitoringDB（SQLite に永続化）
  - AlertManager（LINE push 通知）
  - KillSwitch（条件により execution を停止するフラグ生成）
  - Streamlit ダッシュボード（監視情報の可視化）
  - MonitoringEngine（ポーリングループ）

- AI（kabusys.ai）
  - ニュース NLP（ニュースをまとめて OpenAI に投げる → ai_scores へ）
  - レジーム判定（ETF MA とマクロセンチメントの組合せ）

- ツール
  - paper_verification_report（ペーパートレードログから検証レポート生成）

---

## セットアップ手順

前提（開発環境・サーバ上とも共通）：
- Python 3.9+
- Git（プロジェクトルートを自動検出する仕組みあり）
- 必要パッケージ（例）

推奨の最低インストール例（pip）:
```
pip install duckdb psutil requests openai streamlit
```
※requirements.txt がある場合はそれを利用してください（本リポジトリには示されていません）。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
  - paper_trading の場合、run_execution は MockBroker を使用し、ペーパートレード専用 DB に記録
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視ログ用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH / PID 周りの挙動に関する設定

.env の自動読み込み：
- プロジェクトルートに `.env` / `.env.local` があれば自動で読み込まれます（OS 環境変数が優先）。
- テスト等で自動ロードを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

データディレクトリ：
- data/ 以下に SQLite / DuckDB / pid / flag ファイルが置かれます。必要に応じて作成してください。

初期 DB 作成：
- run_monitoring.py / run_execution.py 実行時に init_monitoring_db が呼ばれ、テーブルが作成されます（冪等）。

---

## 使い方

基本的な実行例（プロジェクトルートで実行）:

1. 監視ループ起動（SystemMonitor）
- デフォルトポーリング間隔: 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能。
- 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存しない点に注意）。
```
python -m kabusys.run_monitoring
```
- 停止: data/stop_requested.flag を作成するか、Ctrl+C（KeyboardInterrupt）。
- 監視起動時にプロセス優先度を "high" に設定します（set_process_priority）。

2. 実行エンジン起動（ExecutionEngine）
- KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、データは data/paper_trading.db に記録されます（本番 DB と分離）。
```
python -m kabusys.run_execution
```
- 実行中の停止は data/stop_requested.flag を作成することでエンジンに伝えます。
- run_execution は ExecutionEngine をスレッドで起動し、stop フラグを監視して安全に停止します。

3. Streamlit ダッシュボード（監視データの可視化）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- ダッシュボードは監視 DB を読み取り専用で開きます（存在しない場合はエラー表示）。

4. Paper Trading 検証レポート生成
- ペーパートレード DB（デフォルト: data/paper_trading.db）から検証レポートを生成します。
```
python -m kabusys.tools.paper_verification_report
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

5. AI 機能（ニュース NLP / レジーム判定）
- OPENAI_API_KEY が必要です。モジュール関数を直接呼び出して使用します（DuckDB 接続を渡す）。
  - ニューススコア付与: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- API 呼び出しで 429 / タイムアウト / 5xx のリトライや、JSON の検証・クリップが実装されています。

運用に関する注意：
- run_monitoring は MONITOR_POLL_INTERVAL と data/stop_requested.flag を利用して挙動を制御します。
- KillSwitch は RiskMonitor の結果（ドローダウン、ポジション上限等）に基づいて data/kill.flag を出力します（Execution 停止トリガー）。
- Monitoring は本番 sqlite を参照するため、環境切替時の DB パスに注意してください。

ログ：
- スクリプトは基本 INFO レベルで logging.basicConfig を行います。詳細ログを見たい場合は LOG_LEVEL を DEBUG に設定してください。

---

## 環境変数（主要一覧・説明）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能で必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（ペーパートレード約定動作）
- PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 1 を設定すると起動時に kill.flag をクリア
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

サンプル .env（例）
```
KABUSYS_ENV=development
LOG_LEVEL=INFO
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## ディレクトリ構成（主要ファイルの説明）

（パスは src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス（各種設定取得）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB と MockBroker）
  - ai/
    - news_nlp.py: ニュースを OpenAI に送りセンチメントを ai_scores に書き込む
    - regime_detector.py: ETF MA と LLM マクロセンチメントを合成して market_regime を書き込む
  - monitoring/
    - monitoring_db.py: SQLite テーブル定義・永続化 API（MonitoringDB）
    - system_monitor.py: CPU/メモリ/ディスク/プロセス状態・データ鮮度チェック
    - trade_monitor.py: 注文滞留／約定異常の検出
    - risk_monitor.py: ドローダウン・ポジション上限の監視
    - monitoring_engine.py: 複数 Monitor を束ねるポーリングエンジン
    - alert_manager.py: LINE push 通知ラッパー
    - kill_switch.py: kill.flag の作成/判定
    - streamlit_dashboard.py: Streamlit を使った監視ダッシュボード
  - execution/
    - order_manager.py: 注文の作成・同期など（OrderManager）
    - reconciler.py: 再起動時の注文・ポジション同期ロジック
    - その他（broker_factory などは実装想定：実際のブローカーAPIラッパー）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 発注株数決定ロジック（単元切捨等）
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: Momentum/Volatility/Value ファクター計算（DuckDB SQL）
    - feature_exploration.py: 将来リターン・IC・統計サマリー
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成
  - utils/
    - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

data/ ディレクトリ（運用で生成されるファイル例）
- data/monitoring.db (SQLite)
- data/paper_trading.db (SQLite, paper_trading 用)
- data/kabusys.duckdb (DuckDB)
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

---

## 運用上の注意・トラブルシューティング

- MONITOR_POLL_INTERVAL に 0 以下を設定すると無効値扱いでデフォルト（60秒）にフォールバックします。
- Monitoring は常に Settings.sqlite_path（本番用）を使用します。開発時に誤って本番 DB を参照しないよう注意してください。
- run_execution は起動時に data/stop_requested.flag が既に存在すると起動を中止します（安全機構）。
- PID ファイル（data/execution.pid）が古い PID を指している場合、SystemMonitor は stale PID と判断してファイルを削除しアラートを出します。
- OpenAI を利用する機能は API 失敗時にリトライやフォールバックを行いますが、API キー未設定時は明示的に例外を出すため設定を忘れないでください。
- SQLite / DuckDB 接続時のパスは Settings でカスタマイズできます。複数インスタンスを立てる場合は DB パスの分離を徹底してください。

---

## 開発・拡張のヒント

- DuckDB クエリはモジュール内で文字列 SQL を使っているため、追加のファクターや集計は SQL を拡張して簡単に実装できます。
- Broker 実装は抽象インターフェイス（BrokerAPIProtocol）に従ってプラグインできます。paper_trading 用の MockBroker は既存の Factory から生成される想定です。
- テスト時は .env の自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で切り、必要な環境変数をテスト側で差し替えると安全です。
- OpenAI 呼び出し部はユニットテストで差し替え可能（_call_openai_api を patch する想定）。

---

この README はコードベースの主要な使い方と構成をまとめたものです。運用前に各モジュールのドキュメント（関数 docstring）を参照し、環境変数や DB パスを適切に設定してください。必要であれば README をプロジェクト固有の運用手順に合わせて追記してください。
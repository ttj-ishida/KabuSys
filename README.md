# KabuSys

日本株自動売買システムの一部（監視・ポートフォリオ構築・リサーチ・AI補助など）を含むライブラリ／実行スクリプト群です。  
この README はコードベース（src/kabusys 以下）に基づく利用方法・セットアップ手順・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買のための内部ライブラリ群と運用用スクリプトを提供します。主な役割は次の通りです。

- 実取引／ペーパートレード用の ExecutionEngine 起動スクリプト（発注・リスク管理・リコンシリエーション）
- 監視（System / Trade / Risk）のポーリングループとログ永続化（SQLite）
- 監視ダッシュボード（Streamlit）
- Paper Trading の検証レポート生成ツール
- ポートフォリオ構築（候補選定・重み計算・株数決定・リスク調整）
- リサーチ（ファクター計算・将来リターン・IC 評価）
- ニュースを用いた LLM ベースのセンチメント評価（OpenAI API 経由）

設計上のポイント：
- DuckDB（時系列・ファクターデータ）と SQLite（監視・注文ログ）を使い分けています。
- Paper Trading は本番 DB と分離され、PAPER_TRADING_SQLITE_PATH を用います。
- .env / .env.local の自動ロード処理を持ち、OS 環境変数を優先します（無効化可能）。

---

## 機能一覧（抜粋）

- 実行／監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 / ペーパー）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - KillSwitch によるフラグファイルで ExecutionEngine を停止可能
  - AlertManager による LINE Push 通知（トークン未設定時は noop）

- 監視コンポーネント
  - SystemMonitor: CPU/Memory/Disk / プロセス PID / データ鮮度を監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン / ポジション数の監視
  - MonitoringDB: SQLite に監視ログ / trade_logs / risk_logs / positions / dashboard テーブルを永続化

- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等重・スコア重み計算（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限・レジーム補正（apply_sector_cap, calc_regime_multiplier）

- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算 / IC（Information Coefficient）計算 / 統計サマリ

- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を LLM に送って銘柄ごとのスコアを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF の MA とマクロ記事センチメントを組み合わせて market_regime を判定・書き込み

- ツール
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL レポートを標準出力

---

## 前提条件

- Python 3.10+
- OS: Linux/macOS/Windows（ただし一部機能は POSIX/Windows で挙動が異なります）
- システムライブラリ（標準）: sqlite3
- Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
※ requirements.txt は本リポジトリに含まれていないため、上記パッケージを個別にインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン／展開し、プロジェクトルートに移動する。

2. 仮想環境を作成して依存パッケージをインストール（上記参照）。

3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須変数の例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI機能使用時）
   - 主要な設定（省略可、デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL 等

4. データディレクトリの作成
```
mkdir -p data
```
5. DuckDB / SQLite の初期化は実行スクリプト内で必要に応じて行われます（init_monitoring_db など）。

注意:
- 実行時にプロセス優先度の設定（psutil）を行います。権限不足の際は警告が出ますが処理は継続します。

---

## 実行方法（主なスクリプト）

プロジェクトルートで Python モジュールとして実行できます（PYTHONPATH が通っていることが前提）。

- 監視ループ起動（SystemMonitor ポーリング）
```
python -m kabusys.run_monitoring
```
環境変数:
- MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満や不正値は無視されデフォルトに戻ります。

監視は Settings.sqlite_path（監視 DB）を使用します。Settings は .env/.env.local や環境変数からロードされます。

- 実行エンジン起動（ExecutionEngine）
```
python -m kabusys.run_execution
```
- KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と完全に分離します。
- 起動時に PID ファイル (Settings.pid_file_path) を使ってプロセス生存確認／再起動検知などを行います。

- 監視ダッシュボード (Streamlit)
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
db 引数を指定しない場合はデフォルト `data/monitoring.db` を参照します。ダッシュボードは読み取り専用で DB を開きます。

- Paper Trading 検証レポート
```
python -m kabusys.tools.paper_verification_report
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
主な判定基準（ソース内定義）:
- 稼働率 >= 99%
- 注文成功率（Filled/Created） >= 90%
- 送信率（Sent/Created） >= 95%
- P95 レイテンシ <= 200 ms

- AI / レジーム判定（ライブラリ関数）
  - ニューススコア算出: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

これらは DuckDB 接続を受け取り、内部で ai_scores / market_regime テーブルへ書き込みます。OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用します。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（必須ではないが valid 値チェックあり）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須使用時）
- KABU_API_PASSWORD: kabuステーション API（必須使用時）
- OPENAI_API_KEY: OpenAI API（AI機能を使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- PID_FILE_PATH: PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH: Kill フラグファイル（default: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE Push）用

詳しくは src/kabusys/config.py の Settings クラスを参照してください。プロジェクトルートの .env/.env.local に設定することで自動読み込みされます（ただし OS 環境変数が優先）。

---

## 注意点 / 運用メモ

- run_execution と run_monitoring はプロセス優先度を "high" に設定しようとします（psutil を利用）。権限不足で失敗することがありますが、ログに警告が出るだけで続行されます。
- Monitoring は常に本番 sqlite_path を参照してログ記録します（監視データは本番 DB を使う設計）。ただし run_execution は KABUSYS_ENV=paper_trading のとき専用 DB を使います。
- KillSwitch は KILL_FLAG_PATH のファイル存在をもって ExecutionEngine に停止指示を送ります。既存ファイルがあれば再書き込みしません。起動時に KILL_FLAG_CLEAR_ON_START を使ってクリアする挙動があります（Settings を参照）。
- AI 呼び出しは外部 API（OpenAI）に依存します。API 呼び出し時のエラー・レート制限に対してはリトライ・フォールバック処理が実装されていますが、APIキー未設定時は例外が発生します。テスト時は _call_openai_api をモックできます（ユニットテスト向け）。
- DuckDB のクエリは時刻や target_date の取り扱いでルックアヘッドバイアスを防止する実装になっています。研究コードは prices_daily / raw_financials / raw_news テーブルのみを参照します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルと役割の一覧です（完全版ではありませんが主要点を含みます）。

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン、エクスポート）
  - config.py — 環境変数 / 設定管理（.env 自動ロードを含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（Paper Trading 切替対応）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor をまとめて定期実行する Engine
    - kill_switch.py — フラグファイル書き込みによる停止指示
    - alert_manager.py — LINE Push 通知ラッパー
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 発注管理（Order State Machine 外向き API）
    - order_repository.py — SQLite ベースの注文リポジトリ（このリポジトリに含まれない場合は別モジュール）
    - reconciler.py — 再起動・クラッシュ後の同期処理（ブローカー照合）
    - ...（broker_factory, execution_engine 等、コードベースに依存）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・リスク制限・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py — MA + マクロセンチメントで市場レジームを判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 開発 / テストのヒント

- OpenAI 呼び出し部分は _call_openai_api をモックすることでユニットテスト可能です（news_nlp, regime_detector における注釈参照）。
- DuckDB に対するリサーチ関数は副作用がなく、DuckDB の接続をモックまたはテスト用ローカル DB を用意して実行できます。
- MonitoringDB.init_monitoring_db は冪等でテーブル・インデックスを作成します。既存 DB に対するマイグレーションも一部含まれます（列追加など）。

---

## 参考 / 追加情報

- config.py 内に .env 読み込みロジックと Settings クラスのプロパティ仕様があります。新しい設定を追加する場合はここにプロパティを追加してください。
- run_execution / run_monitoring はプロセス優先度設定（set_process_priority）を最初に呼びます。管理者権限が必要な場合があります。
- Paper Trading の挙動や fill_mode などは Settings.paper_fill_mode の値に依存します。

---

この README はコードベースから主要な使用方法と構成を抜粋してまとめたものです。より詳細な設計意図やアルゴリズム（例: PortfolioConstruction.md, StrategyModel.md）については別途ドキュメントを参照してください。必要があれば README に追加したい情報（例: サンプル .env.example、requirements.txt、実行フロー図など）を教えてください。
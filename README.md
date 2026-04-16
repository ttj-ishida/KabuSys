# KabuSys

日本株自動売買システムのリポジトリ（モジュール抜粋）。  
この README はソースコード（src/kabusys 以下）に基づいて作成した簡易ドキュメントです。

> 注: 実行には Python 3.10 以上を推奨します（型アノテーションや | 型記法を使用）。

---

## 概要

KabuSys は日本株の自動売買／リサーチ／監視を行うためのコンポーネント群です。  
主な機能として、注文実行エンジン（ExecutionEngine）、監視コンポーネント（MonitoringEngine）、ポートフォリオ構築ユーティリティ、ファクター計算・研究モジュール、LLM を用いたニュース NLP や市場レジーム判定などを提供します。

設計上のポイント：
- 本番／ペーパートレードを環境変数 `KABUSYS_ENV` で切替可能（development / paper_trading / live）。
- Paper Trading は本番 DB と完全分離（専用 SQLite ファイル）。
- DuckDB を分析用（prices_daily / raw_financials など）に使用。
- 監視情報は SQLite（monitoring.db）に永続化。
- OpenAI（gpt-4o-mini 相当）を用いたニュースセンチメントやレジーム判定機能あり（API キー必須）。

---

## 機能一覧（抜粋）

- execution
  - OrderManager / ExecutionEngine / Reconciler（起動時の自動リコンシリエーション）
  - Broker クライアント抽象化（paper_trading 時は MockBrokerClient を利用）
- monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 /プロセス生存確認
  - TradeMonitor：滞留注文、約定価格の異常検知
  - RiskMonitor：ドローダウン、ポジション数上限検出、ダッシュボードの永続化
  - MonitoringEngine：上記を束ねてポーリング、Kill Switch / AlertManager と連携
  - AlertManager：LINE Push による一方向通知（クールダウン実装）
  - Streamlit ベースの監視ダッシュボード
- portfolio
  - 銘柄選定、重み計算（等重／スコア重み）、セクターキャップ、ポジションサイジング（単元丸め、リスクベース）
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）や統計要約
- ai
  - news_nlp：ニュース記事を LLM でセンチメント評価し ai_scores に書込
  - regime_detector：ETF の MA200 とマクロニュースの LLM スコアを合成して日次レジーム判定
- tools
  - paper_verification_report：Paper Trading DB を集計して検証レポート出力

---

## 必要要件（想定）

主な Python パッケージ（最低限）：
- duckdb
- psutil
- requests
- streamlit
- openai

推奨コマンド例（仮想環境下で）：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests streamlit openai
```
プロジェクトに `requirements.txt` があれば `pip install -r requirements.txt` を使ってください。

---

## セットアップ手順

1. リポジトリをクローン／取得する。
2. 仮想環境を作成して依存パッケージをインストール（上記参照）。
3. プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成する。`.env.example` を参考に必須値を設定してください。
   - 自動で `.env` をロードする仕組みがあるため（Settings モジュール）、通常は追加処理不要です。自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
4. データディレクトリ（`data/`）を作成しておくと便利（PID/flag/DB を配置）。
5. 必要に応じて DuckDB 用の分析データ（prices_daily など）を用意する。

---

## 主な環境変数（Settings に定義されているもの）

- KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager 用（未設定なら送信はスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の fill モード（instant | partial | never | reject） — デフォルト: instant
- PID_FILE_PATH: execution.pid のパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を削除するか（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## 使い方（主要コマンド）

- 監視ループを起動（Monitoring; MONITOR_POLL_INTERVAL で秒間隔を上書き可能）：
```bash
python -m kabusys.run_monitoring
# 例: ポーリングを30秒にしたい場合
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Execution エンジンを起動（paper_trading 環境では MockBroker を使い paper DB に記録）：
```bash
python -m kabusys.run_execution
# paper_trading 環境で起動する例
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- Streamlit 監視ダッシュボードを起動（読み取り専用で monitoring.db を開く）：
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- Paper Trading 検証レポート生成：
```bash
python -m kabusys.tools.paper_verification_report
# 期間指定例
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB 指定
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- AI スコア付け（プログラム呼び出し例）
  - news_nlp.score_news(conn, target_date, api_key=None) — OpenAI API キー必要（引数または OPENAI_API_KEY 環境変数）

停止・制御に関するフラグ：
- run_execution / run_monitoring はプロジェクトルート下の `data/stop_requested.flag` を監視しており、存在すると安全に停止します。
- KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送る（監視側が条件を満たしたときに書き込む）。

---

## 実行上の注意点 / 動作の補足

- run_monitoring は Monitoring 用テーブルが存在することを保証するため起動時に `init_monitoring_db()` を呼びます。MONITOR_POLL_INTERVAL は環境変数で上書き可能（デフォルト 60 秒）。0 以下の値は無視されデフォルトにフォールバックします。
- run_execution は `KABUSYS_ENV=paper_trading` のときに paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全に分離します。
- Process 優先度（High/Normal/Low）は psutil を使って設定します（set_process_priority）。権限不足等で設定できない場合は warning を出してスキップします。
- AI 周り（news_nlp / regime_detector）は OpenAI API を利用します。API 呼び出しに失敗した場合はフェイルセーフとして一部ロジックで neutral（0.0）やスキップを採りますが、API キー未設定では例外を発生させる関数もあります（明示的なエラー報告）。
- DuckDB のクエリは主に prices_daily / raw_financials / raw_news 等のテーブルを前提にしています。これらは別途データ投入が必要です（データ取得パイプラインは kabusys.data パッケージに依存）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル・モジュールのツリー（今回提供されたソースに基づく抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - reconciler.py
      - order_manager.py
      # （その他 Execution 関連モジュールはリポジトリ内に存在する想定）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/   # 実行時に使用されるファイル（DB, pid, flags）を想定
      - monitoring.db (デフォルト: SQLITE_PATH)
      - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
      - kabusys.duckdb (DUCKDB_PATH)
      - execution.pid
      - stop_requested.flag
      - kill.flag

---

## 開発者向けメモ

- Settings（config.py）はプロジェクトルートにある `.env` / `.env.local` を自動ロードします。OS 環境変数が優先されます。自動ロードを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading の挙動（fill 模擬）は `PAPER_FILL_MODE` で制御できます（instant/partial/never/reject）。
- 監視データのマイグレーション（dashboard テーブルに peak_value カラム追加等）は `init_monitoring_db()` 内で自動的に行われます。
- Streamlit ダッシュボードは DB を読み取り専用モードで開くよう推奨（起動時に読み取り専用 URI を渡して使用）。

---

## よくある操作フロー（例）

1. 環境変数設定（.env）を用意する。
2. DuckDB に株価データをロードする（prices_daily 等）。
3. Paper Trading でまず検証：
   - KABUSYS_ENV=paper_trading をセットして ExecutionEngine を起動（MockBroker による動作確認）
   - MonitoringEngine を起動して監視ログを収集
   - `python -m kabusys.tools.paper_verification_report --from ... --to ...` で検証レポートを出力
4. 準備が整ったらライブ用設定で起動（十分なテストとリスク管理を実施のこと）

---

この README はソースコード（一部）に基づいた概要ドキュメントです。実運用前には各モジュールの実装、依存、API キー・認証情報の管理方針、ハードウェア要件、テスト方針を必ず確認してください。必要であれば、各モジュール毎の詳細なドキュメント（API、設定例、マイグレーション手順）を追加作成することを推奨します。
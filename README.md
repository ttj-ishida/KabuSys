# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。トレード実行・監視・ポートフォリオ構築・リサーチ・AI ニューススコアリング等のコンポーネントを含み、ローカル SQLite / DuckDB を使って動作します。

以下はコードベース（src/kabusys）に基づく README です。

## プロジェクト概要
- 目的: 日本株の自動売買パイプライン（Signal → Execution → Monitoring）を実装するためのモジュール群。
- 主な構成:
  - Execution（発注・注文管理・再突合）
  - Monitoring（プロセス/リスク/注文監視、LINE アラート、Streamlit ダッシュボード）
  - Portfolio（候補選定・重み付け・ポジションサイズ算出・リスク調整）
  - Research（ファクター計算、特徴量探索）
  - AI（ニュース NLP によるセンチメント／レジーム判定）
  - Tools（紙取引検証レポート等）
- データ永続化:
  - SQLite: 監視ログ（デフォルト `data/monitoring.db`）や Paper Trading 用 DB（`data/paper_trading.db`）
  - DuckDB: 時系列市場データなど（デフォルト `data/kabusys.duckdb`）

## 主な機能一覧
- Execution
  - ブローカー抽象化（本番 / Paper Trading 切替）
  - OrderManager による注文ライフサイクル管理
  - Reconciler による再起動後の自動復旧（ブローカー照合・ポジション差分検出）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 滞留注文検知・約定異常価格検知
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件により `data/kill.flag` を書いて Execution を停止
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用）
- Portfolio
  - 候補選定、等金額／スコア加重配分、セクター制限、ポジションサイズ計算（lot 単位丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を直接参照）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- AI
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメント集計と ai_scores へ書込
  - regime_detector: ETF（1321）MA200 とマクロニュースを合成して市場レジーム判定（market_regime テーブルへ保存）
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

## 必要条件 / 依存パッケージ
- Python 3.9+ 推奨
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite3 は標準ライブラリで使用

（本リポジトリに requirements.txt がない場合は上記を pip でインストールしてください）
例:
```
pip install duckdb psutil openai requests streamlit
```

## セットアップ手順（ローカルでの最小構成）
1. リポジトリをクローンしてワークディレクトリに移動
2. 必要パッケージをインストール（上記参照）
3. `data/` ディレクトリを作成（アプリ実行時に自動作成する箇所もありますが明示的に）
```
mkdir -p data
```
4. 環境変数を設定（.env ファイルをプロジェクトルートに配置するか OS 環境に設定）
   - 主要な環境変数（Settings で参照されるもの）
     - JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
     - KABU_API_PASSWORD — 必須（kabuステーション API 用）
     - OPENAI_API_KEY — AI モジュール利用時に必要
     - KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading の約定挙動 ("instant"|"partial"|"never"|"reject")
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（未設定なら通知は送られません）
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag をクリアする場合は "1"

サンプル .env（例）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

## 実行方法（主要なコマンド）

- 監視ループ起動（SystemMonitor 単体で db に記録）
```
python -m kabusys.run_monitoring
```
- Execution エンジン起動（ブローカー接続・Order マネジメント）
```
python -m kabusys.run_execution
```
注意:
- KABUSYS_ENV が `paper_trading` の場合、Execution は MockBrokerClient を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込みます。本番 DB と完全分離されます。
- `run_monitoring` は環境にかかわらず Settings.sqlite_path（監視用 DB）を使用します（監視ログは本番 DB を参照する想定のため）。

- Streamlit ダッシュボード起動（監視 DB の読み取り専用ビュー）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート（CLI）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB パスを直接指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI ニューススコアリング（プログラム的に呼ぶ）
  - duckdb 接続を渡して kabusys.ai.score_news(conn, target_date, api_key=None) を呼びます。
  - OPENAI_API_KEY が必要（引数または環境変数で指定）。

## 停止 / キル挙動
- プロセスの優雅な停止（監視ループ / 実行エンジン共通）:
  - 監視 / 実行ループはプロジェクトルート `data/stop_requested.flag` の有無を監視しています。停止を要求するにはこのファイルを作成してください（例: `touch data/stop_requested.flag`）。起動時に存在すると ExecutionEngine は起動を拒否します。
- KillSwitch:
  - RiskMonitor 等の評価によって `data/kill.flag` が書き込まれると ExecutionEngine に停止を促す仕組みが動きます（KillSwitch は冪等に書き込み）。`Settings.kill_flag_clear_on_start` を使うと起動時に kill.flag を消すオプションがあります（環境変数 KILL_FLAG_CLEAR_ON_START=1）。

## 重要な設定 / 環境変数（Summary）
- KABUSYS_ENV: development | paper_trading | live
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、既定 60）。無効値はデフォルトにフォールバック。
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
- OPENAI_API_KEY: AI 系機能で必要
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 用の必須トークン
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知用

## ディレクトリ構成（主なファイルと役割）
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数と Settings クラス（.env の自動読み込みロジック含む）
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB を使用）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py — 監視ログ用 SQLite スキーマ / 永続化 API（init_monitoring_db, MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常検知
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書込みユーティリティ
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視 UI
  - execution/
    - order_manager.py — OrderManager（外向き API）
    - reconciler.py — 再起動時の照合ロジック
    - （他の execution モジュール: broker_factory, execution_engine, order_repository など）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・aggregate cap
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング（OpenAI）
    - regime_detector.py — マーケットレジーム判定（MA200 + LLM）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

※上記は主要モジュールの概観です。細かな内部 API（OrderRecord, BrokerAPIProtocol 等）は各モジュールを参照してください。

## 運用上の注意
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル作成・簡易マイグレーション（カラム追加）を行います。初回起動で自動的に必要テーブルを作成します。
- Paper Trading: `KABUSYS_ENV=paper_trading` に切り替えることで発注はモックブローカーへ向かい、データも paper_trading 用 DB に書き込まれます（本番 DB へ影響を与えない設計）。
- OpenAI API: news_nlp / regime_detector は API 呼び出しに失敗した際、フェイルセーフ（スコアを 0 にする等）で継続する実装になっていますが、API キーの管理とレート制御には注意してください。
- 権限: プロセス優先度や CPU affinity の設定は OS/権限に依存し、失敗時は警告を出してスキップします。

## 追加情報 / 開発
- テストや CI では .env の自動読み込みを無効化できます: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- モジュール単位での実行は Python のモジュール実行（python -m <module>）が想定されています。
- ローカルでの検証には paper_trading モードが便利です（ブローカー呼び出しをモック化し安全に検証可能）。

---

その他の詳細（各関数の引数説明や挙動）はソースコード内の docstring を参照してください。必要であれば README に「セットアップの詳細手順」や「開発向けのデバッグ手順」を追加できます。どのような追加情報が必要か教えてください。
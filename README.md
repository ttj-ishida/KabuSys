# KabuSys — README

このリポジトリは日本株の自動売買・リサーチ・監視を目的とした内部ライブラリ群と実行スクリプト群を含みます。  
以下はコードベース（src/kabusys 以下）を元にした README です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群を提供します。主な機能は以下の通りです。

- 注文管理・発注エンジン（ExecutionEngine, OrderManager, Reconciler 等）
- リスク管理・リコンシリエーション機能
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE）
- 監視データの永続化（SQLite）と可視化（Streamlit ダッシュボード）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制限）
- 研究用ファクター計算（DuckDB 経由）
- AI（OpenAI）を使ったニュースセンチメント評価 / 市場レジーム判定
- Paper Trading 用の分離 DB / 検証レポート生成ツール

設計上のポイント：
- DuckDB / SQLite をデータ基盤として利用（ローカルファイル）
- 設定は環境変数（.env / .env.local を自動読み込み）で管理
- Paper Trading は本番 DB と分離（`data/paper_trading.db` を使用）
- モジュールはテストしやすい純粋関数／副作用を限定した設計を心がけている

---

## 機能一覧（主要コンポーネント）

- kabusys.config
  - 環境変数の自動読み込み（.env / .env.local）、設定ラッパー `Settings`
  - 主要環境: `development`, `paper_trading`, `live`
- kabusys.execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager、OrderRepository、Reconciler、RiskManager など
- kabusys.monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringDB: SQLite テーブルの初期化・読み書き（init_monitoring_db）
  - MonitoringEngine: 各モニタの統合ポーリング
  - AlertManager: LINE プッシュ通知
  - KillSwitch: フラグファイルを書いて ExecutionEngine を停止させる仕組み
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- kabusys.portfolio
  - 候補選定（select_candidates）、重み計算（equal/score）
  - リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（lot 単位丸め、aggregate cap）
- kabusys.research
  - ファクター計算（momentum, volatility, value）・将来リターン・IC 計算など
- kabusys.ai
  - news_nlp: ニュースを OpenAI で評価し ai_scores に保存
  - regime_detector: マクロ + MA200 を組み合わせて日次レジーム判定
- kabusys.tools
  - paper_verification_report: Paper Trading DB から検証レポートを出力

ユーティリティ:
- kabusys.utils.process_priority: プロセス優先度 / CPU affinity 設定
- その他：DuckDB / SQLite を直接扱うクエリ群

---

## セットアップ手順

前提:
- Python 3.9+（実際の要件はプロジェクトの pyproject/requirements を参照）
- system パッケージ: libpq 等は不要だが、psutil のビルドが必要な場合はビルドツールが必要

1. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要な Python パッケージをインストール
   - 例:
     pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください。）

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数 (.env) を用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（既存 OS 環境変数は保護されます）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 主要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
   - KABUSYS_ENV: 実行環境（development | paper_trading | live）、デフォルトは development
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（オプション）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、監視起動スクリプト用。デフォルト 60）
   - PAPER_FILL_MODE: paper_trading のモック約定モード ("instant" | "partial" | "never" | "reject")
   - PID_FILE_PATH / KILL_FLAG_PATH: 実行管理用ファイルパス（デフォルト data/execution.pid / data/kill.flag）

   例 .env（最小）
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   ```

---

## 使い方（主要スクリプト・コマンド）

- 監視ループ起動（Monitoring）
  - 動作: SystemMonitor のポーリングを開始し、監視ログを monitoring SQLite に記録します。kill.flag を用いて ExecutionEngine 停止シグナルを送る仕組みを利用します。
  - 実行:
    python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でループ間隔（秒）を上書き（デフォルト 60）
  - 備考:
    - 監視は環境にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用します（監視データは常に共有 DB）。

- 実行エンジン起動（ExecutionEngine）
  - 動作: ExecutionEngine を起動し、ブローカークライアント（本番 or モック）を用いて注文処理を行います。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い `data/paper_trading.db` に記録して本番 DB と完全分離します。
  - 実行:
    python -m kabusys.run_execution
  - 環境:
    - KABUSYS_ENV=paper_trading とすると Paper Trading モード
    - Paper Trading 用 DB は `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db`

- Streamlit 監視ダッシュボード
  - 実行:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 備考:
    - `--` 以降の引数がダッシュボードスクリプトに渡されます（既定 db を上書き可能）
    - DB を読み取り専用で開きます（監視が走っていることを前提）

- Paper Trading 検証レポート生成
  - 実行:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（プログラム API）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、指定日付のニュースをスコア化して ai_scores に書き込む
    - api_key を指定しない場合、環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、レジームを計算して market_regime テーブルに書き込む
  - 注意: OpenAI API キーが必須。API 呼び出しは冪等性・リトライを考慮した実装になっていますが、API料金・レート制限に注意してください。

---

## 重要な実行上の注意点 / 運用メモ

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml があるパス）を探索して `.env` / `.env.local` をロードします。OS 環境変数は上書きされません。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading と本番 DB 分離
  - `KABUSYS_ENV=paper_trading` のとき、ExecutionEngine は `PAPER_TRADING_SQLITE_PATH` を使用します（本番 DB とは別ファイル）。
  - 監視（Monitoring）は常に `Settings.sqlite_path`（デフォルト data/monitoring.db）を使用します。
- kill.flag（停止シグナル）
  - KillSwitch は `Settings.kill_flag_path`（デフォルト data/kill.flag）を作成し、ExecutionEngine に停止を促します。kill.flag が存在すると ExecutionEngine 側で停止処理を行う設計になっています（ExecutionEngine 側の実装に依存）。
  - 起動時にフラグをクリアしたい場合は `Settings.kill_flag_clear_on_start` を確認する設定に従ってください。
- プロセス優先度 / CPU affinity
  - 起動スクリプトは set_process_priority("high") を呼びます。psutil を使って OS に応じて優先度を設定しますが、権限不足や対応外 OS の場合はログに警告を出してスキップします。
- DB マイグレーション
  - init_monitoring_db はテーブル作成と単純なマイグレーション（カラム追加）を行います。既存データは保持されますが、本格的なマイグレーションが必要な変更時は注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — レジーム判定（MA200 + マクロ）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（init_monitoring_db, MonitoringDB）
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor の統合
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - reconciler.py — 起動時リコンシリエーション
    - order_manager.py — 注文状態遷移管理
    - （その他 repository / order_record などが存在）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数計算
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - utils/
    - process_priority.py — nice / priority / cpu_affinity ユーティリティ
  - monitoring/ や execution/ の各モジュールは MonitoringDB / OrderRepository 等を通じて SQLite に読み書きします。

（上記はリポジトリ内の主要ファイルを抜粋したものです。実際のリポジトリにはさらに補助モジュールやデータ処理パイプラインが存在する可能性があります。）

---

## よくある質問（短いトラブルシューティング）

- psutil で優先度が設定できない / AccessDenied が出る  
  → 権限不足（非 root）か OS が未サポートです。ログは警告を出し、処理は継続します。

- OpenAI を使うときエラーが出る（API key 関連）  
  → `OPENAI_API_KEY` を環境変数に設定するか、関数呼び出し時に `api_key` を渡してください。API エラー時はモジュール内でリトライやフェイルセーフ（スコア 0.0 など）を行いますが、料金・レート制限には注意してください。

- monitoring.db が空 / テーブルがないと言われる  
  → run_monitoring/run_execution のいずれか（init_monitoring_db を呼ぶ箇所）が正常に実行されていることを確認してください。`init_monitoring_db` は冪等でテーブル作成を行います。

---

この README はコードベースの主要な動作と使い方のガイドラインをまとめたものです。実際の導入・運用時はプロジェクトの pyproject.toml / requirements.txt、CI 設定、運用手順書を参照してください。必要であれば具体的な起動例や .env.example を作成できます。
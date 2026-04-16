# KabuSys

日本株自動売買システムのコアライブラリ群（監視・実行・ポートフォリオ構築・リサーチ・AI ニュース解析など）。  
この README はコードベース（src/kabusys 以下）を対象に、概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 注文管理・発注実行（ExecutionEngine + OrderManager + BrokerClient）
- 実行系の監視とアラート（MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, AlertManager）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算、セクター制限等）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- AI を用いたニュースセンチメント評価 / 市場レジーム判定（OpenAI API 経由）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針の一部：
- 本番 DB と Paper Trading DB は分離（KABUSYS_ENV で切替）
- ルックアヘッドバイアス対策（date.today() を直接参照しない等）
- OpenAI 呼び出しはリトライ・フェイルセーフ実装

---

## 主な機能一覧

- 実行（run_execution.py）
  - 本番 / Paper Trading を切替可能（KABUSYS_ENV）
  - BrokerClientFactory により実ブローカー or MockBroker を使用
  - リコンシリエーション（Reconciler）で再起動後の同期
  - リスク管理（RiskManager）を組み込んだ ExecutionEngine

- 監視（run_monitoring.py / MonitoringEngine）
  - CPU / メモリ / ディスク / 実行プロセス存在確認の定期ログ化
  - 注文滞留、約定異常価格、ドローダウン、ポジション上限の検出
  - kill.flag による ExecutionEngine 停止（KillSwitch）
  - LINE によるアラート送信（AlertManager）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（select_candidates）
  - 等分配・スコア加重の重み算出
  - セクター上限適用（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）

- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリューのファクター算出（DuckDB 使用）
  - 将来リターン計算、IC（Spearman）や統計サマリ

- AI（kabusys.ai）
  - ニュースセンチメントを OpenAI でスコア化し ai_scores に格納
  - 市場レジーム判定（ma200 + マクロニュースセンチメントを合成）

- ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - Streamlit 監視ダッシュボード（monitoring/streamlit_dashboard.py）

- 永続化（kabusys.monitoring.monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル等を管理し、DB マイグレーションも一部対応

---

## セットアップ手順

前提：Python 3.10+（typing の | 記法を使用）を推奨します。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（requirements.txt がない場合は主要依存を直接）
   ```
   pip install psutil duckdb openai requests streamlit
   ```
   追加の依存（環境による）：SQLite は標準ライブラリで OK。

4. data ディレクトリ作成（DB や PID/flag を格納）
   ```
   mkdir -p data
   ```

5. 環境変数設定
   - .env または .env.local をプロジェクトルートに置くと自動で読み込みます（OS 環境変数が優先）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（主なもののみ）：
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
   - LOG_LEVEL, PID_FILE_PATH, KILL_FLAG_PATH, 等

   .env のフォーマットはシェル風（コメントやクォート対応）です。コード内にパーサが実装されています。

6. DB の初期化
   - run_monitoring.py / run_execution.py を起動すると init_monitoring_db() が呼ばれ監視用テーブルが作成されます。
   - DuckDB テーブル（prices_daily や raw_financials 等）は別途データ取り込みが必要です（研究・ファクター計算で利用）。

---

## 使い方（よく使うコマンド例）

- 監視ループ起動（監視データの定期ログ化・KillSwitch 評価）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（1 以上、デフォルト 60）。

- 実行エンジン起動（注文送信・ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して Paper Trading DB（data/paper_trading.db）に記録します。
  - 起動前に `data/stop_requested.flag` が存在すると起動をスキップします。監視・停止は同ディレクトリのフラグファイルで制御します。

- Streamlit 監視ダッシュボード（読み取り専用 DB を指定して起動）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で SQLite ファイルを明示可能。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可。

- AI ニューススコアリング（プログラム的に利用）
  - OpenAI API キーを用意して、kabusys.ai.score_news(conn, target_date, api_key=...) を呼び出してください。
  - 同様に regime 判定は kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止方法（運用中）：
- ExecutionEngine 停止要求: `data/kill.flag` を書き込むと ExecutionEngine に停止シグナルとして扱われます（KillSwitch/Alert の運用）。
- 即時終了を要求する場合は `data/stop_requested.flag` を作成すると run_monitoring や run_execution のループが検知して終了します。

ログレベル:
- Settings.log_level（環境変数 LOG_LEVEL）で INFO/DEBUG 等を設定できます。

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数 / Settings 管理（.env 読み込みロジック含む）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

kabusys/monitoring/
- monitoring_db.py — SQLite ベースの監視 DB（テーブル作成・CRUD）
- system_monitor.py — CPU/メモリ/ディスク・データ鮮度・PID チェック
- trade_monitor.py — 注文滞留 / 約定価格異常検出
- risk_monitor.py — ドローダウン / ポジション上限監視
- monitoring_engine.py — 各 Monitor を束ねるループ（run / run_once）
- kill_switch.py — kill.flag 書き込み・評価ロジック
- alert_manager.py — LINE Push API による通知
- streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

kabusys/execution/
- order_manager.py — 発注ワークフロー（OrderRecord と OrderRepository 統合）
- reconciler.py — 再起動時の同期（注文・ポジション照合）
- order_repository.py, execution_engine.py, broker_factory 等（実行ロジックはディレクトリ内に実装）

kabusys/portfolio/
- portfolio_builder.py — 候補選定・スコアソート
- position_sizing.py — 株数算出・スケーリング・単元丸め
- risk_adjustment.py — セクター制限・レジーム乗数
- __init__.py — エクスポート

kabusys/research/
- factor_research.py — Momentum / Volatility / Value ファクター
- feature_exploration.py — 将来リターン、IC、統計サマリ
- __init__.py — エクスポート（zscore_normalize を含む）

kabusys/ai/
- news_nlp.py — raw_news を OpenAI でスコアし ai_scores に書き込むロジック
- regime_detector.py — ma200 + マクロセンチメントで market_regime を判定
- __init__.py — エクスポート

kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- その他ユーティリティ

kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成

data/
- （実行時生成）monitoring.db（SQLite）, kabusys.duckdb, paper_trading.db, PID/flag ファイル等

---

## 追加の注意点 / 運用メモ

- 環境分離:
  - `KABUSYS_ENV=paper_trading` では実アカウントに触らないよう MockBroker を使用し、Paper Trading DB に記録されます。
  - Monitoring はコード上「環境にかかわらず本番 sqlite_path を使用する」箇所があるため、運用時は設定を確認してください（run_monitoring 内コメント参照）。

- OpenAI 関連:
  - API 呼び出しはリトライや JSON バリデーションを行いますが、API キーが未設定の場合は例外を投げます（score_news / score_regime）。
  - レスポンスの検証を慎重に行う設計になっています（スコアのクリップ、未知コードの無視、部分成功の DB 保護等）。

- DB マイグレーション:
  - init_monitoring_db() は既存 DB のカラム追加（例: latency_ms や peak_value）を行う簡易的なマイグレーション処理を含みます。

- PID / flag 管理:
  - 実行プロセスは PID ファイル（デフォルト data/execution.pid）を作成することを想定。
  - stale PID 検出時にファイルを削除しアラートを残す挙動があります。

---

## よくあるコマンドまとめ

- 監視を起動: python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
- Streamlit ダッシュボード: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

この README はコードからの抜粋・要約に基づいて作成しています。実運用前に各 Settings / 環境変数 / DB パスおよび Broker の実装を必ず確認してください。必要であれば各モジュール毎の詳細ドキュメント（関数・引数・返り値の仕様）も作成できます。
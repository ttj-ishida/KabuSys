# KabuSys

バージョン: 0.1.0

日本株自動売買システムの一部実装（ライブラリ + 実行スクリプト群）。  
本リポジトリには、発注エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ用ファクター計算、AI を用いたニュース NLP / レジーム判定、各種ユーティリティが含まれます。

※ この README はソースコード（src/kabusys）を基に作成しています。

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- 環境変数（主要）
- セットアップ手順
- 使い方（実行方法・コマンド例）
- ディレクトリ構成（主なファイル説明）
- 運用時の注意点

---

## プロジェクト概要

KabuSys は日本株自動売買システム向けのモジュール群です。  
コンポーネントは概ね下記の責務を持ちます：

- ExecutionEngine: ブローカー API とのやり取り、注文管理、リスク管理
- Monitoring: システム状態・注文状態・リスクの定期チェック、アラート発行（LINE）
- Portfolio: 銘柄選定・重み計算・株数決定（純粋関数）
- Research: DuckDB を使ったファクター計算・ファクター評価ユーティリティ
- AI: ニュースの NLP スコアリング、マクロニュースからの市場レジーム判定
- Tools: 検証レポート出力などのユーティリティスクリプト

本リポジトリはライブラリとしても利用でき、個別モジュール（例: kabusys.research.calc_momentum、kabusys.ai.score_news など）を呼び出して使えます。

---

## 主な機能

- 実行（Execution）:
  - 実取引 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - 発注状態管理、OrderManager、Reconciler による再同期
  - RiskManager による複数のリスクチェック（ポジション上限・ドローダウン等）

- 監視（Monitoring）:
  - SystemMonitor: CPU / メモリ / ディスク / 実行プロセス生存チェック / データ鮮度
  - TradeMonitor: 滞留注文、約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限のモニタリングとリスクログ
  - KillSwitch: データ/フラグに基づく ExecutionEngine 停止トリガ
  - AlertManager: LINE Messaging API を用いた通知（クールダウン管理）
  - Streamlit ダッシュボードで可視化（監視 DB を参照）

- ポートフォリオ構築:
  - 候補選定、等金額／スコア加重、リスクベース配分、セクター制限、レジーム乗数
  - 単元株（lot）丸め、集約上限スケールダウンロジック

- リサーチ:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI:
  - ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に保存
  - マクロニュース + MA200 乖離から日次レジーム判定

- ツール:
  - Paper Trading の検証レポート生成スクリプト（期間指定可能）

---

## 前提・依存関係

- Python 3.9+
- 外部パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai (OpenAI Python SDK)
  - streamlit (ダッシュボード起動時)
  - その他（必要に応じてプロジェクトで要求されるパッケージ）

サンプル（requirements.txt）:
pip install duckdb psutil requests openai streamlit

※ 実行に必要な追加パッケージやバージョンはプロジェクトの要件に応じて調整してください。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading: ブローカーはモックを使用し、SQLite は data/paper_trading.db（分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須プロパティとして扱われる箇所あり）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- OPENAI_API_KEY: OpenAI API キー（AI 関連機能で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）。デフォルト 60。
- PAPER_FILL_MODE: Paper Trading のマッチング挙動（instant|partial|never|reject）。デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: paper_trading 時の SQLite DB パス（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視関連のパスと挙動
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化（テスト用途）

.env ファイルはプロジェクトルートの .env / .env.local に置かれ、OS 環境変数と併せて読み込まれます（auto-load 無効化可能）。.env のパースは shell 風の export KEY=VAL / quotes / コメントに対応。

例（.env）:
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows

3. 依存パッケージをインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は上の推奨パッケージを個別インストール）

4. data ディレクトリを作成
   mkdir -p data

5. 環境変数を設定（.env を作成）
   - プロジェクトルートに .env（または .env.local）を作成し必要なキーを設定
   - OPENAI_API_KEY / KABU_API_PASSWORD / JQUANTS_REFRESH_TOKEN 等を忘れずに設定

6. 初回実行で必要な DB テーブルはコード側で自動作成・マイグレーションされます（例: init_monitoring_db）。

---

## 使い方（実行方法・コマンド例）

基本的にモジュールは python -m で起動できます。

- Monitoring を起動（ポーリング監視）
  python -m kabusys.run_monitoring
  オプション:
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）上書き（デフォルト 60 秒）
   - run_monitoring は常に本番用の sqlite_path を使用（KABUSYS_ENV にかかわらず）

- Execution（発注エンジン）を起動
  python -m kabusys.run_execution
  特記事項:
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db を使用（本番 DB と完全分離）
   - 起動時に data/stop_requested.flag が存在すると起動せず終了
   - 実行中に data/stop_requested.flag が作成されるとエンジンは停止します
   - 実行中の PID ファイルは data/execution.pid（デフォルト）に保存

- Streamlit ダッシュボード（監視 DB を可視化）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  （--db で監視 DB のパスを指定可能）

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- ライブラリとしての利用（Python スクリプト内で呼び出し）
  - ポートフォリオ関数:
      from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - リサーチ / ファクター:
      from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI スコアリング:
      from kabusys.ai import score_news
      # DuckDB 接続（duckdb.connect）を渡し、score_news(conn, target_date, api_key=...)
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime

---

## 運用上のフラグ / ファイル

- data/stop_requested.flag: 実行を外部から停止させたい場合に作成（run_monitoring・run_execution で参照）
- data/execution.pid: ExecutionEngine の PID（実行時に作成）
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に停止を促す）
- デフォルト DB:
  - 監視 DB: data/monitoring.db
  - DuckDB: data/kabusys.duckdb
  - Paper trading DB: data/paper_trading.db（paper_trading 環境時）

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 対応）
- utils/
  - process_priority.py — プロセス優先度設定 / CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite を使った監視ログ永続化層（テーブル作成・CRUD）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度のチェック
  - trade_monitor.py — 注文滞留 / 約定異常のチェック
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — kill.flag 管理（書き込み・判定）
  - alert_manager.py — LINE 通知実装
  - monitoring_engine.py — 監視モニタ群を束ねるエンジン
  - streamlit_dashboard.py — Streamlit 監視ダッシュボード
- execution/
  - order_manager.py — 発注の高レベル管理（OrderManager）
  - reconciler.py — 再起動時リコンシリエーション
  - （その他: broker_factory, execution_engine, order_repository などが存在）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクター制限・レジーム乗数
  - position_sizing.py — 株数決定・集約上限スケールダウン
- research/
  - factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- ai/
  - news_nlp.py — raw_news を LLM でスコアリングして ai_scores に保存
  - regime_detector.py — マクロニュース + MA200 乖離からレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力（CLI）

その他、プロジェクトルートに .env/.env.local、data/ ディレクトリ、必要に応じて requirements.txt を配置してください。

---

## 運用時の注意点

- 本コードは実取引を行う機能を含みうるため、本番運用前に paper_trading モードやモックブローカーで十分な検証を行ってください。
- OpenAI API 等の外部サービスは利用量に応じた制限や課金が発生します。API キーの管理を適切に行ってください。
- MONITOR_POLL_INTERVAL を 0 や負の値に設定すると無効（デフォルトにフォールバック）になります。
- paper_trading モードは本番 DB と分離する設計です（PAPER_TRADING_SQLITE_PATH を利用）。
- データ鮮度チェックは DuckDB の prices_daily を参照します。データ更新パイプラインが正しく動作していることを確認してください。

---

必要であれば README に実行例（ログ出力例）、より詳細な .env.example、requirements.txt の推奨内容、運用 Playbook（停止・起動手順）などを追加します。どの情報を追記しますか？
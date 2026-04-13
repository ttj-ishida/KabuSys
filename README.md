# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、注文発行・リスク制御・監視・研究（ファクター計算）・AI ベースのニュースセンチメント評価などを含む、自動売買の基盤コンポーネント群を提供します。実運用（live） / ペーパー取引（paper_trading） / 開発（development）を想定した設定と分離が組み込まれています。

---

## 機能一覧

- Execution（ExecutionEngine）
  - ブローカー抽象化（本番ブローカー / MockBroker を切替）
  - 注文作成・送信・状態同期（OrderManager / Reconciler）
  - リスク管理（RiskManager）
- Monitoring
  - システム稼働監視（CPU/メモリ/ディスク/プロセス PID）
  - 注文滞留・約定異常の検出
  - ドローダウン・ポジション上限の監視と kill flag（Execution 停止シグナル）
  - 監視データ永続化（SQLite）
  - Streamlit による監視ダッシュボード
- Portfolio construction
  - 候補選定、重み計算（等分配・スコア加重）
  - セクター分散適用、レジーム乗数
  - 株数計算（単元丸め、リスクベース／等分配）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン・IC 計算・統計サマリー
- AI（OpenAI）
  - ニュース記事のセンチメントスコア化（ai_scores に書き込み）
  - マクロニュースと ETF MA200 を合わせた市場レジーム判定
  - API 呼び出しはリトライ・フェイルセーフ実装
- ツール
  - Paper Trading 検証レポート生成（過去期間の稼働率 / 注文成功率 / レイテンシ等）
- ユーティリティ
  - 設定管理（.env 自動ロード、Settings クラス）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.10+（型注釈に Union | などを利用）
- SQLite（標準で付属）
- DuckDB（Python パッケージ）
- OpenAI API を利用する場合は API キー

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（例）
   pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

4. データディレクトリを作成
   mkdir -p data

5. 環境変数を設定
   - 簡単にはリポジトリルートに `.env` を置くと自動読み込みされます（デフォルト）。`.env.local` は上書き用。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API（必須な場合）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（本番時必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
   - KABUSYS_ENV: 起動モード（development | paper_trading | live） — デフォルト `development`
   - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト `data/paper_trading.db`）
   - SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
   - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag ファイルパス
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で上書き可能）

   例 `.env`（最低限、本番で live を使う場合は十分に設定してください）:
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   KABUSYS_ENV=development
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（主要スクリプト）

- Execution Engine を起動（発注系）
  - 開発 / ペーパー / 本番は KABUSYS_ENV に依存
  - paper_trading の場合は MockBroker を使い、Paper DB（PAPER_TRADING_SQLITE_PATH）に記録します

  実行:
  python -m kabusys.run_execution

  動作:
  - プロセス優先度を "high" に設定（psutil を利用）
  - SQLite/DuckDB に接続
  - BrokerClientFactory により本番/Mock を選択
  - ExecutionEngine.run_session() を実行

- Monitoring（ポーリング監視）を起動
  - 環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書き（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を使用（KABUSYS_ENV に関わらず）

  実行:
  python -m kabusys.run_monitoring

  動作:
  - SystemMonitor / TradeMonitor / RiskMonitor 等のチェックを定期実行
  - kill.flag の作成や LINE 通知（AlertManager）を行う

- Streamlit ダッシュボード（監視画面）
  実行例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  実行:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  --db PATH で SQLite ファイルを指定（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）

- AI 関連（プログラムから呼び出す例）
  - ニュースセンチメントをスコア化して ai_scores テーブルに書き込む:
    from datetime import date
    import duckdb
    from kabusys.ai import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, target_date=date(2026,4,1), api_key='YOUR_OPENAI_KEY')

  - 市場レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,1), api_key='YOUR_OPENAI_KEY')

  注意: OpenAI 呼び出しはコストが発生します。API キーは厳重に管理してください。

---

## 主要設定と挙動のポイント

- KABUSYS_ENV
  - development: 開発用
  - paper_trading: MockBroker を使用しデータを paper_trading 用 DB に分離
  - live: 本番ブローカーを使用（実際の発注を行うため注意）

- DB
  - 監視ログ: SQLITE_PATH（デフォルト data/monitoring.db）
  - DuckDB: DUCKDB_PATH（解析・ファクター計算用）
  - paper_trading の場合は PAPER_TRADING_SQLITE_PATH を別で使用

- モニタリング
  - MONITOR_POLL_INTERVAL 環境変数で監視ループ間隔を変更可能
  - kill.flag を作成すると ExecutionEngine を停止させるための外部シグナルとなる
  - Settings.kill_flag_clear_on_start が "1" の場合、起動時に kill.flag を自動削除

- プロセス優先度
  - run_execution/run_monitoring は起動時に set_process_priority("high") を実行
  - 権限や OS により設定できない場合は警告を出してスキップ

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数/.env の読み込みと Settings クラス
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- execution/
  - order_manager.py — 注文の作成・送信ロジック
  - reconciler.py — 起動時の自動リコンシリエーション
  - order_repository.py, order_record.py, broker_api.py ...（ブローカー & DB 抽象）
- monitoring/
  - monitoring_db.py — SQLite への永続化層
  - system_monitor.py — システム稼働・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各モニターの統括
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み
  - position_sizing.py — 株数決定
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 等の計算
  - feature_exploration.py — 将来リターン・IC・統計解析
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py — マクロ + ETF MA200 によるレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポートスクリプト
- utils/
  - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下を参照してください。）

---

## 注意事項 / 運用上のヒント

- live モードでは実際にブローカーへ発注が行われます。API キー / パスワードの管理、動作確認は十分に行ってください。
- Paper Trading モードは本番 DB と分離されますが、設定ミスで本番 DB に接続しないよう環境変数を確認してください。
- OpenAI を使う機能は API コストが発生します。バッチサイズやトークン量に注意してください。
- kill.flag による停止は意図的な停止手段です。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に古いフラグを自動でクリアします。
- DuckDB / prices_daily 等の入力データが新鮮でないとファクター計算やレジーム判定に影響します。SystemMonitor はデータ鮮度をチェックします。

---

もし README に追加したい運用手順（デプロイ方法、systemd ユニット例、Docker 化、CI ワークフロー等）があれば教えてください。必要に応じてサンプルを追記します。
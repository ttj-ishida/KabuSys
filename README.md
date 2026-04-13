# KabuSys

KabuSys は日本株の自動売買システム（研究・検証・本番運用を想定）を構成する Python モジュール群です。本リポジトリは取引ロジックやポートフォリオ構築、監視・アラート、Paper Trading 用のツール、LLM を使ったニュースセンチメント等を包含します。

この README ではプロジェクト概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成をまとめます。

---

## プロジェクト概要

- 日本株自動売買のコア機能（シグナル → 発注 → リコンシリエーション）と、ポートフォリオ構築・リスク調整・ポジションサイズ計算を提供します。
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送信（LINE）機能を備え、ExecutionEngine と並行してシステム健全性を監視します。
- Paper Trading 用の分離された SQLite DB を使った検証フローをサポートします（KABUSYS_ENV による切替）。
- DuckDB を用いた時系列・財務データ処理、研究用途のファクター計算・特徴量解析、LLM（OpenAI）を使ったニュースNLP・市場レジーム判定も含まれます。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカー抽象化（BrokerClientFactory / Broker API プロトコル）
  - OrderManager / OrderRepository / Reconciler（再起動時の同期）
  - RiskManager（発注制限・回路遮断など）

- Portfolio（純粋関数）
  - 候補選定（select_candidates）
  - 重み計算（等金額、スコア加重）
  - セクター上限、レジーム乗数の適用
  - ポジションサイズ計算（lot 単位丸め・aggregate cap）

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor（DB へログ記録・アラート送出）
  - MonitoringEngine（各モニタを束ねるポーリングループ）
  - MonitoringDB（SQLite での永続化スキーマ & API）
  - LINE を使った AlertManager
  - Streamlit ダッシュボード（簡易 UI）

- Tools
  - Paper Trading 検証レポート生成ツール（paper_verification_report）
  - Streamlit ベース監視ダッシュボード

- Research / AI
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC 計算・統計サマリー
  - ニュース NLP（OpenAI）を使った銘柄別センチメントスコアリング
  - 市場レジーム判定（ETF MA + マクロニュース + LLM）

---

## セットアップ手順（ローカル開発環境）

以下は推奨手順です。

1. Python（3.10+ 推奨）をインストール
2. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil requests openai streamlit
   - 追加で開発用に pytest 等を導入しても良いです。

注意: requirements.txt はリポジトリに含まれていない想定のため、上記パッケージを手動でインストールしてください。

---

## 必要な環境変数（代表例）

Settings クラスは .env / .env.local / OS 環境変数を読み込みます（自動ロード）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

代表的な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
  - paper_trading 時は MockBroker + 別 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill flag（デフォルト: data/kill.flag）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用

環境変数の自動読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を読み込みます（OS 環境変数を保護）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 使い方（主要コマンド / スクリプト）

プロジェクトをパッケージとして使うため、モジュールとして起動できます（プロジェクトルートから実行）。

1. 監視ループを起動
   - MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト 60 秒）
   - 起動例:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 特記事項:
     - run_monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用して監視データを書きます。
     - 起動時にプロセス優先度を High に設定しようとします（psutil の権限に依存）。

2. ExecutionEngine（発注エンジン）を起動
   - KABUSYS_ENV により本番/紙トレード切替:
     - 本番: KABUSYS_ENV=live
     - ペーパートレード: KABUSYS_ENV=paper_trading
       - paper_trading 時は MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にデータを書きます。
   - 起動例:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

3. Paper Trading 検証レポート生成ツール
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --from YYYY-MM-DD、--to YYYY-MM-DD、--db PATH（PAPER_TRADING_SQLITE_PATH より優先）

4. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは読み取り専用で DB を開こうとします。監視（MonitoringEngine）が先に動いていないとデータがありません。

5. AI / 研究用関数の利用例（Python スクリプト内）
   - DuckDB 接続を渡して利用:
     - import duckdb
     - conn = duckdb.connect('data/kabusys.duckdb')
     - from kabusys.research import calc_momentum
     - res = calc_momentum(conn, date(2026, 4, 1))
   - ニュース NLP（OpenAI API）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date=date(2026,4,1), api_key="YOUR_KEY")
   - 市場レジーム:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date=date(2026,4,1), api_key="YOUR_KEY")

---

## 監視・安全機構（概要）

- SystemMonitor
  - CPU / メモリ / ディスク / 実行プロセスの存在確認 / データ鮮度をチェック
  - PID ファイルを監視し、stale PID を検出すると PID ファイルを削除してリスクログに記録

- TradeMonitor
  - 滞留注文（stale orders）を検出してログ・リスク記録
  - 約定価格の異常（設定比率を超える）を検出してログ

- RiskMonitor
  - ダウンドローダウン（ハイウォーター・マーク）とポジション上限をチェック
  - 必要に応じて kill.flag を作成（KillSwitch）して ExecutionEngine に停止シグナルを送る

- AlertManager
  - LINE プッシュ通知を行う（channel token / user id が設定されている場合）
  - 同一カテゴリ/レベルのクールダウンをメモリ内で管理

---

## 設定・チューニング（代表的なキー）

- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant / partial / never / reject）
- CPU / MEMORY / DISK 閾値 — Settings.cpu_threshold_pct 等（監視閾値）
- kill.flag のパス / PID ファイルのパス — Settings.kill_flag_path / pid_file_path

---

## 開発者向けノート

- Settings モジュールは .env のパースを自前で行います。クォート・コメント処理等に対応しています。
- .env の読み込み優先順位:
  - OS 環境 > .env.local > .env
- 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行うため、実行ディレクトリに依存しません。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- DuckDB と SQLite を併用しています:
  - DuckDB: 大量の時系列／分析データ（prices_daily、raw_financials 等）
  - SQLite: 監視ログ（monitoring.db）・（paper trading 用の別 DB）等

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / Settings
  - run_monitoring.py                  — SystemMonitor ポーリング起動
  - run_execution.py                   — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py     — Paper Trading 検証レポート
  - portfolio/
    - __init__.py
    - portfolio_builder.py             — 候補選定 / 重み計算
    - risk_adjustment.py               — セクター制限 / レジーム乗数
    - position_sizing.py               — 株数計算 / aggregate cap
  - monitoring/
    - __init__.py
    - monitoring_db.py                 — SQLite スキーマと DB API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (他: broker_factory, execution_engine, order_repository 等—発注/再調整関連)
  - research/
    - __init__.py
    - factor_research.py                — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py            — 将来リターン / IC / 統計
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py                — 市場レジーム判定（LLM + ETF MA）
  - data/
    - （DuckDB / SQLite の default path は data/ 下に想定）

---

## 注意事項 / 運用上のポイント

- paper_trading モードは本番 DB と完全分離する設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API を利用する機能はキーの設定が必須です。API の呼出しはリトライ・フェイルセーフを備えていますが、コスト/レート制限に留意してください。
- process priority / cpu affinity の設定は OS と権限に依存します（psutil の AccessDenied 等をハンドリングして警告）。
- Monitoring は本番稼働中の ExecutionEngine を停止させるための kill.flag を書き込むことがあります。運用前に kill.flag の位置 /クリアの挙動を確認してください（Settings.kill_flag_clear_on_start が有効な場合、起動時に自動でクリアされます）。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存 DB のカラム追加（冪等）を行うため、バージョン互換に配慮しています。

---

これで README の基本説明は以上です。必要であれば、導入例（サンプル .env）、より詳細な運用手順、CI・テスト指針や API シグネチャのドキュメントを追加で作成できます。どの情報を優先して追加しましょうか？
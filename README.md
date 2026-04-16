# KabuSys

KabuSys は日本株の自動売買システム向けのコンポーネント群です。  
実運用用の ExecutionEngine（発注・リスク管理・リコンシリエーション）、監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）とそれらを補助する研究・ポートフォリオ・AI（ニュース NLP / レジーム判定）モジュール、ならびに運用支援ツールを含みます。

主な設計方針：
- 本番・ペーパー（paper_trading）を環境変数で切替可能（DBは分離）。
- DuckDB をデータ分析用（prices_daily 等）、SQLite を監視・注文ログに使用。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント、レジーム判定（API キー必須）。
- フェイルセーフ設計（API失敗時のフォールバック、部分書き込みの保護、冪等性確保）。

---

## 機能一覧

- Execution
  - ExecutionEngine：ブローカー経由での注文管理 / RiskManager / OrderManager / Reconciler による自動復旧。
  - Paper trading モード：`KABUSYS_ENV=paper_trading` の場合 MockBroker を使用し、data/paper_trading.db に書き込む（本番 DB と分離）。

- Monitoring
  - SystemMonitor：CPU・メモリ・ディスク・プロセス状態・データ鮮度の監視と記録。
  - TradeMonitor：滞留注文（stale orders）や約定価格の異常検出。
  - RiskMonitor：ドローダウン・ポジション上限の監視とリスクイベント記録。
  - KillSwitch：条件に応じて `data/kill.flag` を書き、ExecutionEngine 停止をトリガー。
  - AlertManager：LINE Messaging API を用いたプッシュ通知（トークン未設定時はログ出力のみ）。
  - Monitoring DB：SQLite に監視ログとダッシュボード情報を永続化（マイグレーション対応）。

- Tools / UI
  - streamlit ベースの監視ダッシュボード（read-only で monitoring.db を表示）。
  - paper_verification_report：Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）。

- Research / Portfolio
  - Factor 計算（Momentum / Volatility / Value）・特徴量解析（IC 計算・統計サマリー）。
  - ポートフォリオ構築：候補選定・等重/スコア重み・ポジションサイズ計算（単元株丸め等）。
  - リスク調整：セクター上限・レジーム乗数。

- AI
  - news_nlp.score_news：ニュース記事を集約して OpenAI に渡し、銘柄毎の ai_score を ai_scores テーブルへ書込む。
  - regime_detector.score_regime：ETF（1321）MA200 とマクロニュースの LLM 判定を組合せてレジーム判定・保存。

---

## セットアップ手順

前提
- Python 3.10+（ソース注釈で typing | 機能を多用）
- OS: Linux / macOS / Windows（プロセス優先度設定はプラットフォーム依存の挙動あり）

1. リポジトリをクローン（本例は省略）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai requests streamlit

   （実運用では versions を固定した requirements.txt を用意してください）

4. 環境変数を設定（.env または環境へ直接）
   - .env / .env.local がプロジェクトルートにあれば自動読み込みします（既存 OS 環境変数は上書きされません）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   代表的な環境変数（省略値はコード内のデフォルト）：
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能利用時に必須)
   - KABUSYS_ENV = development | paper_trading | live  (デフォルト: development)
   - PAPER_FILL_MODE = instant | partial | never | reject  (default: instant)
   - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
   - SQLITE_PATH (monitoring 用, default: data/monitoring.db)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID （AlertManager 用）
   - LOG_LEVEL（DEBUG/INFO/...）

5. データディレクトリ作成
   - mkdir -p data

6. （任意）DuckDB に prices_daily / raw_financials / raw_news 等のテーブルを投入しておく

---

## 使い方（主要実行コマンド）

※ 下記はプロジェクトルートで実行することを想定します。

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - デフォルトポーリング間隔: 60 秒
  - 環境変数で上書き: MONITOR_POLL_INTERVAL=30
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します
  - 重要: Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（本番パス）を使って監視テーブルを初期化します

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、DB は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録され、本番 DB と完全分離されます
  - 停止: data/stop_requested.flag を作成すると実行中のエンジンに停止シグナルを送ります
  - PID ファイル: data/execution.pid に PID を書きます

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開きます（DB が存在しない / 開けない場合はエラーメッセージ）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH の代替）
  - 出力: 稼働率・注文成功率・P95 レイテンシ等のサマリと PASS/FAIL 判定

- AI 周り（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None) — OpenAI API キーが必要（引数 or 環境変数 OPENAI_API_KEY）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- その他
  - モジュール単体のテストや MonitoringEngine の単発実行は MonitoringEngine.run_once() を使えます（ユニットテスト用）。

---

## 重要な挙動・運用メモ

- MONITOR_POLL_INTERVAL：run_monitoring のポーリング間隔を秒で指定（デフォルト 60）。1 未満や不正値はデフォルトにフォールバックします。
- stop フラグ / kill フラグ
  - 停止要求（stop_requested.flag）を作ると run_monitoring / run_execution が検知して安全に終了します。
  - KillSwitch は条件を満たすと data/kill.flag を書き、ExecutionEngine を停止対象にします（手動クリア可能）。
- DB のマイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存テーブルにカラムがない場合は ALTER で追記する処理があります（例: latency_ms, peak_value の追加）。
- Process/prioritization
  - 起動スクリプトは最初に set_process_priority("high") を呼びますが、権限不足等で失敗する場合はログに出力してスキップします。
- フェイルオープン設計
  - AI 呼び出しや外部 API エラー時は基本的に例外を上位に投げずフォールバック（例: macro_sentiment = 0.0）して処理を継続する方針です（重要な DB 書き込みはトランザクションで管理）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / Settings 管理（.env 自動ロード機能を含む）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

subpackages:
- monitoring/
  - monitoring_db.py — SQLite の監視テーブル定義＋MonitoringDB helper
  - system_monitor.py — システム状態・データ鮮度の監視
  - trade_monitor.py — 注文滞留・約定異常検知
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書込みユーティリティ
  - monitoring_engine.py — 各モニタを束ねてポーリングする実行ロジック
  - alert_manager.py — LINE Push 通知ユーティリティ
  - streamlit_dashboard.py — streamlit ダッシュボード
- execution/
  - order_manager.py — 発注の外向き API（OrderManager）
  - reconciler.py — 起動時の同期・リコンシリエーション
  - order_repository.py, order_record.py, broker_* など（発注関連）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・丸め・キャップ処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value の計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメント取得・ai_scores 書込
  - regime_detector.py — ETF MA200 + マクロニュースでレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
- data/ (運用時に作成・利用)
  - monitoring.db（default SQLITE_PATH）
  - paper_trading.db（paper trading 用）
  - kabusys.duckdb（default DUCKDB_PATH）
  - stop_requested.flag, kill.flag, execution.pid などのフラグ類

---

## .env 例（プロジェクトルートに配置）
以下は最小例（実際には機密値を含むので .env.local を使うなど運用上の注意を払ってください）：

KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxx...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

---

必要に応じて README を改善できます（例: requirements.txt の具体化、運用フロー図、詳しい CLI 引数、実行例ログ、ユースケース別の設定例など）。必要なら追加内容を教えてください。
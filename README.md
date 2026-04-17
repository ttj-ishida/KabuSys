# KabuSys

日本株向けの自動売買・監視ライブラリ群（実行エンジン、監視、ポートフォリオ組成、リサーチ、AI 補助機能など）。  
この README はコードベース（src/kabusys 以下）に基づく概要、セットアップ、基本的な使い方、およびディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下機能を備えた自動売買システムのコンポーネント群です。

- ExecutionEngine（発注・注文管理・リスクリミット）
- Monitoring（システム状態・注文滞留・リスク監視・アラート）
- Portfolio construction（銘柄選定、重み付け、ポジションサイズ計算）
- Research（ファクター計算、特徴量探索）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定）
- ユーティリティ（プロセス優先度設定、.env ロード等）
- ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計方針の特徴：
- DuckDB / SQLite を使ったローカル DB ベース（ログ/履歴/市場データ）。
- Paper Trading と Live を分離（paper_trading 環境では専用 DB を使用）。
- OpenAI を用いた自然言語処理機能（ニュースセンチメント等）を持つ（API キーが必要）。
- モジュールはテストしやすく、外部副作用を最小化する設計（例: 日付参照を直接行わない等）。

---

## 主な機能一覧

- 監視（monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス存在、データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格の異常検出
  - RiskMonitor：ドローダウン・ポジション数上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて stop フラグを書き込み Execution を停止
  - AlertManager：LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- 実行（execution）
  - OrderManager / OrderRepository / Reconciler：注文作成、状態同期、再起動時のリコンシリエーション
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - BrokerFactory により本番/モックの切替（paper_trading 環境）
- ポートフォリオ（portfolio）
  - 候補選定（select_candidates）
  - 重み付け（等重・スコア重み）
  - セクター制約・レジーム乗数
  - ポジションサイズ計算（単元株丸め・利用可能現金のスケール）
- リサーチ（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC（情報係数）・統計サマリ
- AI（ai）
  - ニュース NLP（OpenAI）で銘柄ごとにセンチメントを算出し ai_scores に保存
  - レジーム判定（ETF ma200 とマクロニュースの LLM センチメント合成）
- ツール（tools）
  - paper_verification_report：Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

---

## セットアップ手順

前提：Python 3.9+（型注釈の使用を考慮）。プロジェクトルートに `src/` 配下のコードがある構成を想定します。

1. リポジトリをクローンし、プロジェクトルートに移動
   - (例) git clone ... && cd <project>

2. 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（主な依存）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （必要に応じて pytest 等）
   - 例:
     - pip install duckdb psutil requests openai streamlit

   > ※requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

4. 環境変数の設定
   - プロジェクトは .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須（Settings._require によるチェック）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨/任意:
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - SQLITE_PATH（monitoring DB のパス、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB のパス、デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager を使う場合）
   - 例 .env：
     - KABUSYS_ENV=paper_trading
     - OPENAI_API_KEY=sk-...
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要スクリプト／機能）

以下はプロジェクトに含まれる主要スクリプトと実行方法の例です。

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可。デフォルト 60 秒。
  - run_monitoring は常に本番用の sqlite_path を使って monitoring DB を開きます（KABUSYS_ENV にかかわらず）。

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録するため本番 DB と完全に分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。実行中も同フラグで停止検出します。

- Streamlit ダッシュボード（監視表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB に接続します（存在しない場合は起動エラーを表示）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が優先される）
  - デフォルト DB: data/paper_trading.db

- AI 機能（プログラムからの呼び出し例）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、target_date のニュース時間ウィンドウを対象に ai_scores を書き込みます。
    - api_key を与えない場合は環境変数 OPENAI_API_KEY を使用します（未設定時は ValueError）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム（bull/neutral/bear）を算出して market_regime テーブルに書き込みます。

- プロセス優先度の設定
  - run_monitoring / run_execution 起動時にプロセス優先度を "high" に設定する試みを行います（psutil 経由）。権限がないと警告でスキップされます。

- Kill/Stop フラグ
  - 実行の停止にはプロジェクト内のフラグファイルを使用します:
    - data/stop_requested.flag：run_monitoring / run_execution のループ停止フラグ
    - data/kill.flag：KillSwitch が書き込むフラグ（ExecutionEngine 停止要求）
  - KillSwitch はリスク条件（ドローダウンなど）で kill.flag を書き込みます。Execution 側は kill.flag の存在を検知して安全に停止します。

---

## 環境変数一覧（主要）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN
  - 必須（Settings が要求）
- KABU_API_PASSWORD
  - 必須（Settings が要求）
- OPENAI_API_KEY
  - OpenAI を使う機能で必要
- SQLITE_PATH
  - 監視 DB path（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH
  - paper_trading 用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH
  - DuckDB path（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL
  - 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / LOG_LEVEL 等
  - run_execution / monitoring の挙動を制御する追加パラメータ
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env 自動読み込みを無効化

---

## Monitoring DB（SQLite）スキーマ（要約）

init_monitoring_db により以下テーブルが作成されます（冪等）:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PRIMARY KEY), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id=1 固定行で集計保持（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

監視モジュールはこの DB を通じてログ・アラート・ダッシュボード集計を永続化します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／ディレクトリです（本リポジトリに含まれるファイル群に基づく抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理（.env 自動ロード機能含む）
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — monitoring DB の初期化・永続層
    - system_monitor.py      — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py       — 注文滞留／約定異常検出
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — LINE Push 通知
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py    — （エンジン本体はこのディレクトリに存在）
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_*                 — その他発注関連モジュール
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — 実行時に使用する DB / flag / pid ファイル等を置く想定

---

## 開発者向けメモ・運用上の注意

- .env パーサはシェルの export 形式やクォート、インラインコメント等を柔軟に扱いますが、必須値未設定時は Settings がエラーを出します。`.env.example` を参考にしてください。
- Paper Trading モードでは本番 DB と完全分離するためリスクなく検証できます（PAPER_TRADING_SQLITE_PATH を確認）。
- OpenAI 呼び出しは失敗に対してフェイルセーフ（リトライや 0.0 フォールバック等）を入れていますが、API キーのレート制限・課金に注意してください。
- Process priority / CPU affinity の設定はプラットフォーム依存。権限がない場合は警告でスキップされます。
- Monitoring のチェック間隔を短くしすぎると過剰な DB 書き込みや API 呼び出しを発生させる可能性があります。デフォルト 60 秒を推奨。

---

この README はコードベースの主要点を抜粋してまとめたものです。実装の詳細や追加のユーティリティは各モジュールの docstring とソースコードをご参照ください。質問や補足して欲しい項目があればお知らせください。
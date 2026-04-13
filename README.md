# KabuSys

日本株自動売買システム（ライブラリ / 実行ツール群）

このリポジトリは、売買シグナルの実行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築、研究用ファクター計算、AI を用いたニュースセンチメント評価などを含むモジュール群を提供します。

---

## プロジェクト概要

- 発注（ExecutionEngine）と注文管理（OrderManager / OrderRepository）を備えた実運用向け自動売買基盤のプロトタイプ実装です。
- 監視（Monitoring）機能により、プロセス健全性・データ鮮度・注文滞留・リスク指標（ドローダウン・ポジション上限）を定期的にチェックし、ログ保存や LINE 通知 / kill flag による強制停止トリガーを提供します。
- DuckDB を用いた市場データ処理・ファクター計算、OpenAI（gpt-4o-mini）を使ったニュース NLP による銘柄センチメント評価、及びそれらを組み合わせた市場レジーム判定を含みます。
- Paper Trading モードを用意しており、本番 DB と分離して安全に検証できます。

---

## 主な機能一覧

- Execution
  - 注文の作成 / 送信 / 同期（Reconciler による再同期）
  - RiskManager による発注制限（最大ポジション比率・利用率など）
  - BrokerClientFactory による実ブローカー / モックの切替（KABUSYS_ENV=paper_trading 時はモック）
- Monitoring
  - SystemMonitor: CPU/Mem/Disk, プロセス PID チェック, データ鮮度チェック
  - TradeMonitor: 注文滞留（stale order）、約定価格異常検出
  - RiskMonitor: ドローダウン監視、ポジション上限監視、dashboard 集計の永続化
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル出力
  - AlertManager: LINE Push API による通知（クールダウン制御）
  - Streamlit ダッシュボード（Read-only 接続で監視 DB を可視化）
- Research / Portfolio
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - portfolio: 候補選定、等金額・スコア加重配分、リスク調整、株数決定（単元丸め・aggregate cap）
- AI
  - news_nlp: raw_news を集約して OpenAI に送信、銘柄別センチメントを ai_scores に保存
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

---

## セットアップ手順

必要環境（主な依存）
- Python 3.9+
- pip
- SQLite（Python 標準ライブラリで利用）
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit

1. レポジトリをクローン／チェックアウト
2. 仮想環境を作成して依存をインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
     - pip install duckdb psutil requests openai streamlit

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意してください。

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし OS 環境変数を上書きしない）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（動作に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必要箇所がある場合）
- KABU_API_PASSWORD — kabuステーション API パスワード

OpenAI を使う機能を使う場合
- OPENAI_API_KEY — news_nlp / regime_detector で使用

その他主な環境変数（デフォルトを併記）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading の場合、Execution は専用の paper DB（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
- PAPER_FILL_MODE — instant | partial | never | reject (デフォルト: instant)
- PID_FILE_PATH — data/execution.pid
- KILL_FLAG_PATH — data/kill.flag
- KILL_FLAG_CLEAR_ON_START — 1 で起動時に kill.flag を消す（デフォルト 0）
- LOG_LEVEL — INFO 等
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、既定 60; 1以上の整数で指定、0/負数は無効扱いでデフォルトにフォールバック）

例 .env
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
JQUANTS_REFRESH_TOKEN=your_token
PAPER_FILL_MODE=instant
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

---

## 使い方

基本的な実行例を示します。プロジェクトルートから実行してください。

- ExecutionEngine を起動（本番 or paper_trading を Settings.kabusys_env で切替）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、モックブローカーを使用して PAPER_TRADING_SQLITE_PATH に書き込みます。
    - 起動時にプロセス優先度を high に設定します。
    - DB は Settings に従って接続されます。

- Monitoring のポーリングループを起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）。
    - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用してログを保存します（環境に関係なく）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプションで `--db PATH` を指定して SQLite ファイルを上書き可能（env PAPER_TRADING_SQLITE_PATH も使用可）。

- Streamlit ダッシュボード（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

- AI 機能（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（conn）と target_date（date）を渡して ai_scores に書き込みます。
    - api_key を省略すると環境変数 OPENAI_API_KEY を参照します（未設定なら例外）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルに書き込む処理。

注意点
- Monitoring の init_monitoring_db は冪等的で、起動時に必要テーブルを作成・マイグレーションを試みます。
- ExecutionEngine は起動時に paper/live の挙動を切り替えます（DB 分離、MockBroker の使用）。
- kill.flag による強制停止は KillSwitch により作成され、ExecutionEngine 側でその存在を検出して停止する設計になっています（Execution 側の実装に依存）。

---

## ディレクトリ構成（主要ファイルと概要）

src/kabusys/
- __init__.py
  - パッケージ定義（__version__ 等）
- config.py
  - .env ロードロジックと Settings クラス（環境変数の管理とデフォルト）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて paper/live を切替）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

サブパッケージ / 主なファイル
- ai/
  - news_nlp.py — ニュースを集約して OpenAI に送信、ai_scores 書込み
  - regime_detector.py — マクロ+MA200 から市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化（テーブル作成・CRUD）
  - system_monitor.py — CPU/Mem/Disk、PID、データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常価格検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込み・管理
  - alert_manager.py — LINE Push 通知（クールダウン付き）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit による監視ダッシュボード
- execution/
  - reconciler.py — 起動時の注文・ポジション再同期
  - order_manager.py — 注文作成 / 送信の高レベル API（状態遷移）
  - order_repository.py — SQLite を使った注文永続化（ファイルあり）
  - order_record.py — 注文の純粋なロジック表現（状態列挙など）
  - execution_engine.py — 実行セッション管理（起動/ループ）
  - broker_factory.py / broker_api.py — ブローカー API 抽象と実装切替
  - risk_manager.py — 発注リスク管理ロジック
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定（単元丸め・aggregate cap）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計系ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading 用検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

データファイル（デフォルト）
- data/kabusys.duckdb — DuckDB（市場データ等）
- data/monitoring.db — 監視ログ（SQLite）
- data/paper_trading.db — Paper Trading 用注文ログ（SQLite、KABUSYS_ENV=paper_trading で使用）
- data/execution.pid — ExecutionEngine の PID を書くファイル（起動時に作成）
- data/kill.flag — KillSwitch が書き込む停止フラグ

---

## 運用上の留意点

- Paper Trading を使うことで本番 DB を汚さず検証できます（PAPER_TRADING_SQLITE_PATH を使用）。
- MONITOR_POLL_INTERVAL は秒単位で監視ループの間隔を変更できます。ただし 1 秒未満や 0 を設定すると無効扱いになりデフォルトにフォールバックします。
- OpenAI API 呼び出しはネットワークやレート制限で失敗することがあるため、モジュール内でリトライやフェイルセーフ（スコア 0.0 フォールバック等）を実装していますが、API キーの保護・料金管理は運用で注意してください。
- システム優先度（process priority）を high に設定しますが、権限がない場合は設定に失敗する可能性があります（警告のみで続行します）。

---

この README はコードベース（src/kabusys 以下）から主要な挙動を抜粋してまとめたものです。実際の導入・本番運用に当たっては、環境別の設定、ブローカー API の資格情報管理、監視ポリシーのチューニング、テストシナリオの整備を行ってください。質問や追記したい項目があれば教えてください。
# KabuSys

軽量な日本株自動売買システムのコアライブラリ群および運用ユーティリティ。マーケットデータ、ポートフォリオ構築、発注ロジック、監視・アラート、Paper Trading 検証、LLM を使ったニュースセンチメント / レジーム判定などを含みます。

---

## 概要

このリポジトリは、以下の主要機能を持つモジュール群で構成されています。

- 発注エンジン（ExecutionEngine）と Order 管理（OrderManager / Reconciler）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算（DuckDB を用いたファクター生成・解析）
- AI ベースのニュースセンチメントと市場レジーム判定（OpenAI API を使用）
- 監視（System / Trade / Risk Monitor）、アラート（LINE Push）、監視ダッシュボード（Streamlit）
- Paper Trading 用の分離された DB とモックブローカーサポート
- 運用用スクリプト：監視ループ起動、Execution 起動、Paper Trading 検証レポート生成等

設計方針の一部：
- DuckDB/SQLite をローカルデータ格納に利用（分析 / 監視用）
- 本番・PaperTrading を分離（Paper 環境は別 SQLite）
- 外部 API（ブローカー / OpenAI）はインターフェース経由で呼び出す設計
- ルックアヘッドバイアス回避（date.today()/datetime.today() 依存を避ける実装）

---

## 主な機能一覧

- Execution（発注）
  - BrokerClientFactory によるブローカークライアント生成（本番 / モック）
  - OrderManager: Order 作成、同期、状態遷移管理
  - Reconciler: 再起動時の自動リコンシリエーション（注文・ポジション同期）

- Portfolio（銘柄選定 / 重み付け / 発注株数）
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes（risk_based / equal / score）

- Research（DuckDB ベースファクター計算）
  - calc_momentum / calc_volatility / calc_value
  - feature_exploration（forward returns、IC、統計サマリー）

- AI（OpenAI を利用）
  - news_nlp.score_news: raw_news から銘柄ごとのセンチメントスコアを ai_scores テーブルに書き込み
  - regime_detector.score_regime: ETF（1321）MA 比率とマクロニュースの LLM センチメントを合成して market_regime を更新

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringDB（SQLite）に system_status / trade_logs / positions / risk_logs / dashboard を保持
  - KillSwitch: 指定条件で data/kill.flag を書き込み ExecutionEngine を安全に停止
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン付き）
  - Streamlit ダッシュボード（監視状況可視化）

- ツール
  - paper_verification_report: Paper Trading DB を元に運用指標（稼働率・注文成功率・レイテンシ等）を集計してレポート出力

---

## 必要条件 / インストール

推奨 Python バージョン: 3.10+

主な依存（例）:
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例:
```bash
python -m pip install duckdb psutil requests openai streamlit
# あるいは requirements.txt があれば:
# python -m pip install -r requirements.txt
```

※ 実際の運用ではブローカークライアントに依存するパッケージや追加の分析用ライブラリが必要になる場合があります。

---

## 環境変数 / 設定

このプロジェクトは .env / .env.local / OS 環境変数を用いて設定を行います。自動ロードはプロジェクトルート（.git または pyproject.toml を探索して決定）を基準に行われ、以下の優先度で読み込まれます:

OS 環境変数 > .env.local > .env

自動ロードを無効化するには:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な環境変数（代表）:
- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG | INFO | …）。デフォルト: INFO
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant | partial | never | reject）デフォルト: instant
- MONITOR_POLL_INTERVAL: 監視ループポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH 等: PID / kill.flag のパス（デフォルト data/ 以下）

Settings クラスは環境変数をラップしており、未設定の必須値は起動時に例外を発生させます。

.env のパースはシェル風の記法（export を含む行、クォート、インラインコメント）にある程度対応します。

---

## セットアップ手順（手順例）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   python -m pip install duckdb psutil requests openai streamlit
   ```

4. data ディレクトリ作成（実行・監視ファイルの置き場）
   ```bash
   mkdir -p data
   ```

5. .env を作成（.env.example を参考に必要な値を設定）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI 機能を使う場合: OPENAI_API_KEY を設定
   - KABUSYS_ENV を切り替えると動作モードが変わります（paper_trading 等）

6. DB と初期テーブルはスクリプト実行時に自動で作成されます（init_monitoring_db 呼び出し）。

---

## 使い方（起動・コマンド例）

- 監視ループ起動（SystemMonitor をポーリング）
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
  ```bash
  # パッケージモジュールとして実行
  python -m kabusys.run_monitoring
  # または直接スクリプトを実行
  python src/kabusys/run_monitoring.py
  ```
  - 停止: data/stop_requested.flag ファイルを作成するとループは安全に終了します。

- Execution (発注エンジン) 起動
  ```bash
  python -m kabusys.run_execution
  # または
  python src/kabusys/run_execution.py
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます（本番 DB と分離）。
  - 実行停止: data/stop_requested.flag を作成するとエンジン停止処理が行われます。
  - 実行時に data/execution.pid を生成します。PID ファイルの stale 判定は SystemMonitor により検出されます。

- Streamlit ダッシュボード（監視）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ローカルで監視 DB を読み取り専用で開き、ポートフォリオや注文ログ、最新システムステータスを表示します。

- Paper Trading 検証レポート（コマンドライン）
  ```bash
  # デフォルト DB path = data/paper_trading.db
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（Python API 呼び出し例）
  - ニュースセンチメントを計算して ai_scores テーブルに書き込む:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
  ```
  - レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")
  ```
  - 注意: OpenAI API キーは OPENAI_API_KEY 環境変数でも指定可能。API 呼び出し時はレート制限/エラーに対するリトライロジックがありますが、API キー未設定時は ValueError が発生します。

---

## 運用上のポイント / 実装の注意点

- 監視は常に本番用 sqlite_path を参照します（monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計）。
- Paper Trading は settings.is_paper を用いて paper_sqlite_path を使用し、本番 DB と分離します。
- プロセス優先度は起動時に set_process_priority("high") を呼び出します。権限不足やプラットフォーム非対応時は警告を出力してスキップします。
- KillSwitch は RiskMonitor の結果に基づいて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。kill.flag のクリアは ExecutionEngine 起動時に設定により行われます（Settings.kill_flag_clear_on_start）。
- .env の自動ロードはプロジェクトルートが見つからない場合はスキップされます（パッケージ配布後でも動作するよう設計）。

---

## ディレクトリ構成（主要ファイルの説明）

（src/kabusys 以下）

- __init__.py
  - パッケージメタ情報（__version__）と公開モジュール群

- config.py
  - Settings クラス：環境変数の読み取り・検証、.env 自動ロードロジック

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔制御。data/stop_requested.flag で終了。

- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は Paper DB / MockBroker を使用。

- execution/
  - order_manager.py, reconciler.py, order_repository.py 等 — 発注管理、Order レコード、再同期ロジック等

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクターキャップ、レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- ai/
  - news_nlp.py — ニュース集約・OpenAI による銘柄センチメント付与
  - regime_detector.py — ETF MA とマクロセンチメントの合成で market_regime を算出

- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化 API（MonitoringDB）
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - monitoring_engine.py — 各 Monitor をまとめる実行ループ
  - alert_manager.py — LINE Push 通知
  - kill_switch.py — kill.flag 管理
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ

- data/
  - 実行時に生成されることがあるファイル（monitoring.db, kabusys.duckdb, paper_trading.db, stop_requested.flag, kill.flag, execution.pid など）

---

## よくある運用フロー（例）

1. .env を整備して本番/テスト環境を決める（KABUSYS_ENV）。
2. DuckDB / SQLite のパスを設定（デフォルトは data/ 下）。
3. ExecutionEngine を起動（run_execution）。Paper 動作確認は KABUSYS_ENV=paper_trading。
4. 監視を別プロセスで起動（run_monitoring）：SystemMonitor / TradeMonitor / RiskMonitor が定期実行され、kill.flag 発行や LINE 通知を行う。
5. Streamlit でダッシュボードを起動して状態を確認。
6. Paper Trading の運用評価は paper_verification_report を定期的に実行して結果をチェック。

---

## テスト・開発のヒント

- 多くの関数は純粋関数（副作用なし）で設計されており、ユニットテストが書きやすい構造です（portfolio.*、research.* 等）。
- OpenAI 呼び出し部は内部でラップされており、単体テストでは _call_openai_api をモックして応答をシミュレートできます（news_nlp, regime_detector 内で注釈あり）。
- 設定読み込みの自動化は .env に依存するため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を制御すると良いです。

---

必要に応じて README に追記できます（例: 開発用セットアップ手順、CI/テスト実行方法、実運用の注意点やバックアップ方針など）。追加で詳述したい項目があれば指定してください。
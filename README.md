# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリと運用ユーティリティ群を含みます。  
主に注文エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）およびニュースNLP / レジーム判定などのコンポーネントを提供します。

> 注意: これはサンプル実装・研究用フレームワークです。実運用で使用する場合は十分なテスト・監査を行ってください。

---

## 目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 使い方（主要スクリプト / ツール）
- 環境変数（主な設定項目）
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は以下の機能を組み合わせた自動売買プラットフォームのプロトタイプです。

- 注文管理と ExecutionEngine による発注・リスク管理
- 監視（System / Trade / Risk）コンポーネントとアラート送信（LINE）
- Paper Trading モード（本番 DB と分離）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- DuckDB を用いた時系列データ・ファクター計算（Momentum / Volatility / Value 等）
- ニュースを LLM（OpenAI）でスコアリングして AI スコアを保存
- Market regime 判定（MA + マクロニュースセンチメントの組合せ）
- Streamlit ベースの監視ダッシュボード
- 検証用レポート（Paper Trading の成績・稼働性チェック）

---

## 機能一覧

- run_execution.py
  - ExecutionEngine 起動。KABUSYS_ENV により paper_trading モードで Mock ブローカーを使える。
  - Paper Trading は専用 SQLite DB（data/paper_trading.db）へ記録して本番 DB と分離。
- run_monitoring.py
  - SystemMonitor をポーリングする監視プロセス起動スクリプト。
  - MONITOR_POLL_INTERVAL によるポーリング間隔設定（デフォルト 60 秒）。
- monitoring.*
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager / KillSwitch 等。
  - SQLite（monitoring DB）へ監視ログを永続化。
- portfolio.*
  - 候補選定、重み付け（等金額 / スコア加重）、ポジションサイズ計算、セクター制限、レジーム乗数。
- research.*
  - DuckDB を用いたファクター計算（momentum, volatility, value）、将来リターン、IC 計算、統計要約。
- ai.news_nlp / ai.regime_detector
  - raw_news を LLM でセンチメント評価し ai_scores に格納。
  - マクロニュース + ETF MA200 を使ったレジーム判定（market_regime 登録）。
- tools.paper_verification_report
  - Paper Trading DB から稼働率 / 注文成功率 / レイテンシなどを集計してレポート出力。
- monitoring/streamlit_dashboard.py
  - Streamlit を用いた監視ダッシュボード（positions / orders / system / overview）。

---

## 必要条件

- Python 3.9+（型アノテーション・match 等は使っていませんが、duckdb / openai SDK 互換のため 3.9 以上推奨）
- SQLite（標準ライブラリ）
- 必要な Python パッケージ:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- その他: ネットワークアクセス（OpenAI / LINE API を使う場合）

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（本リポジトリに requirements.txt がある場合はそちらを使ってください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 必要な DB ディレクトリ作成:
   ```
   mkdir -p data
   ```
   実行スクリプトはデフォルトで `data/monitoring.db`, `data/paper_trading.db`, `data/kabusys.duckdb` 等を参照します。

5. 必要であれば DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）にデータを準備してください。research / ai モジュールはこれらのテーブルを参照します。

---

## 環境変数（主なもの）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 利用時）
- PAPER_FILL_MODE: paper_trading 時の約定モード ("instant" | "partial" | "never" | "reject")
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB データファイル（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE 通知）用
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（例: 30）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 に設定）

.settings モジュール (kabusys.config.Settings) が環境変数を読み込みます。`.env` のパースは bash 風のクォートや `export KEY=val` 形式もサポートします。

---

## 使い方（主要コマンド）

プロジェクトルート（src が存在する位置）から実行します。モジュールはパッケージとして動くように設計されています。

- 監視ループを起動（デフォルトポーリング 60s）
  - 環境変数で間隔を変更:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 停止: プロジェクトルート下 `data/stop_requested.flag` を作成するとループが検知して終了します（実行中プロセスの安全停止用）。

- ExecutionEngine 起動（本番 / paper_trading 切替）
  - Paper trading:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    paper_trading 時は MockBrokerClient を利用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録します。
  - Live / dev:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - 停止:
    - `data/stop_requested.flag` を作成するとエンジンは停止を検知して終了します。
    - KillSwitch (監視) が trigger すると `data/kill.flag` を書き込み、外部に停止シグナルを送ります。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション: `--db PATH` で SQLite DB を指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` が指定されていればそれが優先されます。

- Streamlit ダッシュボード（監視）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  `--` 以降はダッシュボードの引数です（`--db` で DB を指定）。

- ライブラリとしての利用
  - portfolio / research / ai 等はモジュール API を通じて利用可能です（例: kabusys.portfolio.calc_position_sizes, kabusys.research.calc_momentum, kabusys.ai.score_news など）。

---

## ディレクトリ構成（主要ファイル説明）

以下は本リポジトリの主要なモジュールとその役割（抜粋）です。

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__ 等）

- src/kabusys/config.py
  - 環境変数の自動読み込み・設定取得ラッパー（Settings クラス）
  - .env / .env.local のパースルールを含む

- src/kabusys/run_monitoring.py
  - SystemMonitor をポーリングして monitoring DB に書き込むメインスクリプト

- src/kabusys/run_execution.py
  - ExecutionEngine を組み立ててセッションを実行する起動スクリプト（paper_trading 分離対応）

- src/kabusys/monitoring/
  - monitoring_db.py : SQLite スキーマ初期化と DB 操作ラッパー（MonitoringDB）
  - system_monitor.py  : システム状態・データ鮮度チェック
  - trade_monitor.py   : 注文滞留・約定異常検出
  - risk_monitor.py    : ドローダウン / ポジション上限監視
  - kill_switch.py     : kill.flag 書き込みロジック
  - alert_manager.py   : LINE push を使ったアラート送信
  - monitoring_engine.py : 監視コンポーネントの統合（Polling）
  - streamlit_dashboard.py : Streamlit ダッシュボード

- src/kabusys/execution/
  - order_manager.py / reconciler.py / order_repository.py / execution_engine 等（注文管理・発注・リコンシリエーション）

- src/kabusys/portfolio/
  - portfolio_builder.py : 候補選定、重み付け
  - position_sizing.py   : 単元丸め・資金配分・リスク制限
  - risk_adjustment.py   : セクター上限、レジーム乗数

- src/kabusys/research/
  - factor_research.py : momentum/volatility/value 等のファクター計算（DuckDB SQL）
  - feature_exploration.py : 将来リターン、IC、統計サマリー等

- src/kabusys/ai/
  - news_nlp.py        : raw_news を OpenAI でスコアリングし ai_scores に保存
  - regime_detector.py : ETF MA + マクロニュースセンチメントで市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py : Paper Trading DB の稼働・注文指標を出力する CLI

- src/kabusys/utils/
  - process_priority.py : プロセス優先度・CPU affinity 設定ユーティリティ

- data/
  - データファイルを置く想定ディレクトリ（monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, stop_requested.flag, execution.pid など）

---

## よく使う運用フロー（例）

- 日次: 朝イチで DuckDB に株価データ（prices_daily）をロード → research.calc_* を使って因子計算 → シグナル生成 → run_execution を使って当日寄りで発注
- 監視: run_monitoring を常時稼働。異常検知時は LINE に通知し、必要なら KillSwitch により ExecutionEngine を停止。
- 検証: Paper Trading モードで戦略を検証し、tools.paper_verification_report で成績・稼働性を評価。

---

## 運用上の注意

- Paper Trading と本番 DB は分離されますが、設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / KABUSYS_ENV）。
- OpenAI / LINE など外部 API へのキーは厳重に管理してください。
- monitoring / execution はフラグファイル（data/stop_requested.flag, data/kill.flag）による制御を行います。運用時はこれらファイルの存在を適切に扱ってください。
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）は各モジュールが期待するスキーマを満たす必要があります。research / ai モジュールはルックアヘッドバイアス防止のため target_date 取り扱いに注意して実行してください。
- process priority / CPU affinity 設定はプラットフォームに依存し、一部操作は権限不足で失敗します（警告ログのみ）。

---

必要であれば README を拡張して、各モジュールの API サンプル、例外・ログの見方、CI / テスト実行方法、データスキーマ詳細（DuckDB テーブル定義）などを追加できます。どのセクションを深掘りしますか？
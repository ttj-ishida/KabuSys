# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」の一部実装です。  
バックテスト・リサーチ用の DuckDB、監視・発注ログ用の SQLite、LLM を使ったニュース解析などを含んだモジュール群で構成されています。

注意: .env や API キー等の機密情報は絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は以下のような機能を持つ自動売買基盤のコンポーネント群です。

- 発注エンジン（ExecutionEngine）と注文管理（OrderRepository / OrderManager）
- 監視システム（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- リサーチ／ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ニュース NLP（OpenAI を用いた銘柄別センチメント付与）
- Paper Trading モード（本番 DB と分離された専用 SQLite）
- 各種 CLI ツール（環境設定ウィザード、設定検証、Paper Trading 検証レポート）

設計上のポイント:
- DuckDB は分析用データベース（prices_daily / raw_financials 等）として使用
- 監視ログは SQLite（data/monitoring.db）に永続化
- Paper Trading（KABUSYS_ENV=paper_trading）時は MockBroker を使い data/paper_trading.db に記録
- LLM 呼び出しは環境変数 OPENAI_API_KEY または関数引数で指定

---

## 主な機能一覧

- 環境変数の自動読み込み（.env / .env.local）
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的生成
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV による paper_trading/live/development 切替
  - プロセス PID ファイル・停止フラグによる制御
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）
- Kill Switch（data/kill.flag）による強制停止制御
- AI モジュール
  - kabusys.ai.news_nlp.score_news: ニュースを LLM で銘柄別にスコア化して ai_scores に保存
  - kabusys.ai.regime_detector.score_regime: マクロ + ETF MA から市場レジームを判定
- Research モジュール（calc_momentum / calc_volatility / calc_value / calc_forward_returns 等）
- Portfolio モジュール（候補選定・重み・ポジションサイジング）
- ツール: paper_verification_report による Paper Trading のレポート出力

---

## セットアップ手順

前提
- Python 3.9+（コード内 typing 構文に合わせてお使いください）
- システムに以下のパッケージをインストールしてください（一例）

推奨インストール（pip）
```
pip install duckdb psutil openai
# 設定検証で YAML 検証を行いたい場合:
pip install pyyaml
```

1. リポジトリをクローンして作業ディレクトリを移動
2. 仮想環境の作成（任意）
3. 必要パッケージをインストール（上記参照）
4. .env の作成
   - 対話式で作る:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動でルートに `.env` を配置（.env.example を参考に設定）

必須環境変数（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（代表例）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 用）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）

注意: .env を作成したら設定検証を実行してください
```
python -m kabusys.validate_config
# 警告もエラー扱いにする:
python -m kabusys.validate_config --strict
```

ディレクトリとデータの初期化:
- data/ に以下ファイルが自動生成・使用されます:
  - data/kabusys.duckdb (DuckDB)
  - data/monitoring.db (監視用 SQLite)
  - data/paper_trading.db (Paper Trading 用 SQLite)
  - data/execution.pid (ExecutionEngine の PID)
  - data/kill.flag (Kill Switch 用フラグ)
- 必要に応じて data/ ディレクトリを作成してください（多くのコードは起動時にディレクトリを自動生成しますが、権限等に注意）

---

## 使い方（主なコマンド例）

1. 環境設定ウィザード
```
python -m kabusys.config_setup
```

2. 設定検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

3. 監視（Monitoring）起動
- デフォルトポーリング 60 秒。環境変数で変更できます。
```
# デフォルト
python -m kabusys.run_monitoring

# 例: 30 秒間隔にする
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- run_monitoring は常に Settings.sqlite_path（本番/共通の monitoring DB）を使用します。
- 停止は data/stop_requested.flag を作成するか Ctrl+C。

4. 発注エンジン（ExecutionEngine）起動
```
python -m kabusys.run_execution
```
- KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録して本番 DB と分離されます。
- 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
- 停止は data/stop_requested.flag を作成するかプロセスに SIGINT。

5. Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または環境変数で DB 指定:
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report
```

6. AI 機能（プログラム呼び出し）
- ニューススコアリング:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- 市場レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- ※ api_key が未指定の場合は環境変数 OPENAI_API_KEY を参照

停止・Kill Switch の運用:
- KillSwitch は RiskMonitor 等の結果に応じて data/kill.flag を書き込みます。ExecutionEngine はこのフラグで停止します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされます（本番では推奨しません）。

ログレベル
- LOG_LEVEL 環境変数で制御（DEBUG / INFO / WARNING / ERROR / CRITICAL）

プロセス優先度
- 起動スクリプトは set_process_priority("high") を呼びます（psutil を使用）。権限がない場合は警告を出してスキップします。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主なファイル・モジュールを示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - ai/
    - news_nlp.py             — ニュースの LLM による銘柄別スコアリング
    - regime_detector.py      — マクロ + ETF MA による市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite の監視テーブル初期化 / ラッパー
    - monitoring_engine.py    — Monitor 群のポーリング制御
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — 注文滞留 / 約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - alert_manager.py        — （アラート送信管理 — ※未掲載の実装に依存）
  - execution/                 — 発注関連コンポーネント（OrderRepository 等）
    - order_repository.py
    - order_manager.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/ (実行時に使われるデータディレクトリ)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db
    - execution.pid
    - kill.flag / stop_requested.flag

（実際のリポジトリにはさらに多くのファイルが含まれます。上は主要モジュールの抜粋です。）

---

## 実運用上の注意点

- KABUSYS_ENV=live のときは本番設定です。LINE 通知設定や Kill Switch の扱い等を慎重に確認してください。
- .env は機密情報を含むため絶対にコミットしないでください。
- Paper Trading 用 DB は本番 DB と分離されていますが、設定ミスに注意してください（PAPER_TRADING_SQLITE_PATH）。
- OpenAI など外部 API を使う機能は API コストやレート制限に注意して運用してください。API 失敗時はフェイルセーフで継続する実装ですが、結果の信頼性は運用次第です。
- DuckDB / SQLite のファイルは適切なバックアップや権限管理を行ってください。

---

## 追加情報 / 開発メモ

- monitoring_db.init_monitoring_db() はテーブル作成と簡易マイグレーションを行います（列追加等を含む）。
- research モジュールは DuckDB の prices_daily / raw_financials を参照します。データの投入は別スクリプト（data pipeline）を想定しています。
- AI 関連は OpenAI SDK を利用しています。テストでは API 呼び出し部分をモックする設計になっています（ユニットテストしやすい実装）。

---

この README はコードベースの主要点をまとめたものです。追加でドキュメント化したい箇所（例: ExecutionEngine の詳細な設定、OrderRepository のスキーマ、AlertManager の実装方針など）があれば指示ください。
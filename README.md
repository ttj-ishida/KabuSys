# KabuSys

日本株向けの自動売買・研究・監視フレームワーク（モジュール群）の README。

本ドキュメントはリポジトリ内の主要モジュールから抽出した使い方・セットアップ・構成情報をまとめたものです。

> 注: これはコードベースから生成した README です。実行には各種外部依存（DuckDB / OpenAI / LINE API 等）が必要になります。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関連する以下の機能群を持つモジュール群です。

- 取引の実行（ExecutionEngine、OrderManager、Broker クライアント）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine、LINE 通知）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算・リスク調整）
- リサーチ（ファクター計算、特徴量探索、将来リターン / IC 計算）
- AI 支援（ニュースセンチメントスコアリング、レジーム判定 via OpenAI）
- ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）
- ユーティリティ（設定読み込み、自動.env ロード、プロセス優先度設定 等）

設計上のポイント：
- DB（SQLite / DuckDB）を用いたロギング・集計を中心に実装
- Paper Trading（検証）と本番は DB を切り分け可能
- OpenAI を用いた自然言語処理機能は API キーで制御
- 自動で .env / .env.local を読み込む仕組みを持つ（無効化も可能）

---

## 主な機能一覧

- Execution
  - OrderManager / ExecutionEngine による注文生成・管理・再同期（Reconciler）
  - BrokerClientFactory による実運用 / モック（paper_trading）切り替え
  - リスク管理（RiskManager）や約定監視

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor：滞留注文や約定価格の異常検知
  - RiskMonitor：ドローダウンやポジション上限チェック、ダッシュボード更新
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）生成
  - AlertManager：LINE によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）

- Portfolio
  - 候補選定（select_candidates）
  - 等重・スコア重み（calc_equal_weights, calc_score_weights）
  - ポジションサイズ算出（calc_position_sizes）
  - セクター制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）

- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC 計算、統計サマリ機能

- AI
  - news_nlp.score_news：ニュース記事を集約して OpenAI でセンチメントを算出し ai_scores に格納
  - regime_detector.score_regime：ETF の MA とマクロニュースの LLM センチメントを合成してレジーム判定

- Tools
  - paper_verification_report：Paper Trading ログ（SQLite）から稼働率／成功率／レイテンシ等の検証レポートを生成

---

## 必要な依存（例）

以下はコードから参照されている主要パッケージです。環境に応じてバージョン指定してください。

- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- sqlite3（標準ライブラリ）
- その他（プロジェクトの setup/requirements に従ってください）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
# またはプロジェクトの requirements.txt / pyproject.toml に従う
```

---

## 環境変数（主要）

Settings クラスにより環境変数を参照します。自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要なキー（例）:
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH 等も Settings から参照

.env の書式はシンプルな KEY=VALUE を想定し、`.env.local` は `.env` 上書きとして読み込まれます。

---

## セットアップ手順（ローカル、簡易）

1. リポジトリをクローンし作業ディレクトリへ移動
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに `.env`（または `.env.local`）を作成して必須環境変数を設定
   - 例（最小）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     ```
5. data ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

注意:
- 高優先度設定（set_process_priority("high")）は OS 権限や psutil 実装により失敗することがあります（警告ログが出力される）。
- OpenAI / LINE の実行は API キー・トークンが必要です。

---

## 使い方（実行例）

以下はいくつかの主要なエントリポイントの実行方法です。プロジェクトがパッケージとしてインストール済みか、`PYTHONPATH` を通して `src` を参照できる状態で実行してください。

- 監視ループ（SystemMonitor 単体のポーリング）
  ```
  # MONITOR_POLL_INTERVAL 環境変数で間隔秒を上書き可能（デフォルト 60）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は `data/stop_requested.flag` の有無を監視して終了します（存在するとループを抜けます）。
  - Monitoring は環境にかかわらず本番の sqlite_path を使用する設計です（Settings.sqlite_path）。

- 実行エンジン（ExecutionEngine）
  ```
  # 本番相当
  KABUSYS_ENV=live python -m kabusys.run_execution

  # Paper Trading（MockBroker を使用、データは data/paper_trading.db）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - 実行時は `data/execution.pid` に PID を書き込みます。
  - `data/stop_requested.flag` が既にある場合は起動せず終了します。
  - Paper Trading は本番 DB と分離して `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用します。

- Streamlit ダッシュボード（監視データの可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only URI を使って SQLite を開きます。MonitoringEngine が生成した DB を参照します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  - レポートは稼働率・注文成功率・送信率・レイテンシ等を算出し PASS/FAIL を出します。

- AI 機能（ライブラリ関数として使用）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、OpenAI API キーが必要です（引数 or 環境変数 OPENAI_API_KEY）。

---

## 停止・フラグ管理

- ExecutionEngine の停止は kill.flag を生成する仕組み（KillSwitch）により外部から行えます。デフォルトのパスは Settings.kill_flag_path（デフォルト data/kill.flag）。
- run_monitoring は data/stop_requested.flag を検知すると監視ループを終了します。
- run_execution も同様に stop flag を検知して Engine を停止します。

管理コマンド例（停止フラグ作成）:
```
mkdir -p data
echo "manual stop" > data/stop_requested.flag
# または kill.flag を書くと ExecutionEngine 起動時に検出して起動しない等の動作をする箇所があります
```

---

## ディレクトリ構成（概要）

以下は主要パッケージ構造（src/kabusys 以下の重要ファイルを抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env ロード / Settings
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - order_repository.py (参照あり)
    - order_record.py (参照あり)
    - execution_engine.py (参照あり)
    - broker_factory.py / broker_api.py (参照あり)
    - risk_manager.py (参照あり)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/ (想定されるデータ・DB を格納するディレクトリ)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB ファイル)

（実際のファイル一覧はリポジトリを参照してください。）

---

## 注意点・トラブルシューティング

- .env の自動読み込み:
  - デフォルトでプロジェクトルート（.git or pyproject.toml のあるディレクトリ）から `.env` と `.env.local` を読み込みます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 権限関連:
  - set_process_priority("high") は OS 権限に依存します。権限不足時は警告がログに出ますがプロセスは継続します。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は必要なテーブルと列を冪等に作成・追加します（例: trade_logs.latency_ms、dashboard.peak_value の追加対応あり）。

- OpenAI API:
  - API 呼び出しは再試行ロジックを持ちますが、API キー未設定時は ValueError になります。キーは環境変数または関数引数で与えます。

- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、paper 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。本番 DB とは完全分離されます。

---

## 開発・テストのヒント

- 各 monitor / engine はコンストラクタ注入で依存性を与えられるため、単体テストでは SQLite の一時 DB やモック BrokerClient、OpenAI 呼び出しの差し替えを利用してテストできます。
- news_nlp._call_openai_api や regime_detector._call_openai_api はテストで patch して外部 API を呼ばないようにできます。

---

必要があれば README にサンプル .env.example、requirements.txt、実際の起動スクリプト例（systemd ユニットファイル等）を追加します。追加したい内容や重点を置きたい箇所があれば指示してください。
# KabuSys

日本株自動売買システムの一部を切り出した実装例リポジトリ。ポートフォリオ構築、ポジションサイジング、監視 (Monitoring)、Execution エンジン起動スクリプト、AI を用いたニューススコアリング・レジーム判定、研究用ファクター計算などのモジュール群を含みます。

- パッケージ名: kabusys
- バージョン: 0.1.0

以下はこのコードベースを利用するための README（日本語）です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・リサーチ基盤のコンポーネント群です。本リポジトリに含まれる主な要素は次の通りです。

- Execution 起動スクリプト（run_execution）: ブローカークライアントやオーダーマネージャを組み立てて ExecutionEngine を起動
- Monitoring 起動スクリプト（run_monitoring）: SystemMonitor 等のポーリング監視を行う
- 監視永続化レイヤ（monitoring_db / MonitoringDB）
- リスク監視（RiskMonitor）・Kill Switch（KillSwitch）
- ポートフォリオ構築 / ポジションサイズ計算（portfolio モジュール）
- 研究用ファクター計算（research モジュール、DuckDB を利用）
- AI モジュール（news_nlp / regime_detector）: OpenAI を使ったニュースセンチメント・レジーム判定
- ユーティリティ群: 設定読み込み（config）、.env ウィザード（config_setup）、設定検証 CLI（validate_config）、ログ設定、プロセス優先度設定 など
- ツール: Paper Trading の検証レポート生成スクリプト（tools）

設計方針として、実行環境（本番 / ペーパー）に応じて SQLite DB を分離し、DuckDB は分析用途に使用します。外部 API（kabuステーション・J-Quants・OpenAI 等）のキーは環境変数で管理します。

---

## 主な機能一覧

- Execution エンジン起動・停止（run_execution）
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、paper_trading 専用 DB（data/paper_trading.db）へ記録
  - PID ファイル・停止フラグ（stop_requested.flag）による制御
- 監視ループ（run_monitoring）
  - CPU / メモリ / ディスク / プロセス生存 / データ鮮度の定期チェック
  - モニタリング結果を SQLite に記録（monitoring.db、環境に関わらず本番 sqlite_path を使用）
  - MONITOR_POLL_INTERVAL によるポーリング間隔変更
- Kill Switch（kill_switch）
  - ドローダウンやポジション上限超過などの条件で data/kill.flag を書き込み、ExecutionEngine を停止させる
- Risk Monitor（risk_monitor）
  - ダッシュボードのハイウォーターマーク管理、ドローダウン検出、ポジション上限監視
- Portfolio 構築（portfolio）
  - シグナル選定、等金額 / スコア加重の重み計算、ポジションサイズ計算、セクターキャップ適用
- Research（research）
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）や IC 計算、前方リターン
- AI モジュール（ai）
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメントスコア付与（news_nlp）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- 設定ユーティリティ
  - `.env` 対話式作成（config_setup）
  - 起動前チェック（validate_config）

---

## 要件（依存関係）

- Python 3.10 以上（typing の | 演算子を利用）
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証に必要だが必須ではない）
- その他: SQLite は標準ライブラリで利用可能

推奨: 仮想環境（venv / conda）内で運用してください。

requirements.txt が無い場合は次のように最低限をインストールしてください（例）:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして Python 仮想環境を作成・有効化
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb psutil openai PyYAML

3. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話に従って J-Quants トークン、Kabu API パスワード、ログレベル等を設定します
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - 必要に応じて --strict を付けて警告もエラー扱いに

4. data/ と logs/ ディレクトリが自動作成されます（logging_setup がログディレクトリを作成します）。必要なら事前に作成してパーミッションを確認してください。

5. 環境変数のポイント
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - その他（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパー時の専用 SQLite（デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR など

注意: config モジュールは起動時にプロジェクトルート（.git 或いは pyproject.toml の存在）を探索し、.env / .env.local を自動で読み込む仕組みを持ちます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（代表的コマンド）

主要スクリプトはパッケージモジュールとして実行できます。

- .env の対話式作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- Execution エンジン起動:
  - python -m kabusys.run_execution
  - 動作:
    - Settings により KABUSYS_ENV が `paper_trading` のときは paper_trading 用 SQLite を使用
    - 起動前に data/stop_requested.flag が存在すると起動せず終了
    - 起動中は PID ファイル（data/execution.pid）作成・監視

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更（デフォルト 60 秒）
  - 監視は常に Settings.sqlite_path（本番の監視 DB）を利用します（環境に依らず）

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定可能、指定が無ければ環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使用

- 研究用関数（Python REPL / スクリプトから利用）
  - 例: DuckDB 接続を作成してファクター計算
    - from kabusys.research import calc_momentum
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - calc_momentum(conn, datetime.date(2026, 4, 1))

- AI モジュール使用例（OpenAI キー必須）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

---

## 停止・Kill スイッチ

- stop_requested.flag
  - run_monitoring と run_execution はプロセス停止用のフラグファイル data/stop_requested.flag を監視します。
  - このファイルを作成すると次のポーリングやループ内でプロセスが安全に停止します（手動停止用）。
- kill.flag
  - KillSwitch が危険条件（大きなドローダウンやポジション上限超過）を検知したときに data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の設定を参照して kill.flag の自動クリアを制御できます（本番では 0 推奨）。

---

## 環境変数（主要）

（抜粋。詳細は kabusys.config.Settings を参照）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI を使う場合)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- LOG_LEVEL — ログレベル
- LOG_DIR — ログ保存先ディレクトリ
- KILL_FLAG_PATH — KillSwitch の書き込み先（default: data/kill.flag）
- PID_FILE_PATH — Execution の PID ファイルパス

---

## 開発者向けノート

- .env の自動ロードはプロジェクトルートを .git もしくは pyproject.toml から検出して行います。配布パッケージ環境では自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB 接続を受け取る研究用関数は SQL を多用しており、prices_daily / raw_financials / raw_news 等のテーブルが存在することを前提としています。
- AI 関連の API 呼び出しはリトライやバリデーションを備えていますが、API キー・課金上限に注意してください。
- logging_setup は標準出力と日次ローテートファイルハンドラ（logs/<app_name>.log、30 日保持）を設定します。ログディレクトリ作成に失敗するとファイル出力は無効化され stdout のみになります。
- process_priority で psutil による優先度設定を行いますが、権限がないと設定に失敗し警告になります。

---

## ディレクトリ構成

（省略せず主要ファイルを列挙）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - config_setup.py          — .env 対話式ウィザード CLI
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み計算
      - position_sizing.py     — 発注株数計算
      - risk_adjustment.py     — セクターキャップ・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py     — ファクター計算 (momentum/volatility/value)
      - feature_exploration.py — IC / forward returns / summary
      - __init__.py
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング
      - regime_detector.py     — 市場レジーム判定
      - __init__.py
    - monitoring/
      - monitoring_db.py       — SQLite 永続化レイヤ
      - system_monitor.py      — CPU/メモリ/データ鮮度監視
      - trade_monitor.py       — (注文滞留など) ※実装コードベースに存在
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - kill_switch.py         — kill.flag 管理
      - monitoring_engine.py   — 各 Monitor の束ね実行
    - execution/
      - execution_engine.py    — ExecutionEngine（起動スクリプトより使用）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - monitoring/ (上記)
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート
      - __init__.py
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — 優先度 / CPU affinity 設定
      - __init__.py
    - data/                    — 実行時に作成される想定のディレクトリ（DB, pid, flag 等）
  - その他（パッケージ構成）

注意: 一部ファイル（例: trade_monitor.py）の実装は本 README に出てきた機能説明と合わせて利用してください。

---

## よくある運用メモ

- Paper Trading と Live は DB を分離して運用してください（PAPER_TRADING_SQLITE_PATH を利用）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしてください（自動クリアを無効化）。
- ロギングとログローテーションが重要です。運用時は LOG_DIR を十分なディスク容量がある場所に設定してください。
- OpenAI API を多用する処理（news_nlp, regime_detector）はレート制限・エラーに備えた実装ですが、API キーと課金設定を確認してください。

---

必要であれば、README にセットアップ手順の詳細（systemd / Supervisor 用のユニット例、Dockerfile、CI 設定例など）や個々のモジュールの API サンプル（関数シグネチャと例）を追加できます。どの情報を優先して追記しますか？
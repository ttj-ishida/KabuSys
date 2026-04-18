# KabuSys

日本株向け自動売買システムのライブラリ/スクリプト群です。バックテストや研究用のファクター計算、ポートフォリオ構築補助、Execution / Monitoring 周りの実運用スクリプト、OpenAI を利用したニュース NLP / レジーム判定などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能を持つモジュール群で構成されています。

- ExecutionEngine（発注実行）: ブローカークライアントを通じて発注を行うエンジンの起動スクリプト。
  - `run_execution.py` で起動。
  - `KABUSYS_ENV=paper_trading` のときはモックブローカーを使用し、ペーパートレード用 DB（`data/paper_trading.db` 等）へ記録します（本番 DB と分離）。
- Monitoring（監視）: システム状態、データ鮮度、注文・リスクの監視を行う。
  - `run_monitoring.py` でポーリングループを稼働。
  - 監視ログは SQLite（`monitoring.db`）へ永続化。
- 研究・算出系（research）: DuckDB を用いたファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティなど）。
- ポートフォリオ構築（portfolio）: 候補選定、重み計算、ポジションサイズ計算、セクター上限などの純粋関数。
- AI（ai）: OpenAI を活用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）。
- ユーティリティ（utils）: ロギング設定、プロセス優先度・CPU affinity 設定など。
- 管理用ツール:
  - `.env` 対話式ウィザード: `config_setup.py`
  - 設定検証 CLI: `validate_config.py`
  - Paper Trading 検証レポート: `tools/paper_verification_report.py`

設計方針の一部:
- 本番データへの誤発注を避けるため、環境（KABUSYS_ENV）による DB 分離やペーパートレード用の挙動が用意されています。
- ルックアヘッドバイアスを避けるため、時間参照の取り扱いに注意（多くのモジュールで明示的に target_date を受け取る設計）。
- フェイルセーフ: API 呼び出し失敗時は安全側にフォールバックして処理継続。

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine 起動 / 停止（PID / stop flag 管理）
  - リスク管理（position limit / drawdown）・注文管理
- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセス稼働検出
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - リスク・滞留注文検出・Kill Switch（kill.flag）発動
  - 監視ログ保存（SQLite）
- 研究（Research）
  - momentum / value / volatility ファクター計算（DuckDB 参照）
  - forward returns / IC / 統計サマリ
- ポートフォリオ（Portfolio）
  - 候補選定、等配分・スコア加重、ポジションサイズ（リスクベース）計算
  - セクター上限適用、レジーム乗数
- AI
  - ニュースセンチメント（OpenAI を利用して ai_scores へ保存）
  - レジーム判定（ETF + マクロニュース + LLM 合成）
- 管理ツール
  - .env ウィザード、設定検証、Paper Trading レポート出力

---

## セットアップ手順（ローカル開発）

前提:
- Python 3.9+（モジュールが typing や新しい構文を使用しているため推奨）
- ネットワーク接続（OpenAI API を使う場合）

1. リポジトリをクローン / 配置
   - ソースは `src/kabusys/` 配下に配置されています。

2. 仮想環境を作成・有効化（推奨）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストール
   - 最低限:
     - duckdb
     - psutil
   - AI 機能を使う場合:
     - openai
   - 設定ファイル検証をフルに行う場合:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がない場合は上記を手動でインストールしてください。）

4. .env の準備
   - 対話式ウィザードで初期 .env を生成:
     - python -m kabusys.config_setup
   - 生成後、内容を確認・編集して必要な値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を設定してください。
   - もしくは手動で `.env` を作成。作成例（最小）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password_here
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば出力に従って修正してください。
   - 警告も FAIL にしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ / ログディレクトリ等は自動作成されることがありますが、権限等に注意してください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
  - 説明: 実行モード。paper_trading はモックブローカーを使用。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用リフレッシュトークン

- KABU_API_PASSWORD (必須)
  - kabuステーション API パスワード

- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb

- SQLITE_PATH
  - デフォルト: data/monitoring.db
  - 注意: Monitoring は環境に関わらず本番 sqlite_path を使用する設計箇所があります（run_monitoring 参照）。

- PAPER_TRADING_SQLITE_PATH
  - Paper Trading 専用の SQLite パス（paper_trading 実行時に使用）

- PAPER_FILL_MODE
  - paper_trading 時のモックブローカ約定モード
  - 有効値: instant | partial | never | reject
  - デフォルト: instant

- LOG_LEVEL
  - DEBUG / INFO / WARNING / ERROR / CRITICAL

- OPENAI_API_KEY
  - OpenAI を使用する機能 (news_nlp, regime_detector) の API キー

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）。デフォルト 60。無効値はデフォルトにフォールバック。

- KILL_FLAG_CLEAR_ON_START
  - 起動時に kill.flag を自動クリアするか（1=クリア）。本番では注意（デフォルト 0 推奨）。

---

## 使い方（主要コマンド）

- .env の生成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 挙動:
    - プロセス優先度を "high" に設定し、PID ファイル (`data/execution.pid` 既定) を管理します。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 SQLite を使用。

  - 停止方法:
    - 実行中に `data/stop_requested.flag` を作成すると起動スレッドが検知して停止します。
    - Kill Switch は `data/kill.flag` を生成して ExecutionEngine の停止を指示します（Monitoring 内から発動する機能）。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
    - Monitoring は監視用 DB の初期化を行います（init_monitoring_db）。
    - stop flag: `data/stop_requested.flag` を置くことでループ停止。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH : SQLite ファイルパス（指定がなければ環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- 研究モジュールを直接呼ぶ（例）
  - Python REPL / スクリプト内で DuckDB 接続を渡して利用:
    - from kabusys.research import calc_momentum
    - result = calc_momentum(duckdb_conn, date(2026,4,1))

---

## 運用メモ / 注意点

- Monitoring と Execution の DB 分離:
  - run_execution は環境が paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。
  - run_monitoring は設定に関わらず sqlite_path（本番）を使う箇所があるため、環境変数での管理に注意してください。

- Kill Switch / stop flag:
  - kill.flag: Monitoring 側の KillSwitch が条件を満たすと作成し、ExecutionEngine に停止を促します（flag は Settings.kill_flag_path で指定）。
  - stop_requested.flag: run_execution / run_monitoring の外部停止用フラグ。ファイルが存在するとループを抜けます。

- ログ:
  - `kabusys.utils.logging_setup.setup_logging` によりコンソール出力と日次ローテートファイルが作られます（logs/ デフォルト）。

- OpenAI 利用:
  - news_nlp / regime_detector は OpenAI API を使用します。API キーが未設定の場合は ValueError を投げる関数があります（API キーは環境変数 OPENAI_API_KEY または関数引数で渡す）。

- DB マイグレーション:
  - init_monitoring_db は既存 DB に対して必要なカラム追加（例: peak_value, latency_ms）を行う軽量のマイグレーションを含みます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring ポーリングループ起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py              — ニュース NLP / OpenAI 経由のスコアリング
  - regime_detector.py       — レジーム判定（ETF + LLM）

- monitoring/
  - monitoring_db.py         — SQLite 監視ログ層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py

- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
  - ・・・（発注ロジック一式）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

- tools/
  - __init__.py
  - paper_verification_report.py

プロジェクトルート（src/ より上）
- .env, .env.local (プロジェクトルートに置く想定)
- data/                       — 各 SQLite / PID / flag 等を配置する既定ディレクトリ
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/                       — ログ出力先（デフォルト）

---

## よくある質問（QA）

- Q: 本番環境での注意点は？
  - A: KABUSYS_ENV=live を設定すると本番挙動になります（実際に発注）。LINE 通知などの設定を必ず確認し、KILL_FLAG_CLEAR_ON_START の設定は本番で 1 にしないでください。validate_config の警告を十分に確認してください。

- Q: MONITOR_POLL_INTERVAL を変更したい
  - A: 環境変数 MONITOR_POLL_INTERVAL に秒数を設定します（例: export MONITOR_POLL_INTERVAL=30）。1 未満や不正な値はデフォルト 60 秒にフォールバックします。

- Q: OpenAI を使いたくない
  - A: ai モジュールを呼ばなければ問題ありません。OpenAI はオプション依存です（インポートするコードパスを呼ぶと API キーが必要になります）。

---

README はここまでです。実行や運用で不明点があれば、どのコマンド／モジュールについて詳しく知りたいか教えてください。さらにサンプル .env、起動スクリプトの具体的なオプション、デバッグ手順なども提供できます。
# KabuSys

日本株自動売買システムのコアライブラリ・ツール群です。本リポジトリは取引実行、監視、ポートフォリオ構築、リサーチ、AI を用いたニュース解析などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- 戦略に基づく銘柄選定とポジションサイズ計算（Portfolio）
- 注文管理・発注エンジン（ExecutionEngine）
- システム稼働・注文状態・リスクの監視（Monitoring）
- DuckDB を用いたファクター計算やリサーチ（Research）
- OpenAI（GPT）を用いたニュースセンチメント評価・レジーム判定（AI）
- 運用支援のコマンドラインユーティリティ（.env ウィザード、設定検証、レポート生成）

設計の要点：
- 環境を .env / 環境変数で管理
- Paper Trading モードは本番 DB と分離（data/paper_trading.db）
- 監視は本番の monitoring DB を常に参照
- 外部 API キー（OpenAI 等）は環境変数から取得

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して注文フローを実行（run_execution.py）
  - Paper Trading（モックブローカー）対応（KABUSYS_ENV=paper_trading）
  - 発注履歴を SQLite に保存、DuckDB は分析用に使用
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視ループ（run_monitoring.py）
  - Kill Switch（閾値超過で data/kill.flag を作成し Execution を停止）
  - 監視ログ（system_status / trade_logs / risk_logs / dashboard / positions）を SQLite に永続化
- Portfolio
  - 候補選定 / 等金額・スコア重み / ポジションサイズ算出
  - セクター上限適用、レジーム乗数
- Research
  - DuckDB 上でファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン・IC 計算、統計サマリー
- AI
  - ニュース記事を OpenAI でセンチメント評価して ai_scores に保存
  - マクロニュース + ETF MA を用いた市場レジーム判定
- ユーティリティ
  - 対話式 .env ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要要件（例）

主要依存ライブラリ（使用する機能により追加の依存あり）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証を行う場合）
- その他（プロジェクトで使用する追加パッケージ）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ requirements.txt はリポジトリに含まれていないので実際の運用ではプロジェクトに合わせて固めてください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境作成・依存インストール（上記参照）
3. 環境変数設定（.env を作成）
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使うオプション（デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能使用時に必要
   - 自動読み込み:
     - プロジェクトルートの .env/.env.local は kabusys.config によって自動読み込みされます
     - 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。

5. 初回実行前に data ディレクトリなど必要なディレクトリを作成（多くは自動作成されますが許可周りで失敗する場合あり）:
   ```
   mkdir -p data logs
   ```

---

## 使い方（起動・停止・ユーティリティ）

- ExecutionEngine 起動（本番/ペーパー分離対応）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い paper_sqlite_path（デフォルト: data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を行いません。
  - 実行中は data/execution.pid ファイル (設定による) を書きます。

- Monitoring 起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）。
  - 監視は本番 sqlite_path（SQLITE_PATH）を使用してログを保持します。
  - run_monitoring は data/stop_requested.flag を検知するとループを終了します。

- 停止シグナル / Kill Switch
  - ExecutionEngine 停止命令（強制）: monitoring の KillSwitch が条件を満たすと data/kill.flag を作成します（ExecutionEngine は起動時に kill flag の自動クリア設定を参照できます）。
  - 手動で実行停止（run_execution/run_monitoring の即時終了）: data/stop_requested.flag を作成してください（これを検知して各プロセスは安全に終了します）。
  - KillFlag の自動クリア設定:
    - KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に存在する kill.flag を自動でクリアします（本番では 0 を推奨）。

- 設定検証（起動前推奨）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（SQLite を指定可能）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)
  - これらは OpenAI API キー (OPENAI_API_KEY) が必要です。

---

## 主要な環境変数（一覧）

必須:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)

重要・よく使う（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live (default: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL (default: INFO)
- OPENAI_API_KEY: OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: paper trading の約定モード（instant|partial|never|reject、default: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか (0/1、default: 0)
- LOG_DIR: ログファイル保存先（default: logs/）

自動 .env 読み込み:
- プロジェクトルートの .env, .env.local が自動で読み込まれます。ただし OS 環境変数は上書きされません。
- 自動読込を止める: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 停止 / フラグファイル

- data/stop_requested.flag
  - run_execution / run_monitoring が監視しているシンプルな停止フラグ。存在すると安全にループを抜けます。
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine に対する停止命令（重篤なリスク等）。
- data/execution.pid
  - 実行中の ExecutionEngine の PID を保存するファイル（設定による）。

---

## ロギング

- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution"など)
- 出力先: コンソール (stdout) と日次ローテートされたファイル logs/<app_name>.log（デフォルト）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定

---

## ディレクトリ構成

（src/kabusys 配下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード・Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
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
    - alert_manager.py (参照用)
  - execution/
    - execution_engine.py (参照)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/ (データベース・フラグファイル等を格納する想定のディレクトリ)
  - logs/ (ログ出力先、デフォルト)

---

## 開発者向けメモ

- Paper Trading と Live の DB は分離されています（paper_sqlite_path と sqlite_path）。
- monitoring 側は常に本番 sqlite_path を参照して監視ログを永続化する設計です。
- AI 関連では OpenAI の API 呼び出しに対してリトライ、レスポンス検証、部分書き込み（部分失敗時のデータ保護）などフェイルセーフ処理が組み込まれています。
- DuckDB 接続を渡して分析・ファクター計算を行う設計（prices_daily / raw_financials / raw_news 等のテーブルを前提）。

---

## よくある操作例

- .env を対話式で作る:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 監視プロセスを起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジンを起動（ペーパートレード）:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はプロジェクトの導入・運用の概要をまとめたものです。実運用ではセキュリティ（.env を Git 管理しない等）、監視・アラート運用、DB バックアップ、ログローテーション設定等を別途検討してください。必要であれば README に追記・細分化して展開します。
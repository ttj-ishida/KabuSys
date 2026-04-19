# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買システム「KabuSys」のコードベースです。本 README はローカル開発／テスト環境でのセットアップと主要な使い方、ディレクトリ構成などをまとめたものです。

重要: 実際に本番環境で発注を行う場合は、設定（特に KABUSYS_ENV / KABU_API_PASSWORD / JQUANTS_REFRESH_TOKEN / LINE_* 等）を慎重に確認してください。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール式の自動売買システムです（コードは Python で実装）。

- マーケットデータ集計・ファクター計算（DuckDB ベース）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- Execution Engine（ブローカー接続・注文管理） — KABUSYS_ENV により paper_trading（モック）/ live（実発注）を切替
- 監視（System / Trade / Risk）と Kill Switch（閾値超過時に Execution を停止）
- AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定：OpenAI API を利用）
- Paper Trading 検証レポート生成ツール

設計方針の特徴：
- 設定は .env ファイルおよび環境変数で管理
- DuckDB／SQLite をデータ永続化に使用
- ログは標準出力と日次ローテーションファイル（logs/*.log）に出力
- 本番 DB と paper_trading 用 DB は分離される設計

---

## 主な機能一覧

- 設定ウィザード: kabusys.config_setup（.env の対話的生成・更新）
- 設定検証: kabusys.validate_config（.env と config/*.yaml のチェック）
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading → MockBrokerClient を使用し、data/paper_trading.db に履歴を記録
  - プロセス PID 書込 / 停止フラグ監視（data/stop_requested.flag, data/kill.flag）
- 監視ループ起動スクリプト: run_monitoring.py
  - SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を更新
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- Monitoring サブシステム:
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager（通知）
- 研究／分析:
  - research.factor_research（モメンタム・ボラティリティ・バリュー等の計算）
  - research.feature_exploration（将来リターン計算、IC 計算など）
- AI:
  - ai.news_nlp（ニュースのセンチメントを OpenAI で評価、ai_scores に書き込み）
  - ai.regime_detector（ETF の MA とマクロ記事で市場レジーム判定）
- ツール:
  - tools.paper_verification_report（Paper Trading の検証レポートを生成）

---

## 前提・依存関係

主な Python パッケージ（プロジェクトの requirements.txt があればそれを利用してください）:

- duckdb
- psutil
- openai
- PyYAML（config YAML 検証で任意）
- Python 3.9+（型注釈や構文から推定）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合は最低限:
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動。

2. 仮想環境を作成し依存をインストール（上記参照）。

3. .env を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成（例: プロジェクトルートに配置）。必要な環境変数の一部は次の通り:

     必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

     任意 / デフォルト付き:
     - KABUSYS_ENV (development, paper_trading, live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - LOG_DIR — デフォルト: logs
     - KILL_FLAG_CLEAR_ON_START — 0/1（本番では 0 推奨）
     - PAPER_FILL_MODE — instant/partial/never/reject（paper_trading の振る舞い）

   - .env の例（最小）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```

4. データディレクトリ等を作成（多くの処理は起動時に自動作成しますが明示的に作成しておくと安全です）:
   ```bash
   mkdir -p data logs
   ```

5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告もエラーとして扱う厳格モード:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（主要コマンド）

- Execution Engine を起動（発注エンジン）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は paper DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient が使用され、本番 DB と分離されます。
  - 停止するには `data/stop_requested.flag` を作成するか、プロセスを SIGINT（Ctrl+C）で終了してください。
  - Execution は起動時に kill.flag を自動でクリアするかどうかは KILL_FLAG_CLEAR_ON_START に依存します。

- Monitoring（監視ループ）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒単位に設定（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（monitoring.db）を使ってログを記録します（monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計）。
  - 停止フラグ: プロジェクトルートの `data/stop_requested.flag` が存在するとループを終了します。

- 設定ウィザード（.env 作成）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（例: レジーム判定・ニューススコアリング）はライブラリ呼び出しから使用します。OpenAI API キーが必要です（OPENAI_API_KEY 環境変数、または関数引数で指定）:
  - 例（レジーム判定をスクリプトから呼ぶ）:
    ```python
    from kabusys.ai.regime_detector import score_regime
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=<date>, api_key="sk-xxxx")
    ```

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: デフォルト INFO
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング周期（秒）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: paper_trading の約定振る舞い（instant, partial, never, reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" でクリア）

---

## Kill Switch / 停止フラグ

- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）
  - RiskMonitor 等が条件を満たすと KillSwitch がこのファイルを書き込み、ExecutionEngine に停止シグナルを送ります（ファイルの存在を検出して停止）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされます（本番では非推奨）。
- stop_requested.flag（data/stop_requested.flag）
  - run_execution / run_monitoring の外部停止用フラグ。存在するとループを終了します。
- PID ファイル: data/execution.pid（Execution 起動時に書き込まれる）

---

## ログ

- ログ出力は標準出力（stdout）とファイル（logs/<app_name>.log）に行われます（TimedRotatingFileHandler、日次ローテーション、30 日保持）。
- ログディレクトリは LOG_DIR 環境変数で指定可能。ディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

## ディレクトリ構成（抜粋）

プロジェクトルートの `src/kabusys` に主要モジュールが格納されています。主なファイル・ディレクトリ:

- src/kabusys/__init__.py
- src/kabusys/config.py — 環境変数 / .env ロードと Settings
- src/kabusys/config_setup.py — .env 対話式ウィザード
- src/kabusys/validate_config.py — 設定検証 CLI
- src/kabusys/run_execution.py — ExecutionEngine 起動スクリプト
- src/kabusys/run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- src/kabusys/utils/
  - logging_setup.py
  - process_priority.py
- src/kabusys/monitoring/
  - monitoring_db.py
  - system_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - (trade_monitor.py, alert_manager.py 等は同階層に存在)
- src/kabusys/execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- src/kabusys/tools/
  - paper_verification_report.py
- data/ （ランタイムで生成される / DB・フラグファイル等）
- logs/（ログファイル）

※ 上記はリポジトリ内の主要ファイルを抜粋したものです。詳細はソースツリーを参照してください。

---

## 開発・運用時の注意点 / トラブルシュート

- .env を絶対に Git にコミットしないでください（.env は秘密情報を含みます）。
- 本番環境では KABUSYS_ENV=live、KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動クリアは危険）。
- OpenAI を使用する機能は API キーと通信コストが必要です。テスト時は API 呼び出し部分をモックすることを推奨します。
- DuckDB / SQLite ファイルのパス（DUCKDB_PATH / SQLITE_PATH）は config で適宜変更してください。監視コンポーネントは sqlite_path を必ず使用する点に注意。
- CPU・メモリ等の閾値は Settings（環境変数）で調整できます（CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT）。
- psutil によるプロセス優先度 / CPU affinity 設定は OS 権限に依存します。権限不足時は警告を出してスキップします。

---

## さらなる参照

- 各モジュール（ai/news_nlp.py, portfolio/*, research/*, monitoring/* 等）の docstring に設計意図や詳細な処理フローが記載されています。実装の理解・変更時はそちらを参照してください。
- config ディレクトリに sample YAML（system_config.yaml 等）がある想定です。`python -m kabusys.validate_config` で YAML のパースチェックを行います（PyYAML インストール時）。

---

この README はリポジトリ内のソース（docstring・コメント）を元に作成しています。運用・本番移行の際は各設定と外部依存（API キー・ブローカー接続・ネットワーク、権限等）を十分に確認してください。必要であれば、README に環境別の運用手順（systemd/tmux/docker など）やデプロイ手順を追加できます。
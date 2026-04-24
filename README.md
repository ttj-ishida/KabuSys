# KabuSys

日本株向け自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・研究ツール・AI 補助（ニュース NLP / レジーム判定）を含む自動売買システムのコードベースです。  
以下はリポジトリの概要、機能、セットアップ方法、基本的な使い方、主要ディレクトリ構成の説明です。

注意: 本 README はソースコード（src/kabusys）を基に作成しています。実行にあたっては環境変数の設定 (.env) が必須な項目があります。  

---

## プロジェクト概要

- 株価データ（DuckDB）を使った研究・ファクター計算モジュール
- ポートフォリオ構築（候補選定・重み付け・株数計算・セクター制約）
- 発注実行エンジン（ExecutionEngine） — live / paper_trading モード対応
- モニタリング機構（System / Trade / Risk モニタ）と Kill Switch による安全停止
- ニュースの LLM（OpenAI）によるセンチメントスコア付与およびレジーム判定
- 研究用ユーティリティ（ファクター計算、IC 計算、特徴量探索）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、無効化可能）
  - 対話式設定ウィザード: kabusys.config_setup
  - 設定検証 CLI: kabusys.validate_config（--strict オプションあり）
- 実行系
  - ExecutionEngine 起動スクリプト: run_execution.py
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に記録（本番 DB と分離）
    - 起動時にプロセス優先度を "high" にセット
  - Monitoring 起動スクリプト: run_monitoring.py
    - 定期ポーリング（MONITOR_POLL_INTERVAL 環境変数で上書き、デフォルト 60 秒）
    - System / Trade / Risk モニタを統合
    - KillSwitch による execution 停止指示（data/kill.flag）
- モニタリング
  - system_monitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
  - trade_monitor: 注文滞留・約定異常などの検出（trade_logs テーブル参照）
  - risk_monitor: ドローダウン・ポジション上限監視（dashboard / positions）
  - monitoring_db: SQLite を用いた永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ
  - 候補選定・重み計算（等配分・スコア加重）
  - セクター上限適用、レジーム乗数
  - 株数算出（risk_based / equal / score）、lot（単元）丸め、aggregate cap
- 研究モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（スピアマン）算出、統計サマリー
- AI 関連
  - ニュース NLP（OpenAI）で銘柄別 sentiment / ai_score を生成し ai_scores に書き込み
  - レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM センチメント）
  - 両機能とも API キー（OPENAI_API_KEY）に依存し、失敗時のフォールバックがある設計
- 運用ツール
  - paper_verification_report: ペーパートレード DB から検証レポート（稼働率、約定率、レイテンシなど）を出力

---

## 必要な依存パッケージ（代表例）

最低限必要なパッケージ（環境により異なる）:
- Python 3.10+（コード内の型記法により）
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合に必要）

インストール例:
```bash
python -m pip install duckdb psutil openai pyyaml
```

（実際の requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリを取得して、Python 仮想環境を作る
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb psutil openai pyyaml
   ```

2. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他: KABUSYS_ENV（development / paper_trading / live）、DUCKDB_PATH、SQLITE_PATH、OPENAI_API_KEY（AI 機能使用時）など
   - 自動ロード: 起動時にプロジェクトルートの .env / .env.local が自動読み込みされます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

3. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
   ```

4. データディレクトリ（デフォルト）:
   - DuckDB: data/kabusys.duckdb
   - SQLite (監視): data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に利用）
   - ログ: logs/<app_name>.log（setup_logging によりログディレクトリは自動作成される）

---

## 使い方（例）

- ExecutionEngine を起動（通常: systemd / supervisor 等で管理）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し paper_trading 用 DB に記録します。
  - 起動前に data/stop_requested.flag が存在すると起動をキャンセルします。
  - 実行中に data/stop_requested.flag が作成されるとエンジンは安全に停止します。
  - エンジンは data/execution.pid に PID を書きます（設定でパス変更可能）。

- Monitoring を起動
  ```bash
  # ポーリング間隔を環境変数で上書き（秒単位。デフォルト 60）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視ループは定期的に System / Trade / Risk モニタを実行し、必要に応じて kill.flag を書くことで ExecutionEngine に停止指示を送ります。
  - Monitoring は監視用 SQLite DB（Settings.sqlite_path）を使用します（環境にかかわらず本番 sqlite_path を使う実装上の挙動）。

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。オプション --db で別パスを指定できます。
  - レポートは稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL を表示します。
  - 閾値はソースコード内に定義（例: uptime >= 99%、fill_rate >= 90% など）。

- .env ウィザード（再掲）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（再掲）
  ```bash
  python -m kabusys.validate_config --strict
  ```

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- OPENAI_API_KEY: OpenAI API を使う機能で必要
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB のデフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の埋め方（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト logs/）
- PID_FILE_PATH: 実行エンジン PID のファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch が書き込むフラグ（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

---

## 停止 / 制御フラグ

- data/stop_requested.flag
  - run_execution / run_monitoring の起動ループで参照し、存在するとループを終了します（手動の即時停止用）。
- data/kill.flag
  - Monitoring の KillSwitch が発動した際に書き込まれるファイル。ExecutionEngine 側はこのファイルの存在を確認して安全停止します（実装によりパスは Settings.kill_flag_path から取得）。

---

## ログ

- ログは stdout（コンソール）とファイル（logs/<app_name>.log）へ出力されます。
- ファイル出力は日次ローテーション（30 日分保持）です。
- setup_logging() により、全起動スクリプトで統一的なロギング設定が適用されます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・Settings 管理（.env 自動ロード）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                — ニュースの LLM スコアリング
    - regime_detector.py         — 市場レジーム判定（LLM + MA200）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（テーブル作成・操作）
    - system_monitor.py          — システム・データ鮮度監視
    - trade_monitor.py           — 注文監視（trade_logs を参照）
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — Kill Switch ロジック（flag 書き込み）
    - monitoring_engine.py       — 各モニタを束ねるエンジン
    - alert_manager.py           — （アラート送信管理、省略説明）
  - execution/
    - execution_engine.py        — ExecutionEngine 本体（起動・セッション管理）
    - order_manager.py           — 注文管理
    - order_repository.py        — 注文永続化（SQLite）
    - reconciler.py              — オーダーとブローカー整合処理
    - broker_factory.py          — ブローカークライアント生成（Mock / Live 切替）
    - risk_manager.py            — 実行時リスク管理（rate limit, max_position など）
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数算出（allocation）
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py         — ファクター計算（momentum/value/volatility）
    - feature_exploration.py     — 将来リターン・IC・統計ユーティリティ
  - utils/
    - logging_setup.py           — 共通ログ設定
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (ランタイムで作成される想定)
    - *.db / kill.flag / stop_requested.flag / execution.pid

（上記は主要モジュールの抜粋です。詳細は各ファイルの docstring を参照してください。）

---

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では設定ミスが重大な影響を与えます。validate_config を実行して警告・エラーを事前に確認してください。
- .env は決して Git にコミットしないでください（config_setup.py のヘッダにもその注意あり）。
- OpenAI API を利用する機能は API キーと利用コストに注意してください。API エラー時はフェイルセーフ（スコア 0 やスキップ）で継続する実装です。
- Monitoring は監視 DB（SQLite）と DuckDB に依存します。DuckDB は分析用データベースとして外部データ取り込みの受け口になります。
- プロセス優先度設定 (psutil) は権限の関係で失敗する場合がありますが、失敗時は警告ログを出してスキップします。
- 起動／停止フローは flag ファイル（data/stop_requested.flag, data/kill.flag）で制御されています。自動化された運用ではこれらのファイル管理に注意してください。

---

この README はコードベースの主要点をまとめたものです。詳細な実装や API の仕様は各ソースファイルの docstring・コメントを参照してください。追加で「導入手順の自動化 (systemd / docker / docker-compose)」や「テストの実行方法」をまとめる必要があれば教えてください。
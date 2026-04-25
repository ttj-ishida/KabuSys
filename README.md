# KabuSys

日本株向け自動売買 / 研究基盤の一部を実装した Python パッケージ群です。本リポジトリは取引実行・監視・ポートフォリオ構築・リサーチ・AI ニュース解析などのモジュールを含みます。

> バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような責務を持つモジュール群で構成されています。

- Execution: 発注エンジン (ExecutionEngine)、Order 管理、リスク管理など
- Monitoring: システム稼働監視、注文ログ監視、リスク監視、Kill Switch
- Portfolio: 候補選定、重み算出、ポジションサイズ計算、セクター制限
- Research: ファクター計算、特徴量探索、将来リターン / IC 計算
- AI: ニュース NLP（OpenAI を用いたセンチメント評価）、レジーム判定
- Tools: ペーパートレード検証レポート生成など
- Utils: ログ設定、プロセス優先度設定、設定読み込みユーティリティなど

設計上のポイント:
- 環境変数 / .env による設定管理（自動読み込み／対話式ウィザードあり）
- 本番 DB / ペーパートレード DB を明確に分離可能
- OpenAI を使う処理はフェイルセーフ（API 失敗時はスキップ/デフォルト動作）
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に使用

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV により paper/live で挙動切替）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 環境設定・検証
  - python -m kabusys.config_setup : 対話式 .env 作成ウィザード
  - python -m kabusys.validate_config : .env / config/*.yaml の静的検証
- 監視
  - system_monitor / trade_monitor / risk_monitor を統合した MonitoringEngine
  - データ永続化用 MonitoringDB (SQLite)
  - kill.flag による ExecutionEngine 停止（KillSwitch）
- 発注・リスク
  - OrderManager / RiskManager / Reconciler / ExecutionEngine（発注フロー）
  - Paper Trading モードでは MockBrokerClient を利用し、専用 SQLite に記録
- ポートフォリオ構築
  - 候補選定、等重/スコア重み付け、リスク制約（セクター上限、レジーム乗数）、株数算出（単元丸め）
- リサーチ
  - momentum / volatility / value 等のファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI（OpenAI）
  - ニュース記事の銘柄別センチメント評価（ai_scores テーブルへ書込）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- ツール
  - ペーパートレードの検証レポート出力（期間指定可）

---

## 必要な依存パッケージ (例)

最低限必要な外部パッケージはソースから読み取れるものです。プロジェクトの実際の requirements.txt がある場合はそちらを優先してください。

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML — config/*.yaml の構文チェックを行う場合

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリを取得してプロジェクトルートへ移動

2. 仮想環境を作成・有効化し依存をインストール（上記参照）

3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードで J-Quants / kabu API のトークンや DB パスなどを設定します。
   主要な必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   重要なオプション:
   - KABUSYS_ENV: development | paper_trading | live (default: development)
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時に使用)
   - OPENAI_API_KEY: OpenAI を使う機能に必要（AI モジュール）
   - LOG_LEVEL: DEBUG/INFO/...

   自動ロード挙動:
   - プロジェクトルートに .env または .env.local があれば自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリ作成（ログ / data）
   多くのランタイムは `logs/` と `data/` ディレクトリを使用します。通常は自動作成されますが、権限が厳しい環境では事前作成してください。

---

## 使い方 (主要コマンド)

- ExecutionEngine の起動
  - 本番（または設定に応じた動作）で発注エンジンを起動します。
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます。

  停止方法:
  - 実行中にプロセス優先度や PID 管理が行われます。停止フラグを書き込むことで安全に停止できます:
    - stop フラグ: data/stop_requested.flag（run_execution はこのファイルを監視して停止）
    - Kill Switch: monitoring が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る仕組みがあります。

- Monitoring の起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は設定に関わらず本番 sqlite_path を参照して監視ログを永続化します。

- .env の対話式作成
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能
  - OpenAI キーは環境変数 OPENAI_API_KEY か、関数呼び出し時に引数で渡します。
  - news_nlp.score_news や regime_detector.score_regime を使って ai_scores / market_regime を更新します。
  - API 呼び出しはリトライ・フェイルセーフの設計です。

- ログ
  - logging_setup.setup_logging を使い、デフォルトで `logs/<app_name>.log` に日次ローテーションで保存します。
  - 環境変数 LOG_DIR でログディレクトリを変更可能。

---

## 停止・保護機構

- stop_requested.flag (data/stop_requested.flag)
  - run_monitoring / run_execution が監視している単純な停止フラグファイル。存在すると起動中のループは終了します。

- kill.flag (data/kill.flag)
  - Monitoring の KillSwitch が書き込み、ExecutionEngine に危険停止を通知するために用いられます。ファイルに理由テキストを保存します。

- PID ファイル
  - run_execution は data/execution.pid を PID 保存に使います。設定は Settings.pid_file_path で変更可能。

---

## 設定上の注意

- KABUSYS_ENV は development / paper_trading / live のいずれかを指定します。live の場合は特に注意深く設定を確認してください（validate_config で警告が出ます）。
- .env は絶対にリポジトリへコミットしないでください（config_setup のヘッダにも記載されています）。
- Paper Trading は本番 DB と分離するよう設計されています（paper_sqlite_path を使用）。

---

## ディレクトリ構成（主なファイル・モジュール）

以下はパッケージ内の主要構成（src/kabusys 以下）です。主なモジュールと役割を示します。

- kabusys/
  - __init__.py
  - config.py — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/ — 発注周りの実装（Engine, OrderManager, BrokerFactory, RiskManager, Reconciler 等）
  - monitoring/
    - monitoring_db.py — SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システムリソース・データ鮮度監視
    - trade_monitor.py — 注文ログ監視（滞留注文・約定異常等）
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — Kill Switch 実装
    - monitoring_engine.py — 各 Monitor の統合実行
    - alert_manager.py — アラート送信管理（LINE 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・投下資金のスケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュースの LLM によるセンチメント評価と ai_scores 書き込み
    - regime_detector.py — ETF MA とマクロセンチメントでレジーム判定
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ — 実行時に使用される SQLite / DuckDB / フラグファイル等（実行環境で生成）

---

## 開発時のヒント

- DuckDB を用いている関数群は DuckDB 接続を引数に取るため、テストでは in-memory DuckDB 接続を使うと良いです。
- OpenAI API 呼び出し部分は _call_openai_api を patch してモック化するとユニットテストが容易です（ソース内にその旨のコメントあり）。
- .env の自動読み込みはプロジェクトルート検出機能に依存します（.git または pyproject.toml を基準）。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

---

## よく使うコマンドまとめ

- 仮想環境・依存インストール
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML
  ```

- .env 作成（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- 実行エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```

- 監視プロセス起動
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README の拡張（詳しい構成図、シーケンス図、設定例のテンプレート、運用手順など）を追加できます。追加で欲しいドキュメント項目があれば教えてください。
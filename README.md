# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
戦略のリサーチ・ファクター計算、ポートフォリオ構築、注文実行エンジン（本番 / ペーパートレード切替）、監視・アラート、LLM を活用したニュースセンチメント評価などを含むモジュール群で構成されています。

Version: 0.1.0

---

## 概要

このリポジトリは以下の主要機能を持ちます。

- ExecutionEngine：ブローカーと連携して発注を行う実行エンジン。KABUSYS_ENV によって paper_trading（MockBroker）／live を切替。
- Monitoring：システム稼働状況、データ鮮度、注文状況、リスク（ドローダウン・ポジション上限）を定期監視し、ログ・アラート・Kill Switch（停止フラグ）を管理。
- Portfolio モジュール：候補選定、重み付け、ポジションサイズ計算、セクターキャップ等の純粋関数実装。
- Research：DuckDB を用いたファクター計算（Momentum / Volatility / Value）、将来リターン計算、IC 等の統計解析ユーティリティ。
- AI（LLM）連携：ニュース記事を LLM（OpenAI）で評価して銘柄別スコアを生成、マクロセンチメントと価格指標を合成して市場レジーム判定。
- ユーティリティ：ロギング設定、プロセス優先度設定、設定ウィザード・検証ツール、各種 DB マイグレーション／永続化層。

---

## 主要機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの `.env` / `.env.local`）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行
  - 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - ペーパートレード用の分離 DB（data/paper_trading.db）
- 監視
  - ポーリング監視ループ（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL によるポーリング間隔オーバーライド
  - monitoring_db に system_status / trade_logs / positions / risk_logs / dashboard を保持
  - Kill Switch（data/kill.flag）による外部からの停止制御
- ポートフォリオ構築
  - 候補選定（スコア／ランク）
  - 等金額・スコア加重配分
  - リスクベースのポジションサイズ計算（lot 単位丸め、利用可能キャッシュに対するスケーリング）
  - セクターキャップ、レジーム乗数
- リサーチ
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）や統計要約
- AI（LLM）連携
  - ニュースをまとめて LLM で銘柄別センチメントを算出し ai_scores テーブルへ書込
  - マクロニュースと ETF MA 指標で市場レジーム判定（market_regime テーブルへ書込）
  - API 呼び出しでのリトライ・バリデーション・フェイルセーフ実装
- ツール
  - ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 前提 / 必要環境

- Python 3.10 以上（PEP 604 の型記法などを使用）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証、任意）
- SQLite は標準ライブラリで利用
- ネットワーク接続（実際に OpenAI / ブローカー API を利用する場合）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
（実際の要件はプロジェクトに合わせて requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境と依存ライブラリのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV は development / paper_trading / live のいずれか
   - paper_trading モードでは PAPER_TRADING_SQLITE_PATH（data/paper_trading.db デフォルト）に分離して記録されます

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告をエラーにするなら:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成（必要な場合）
   ```bash
   mkdir -p data logs
   ```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う / 主要:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用の DB、default: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/…)
- LOG_DIR (ログファイル保存先、default: logs/)
- OPENAI_API_KEY（AI モジュール使用時）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、default: 60）

Kill / stop フラグ:
- data/kill.flag — KillSwitch のトリガー
- data/stop_requested.flag — run_execution/run_monitoring が参照する停止フラグ
- data/execution.pid — ExecutionEngine が生成する PID ファイル

自動 .env ロードはデフォルトで有効。無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（コマンド例）

- 実行エンジン（Engine）を起動
  - 本番／ペーパーは KABUSYS_ENV による
  ```bash
  python -m kabusys.run_execution
  ```

- 監視ループ起動（定期ポーリング）
  ```bash
  # ポーリング間隔を変更する例（30秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート（範囲指定）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- ライブラリ関数の利用（Python REPL / スクリプト内）
  ```python
  from kabusys import portfolio, research, ai
  # ポートフォリオ関数
  candidates = portfolio.select_candidates(buy_signals, max_positions=10)
  weights = portfolio.calc_score_weights(candidates)
  sizes = portfolio.calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)
  # DuckDB 接続がある場合の研究関数
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  factors = research.calc_momentum(conn, date(2026,4,1))
  # AI スコアリング（DuckDB 接続を渡す）
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  ```

---

## 監視・停止操作について

- 監視/実行プロセスは data/stop_requested.flag を検知すると安全にループ／スレッドを終了します（外部ツール等でこのファイルを作成して停止可能）。
- KillSwitch はリスク条件を満たしたときに data/kill.flag を書き込みます。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリア（本番では 0 推奨）。

---

## ディレクトリ構成（主なファイル）

簡易ツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py           — ログ初期化ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py
    - trade_monitor.py           — （取引監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py           — （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                         — （runtime データファイル: DB / flags / pid 等）
  - logs/                         — （デフォルトのログ出力先）

各モジュールは README 内の「主要機能一覧」に沿って役割分担されています。詳細は各ファイルの docstring / 関数コメントを参照してください。

---

## 注意事項 / 運用メモ

- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知や API キー等を正しく構成してください。validate_config で追加の警告が出ます。
- .env は機密情報を含むため絶対にリポジトリに含めないでください (.gitignore に追加すること)。
- DuckDB・SQLite のファイルパスを変更する場合は .env で DUCKDB_PATH / SQLITE_PATH を設定してください。
- OpenAI の呼び出しはコストが発生します。rate limit／エラー時のリトライ・フェイルセーフの実装はありますが、本番ではキー管理と費用監視を行ってください。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリのパーミッションに注意してください。

---

この README はコードベースの主要な使い方と構成をまとめたものです。各モジュールの詳細な設計や API 仕様は該当ファイルの docstring を参照してください。必要であれば、運用手順・デプロイ手順・監視ダッシュボードの追加ドキュメントを作成します。
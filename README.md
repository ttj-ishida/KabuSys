# KabuSys — 日本株自動売買システム

README.md（抜粋）へようこそ。  
このドキュメントは、提供されたコードベースの概要、主要機能、セットアップ方法、使い方、およびディレクトリ構成を日本語でまとめたものです。

重要: ここではリポジトリ内の主要モジュールから読み取れる動作仕様を記載しています。実運用時は必ず `python -m kabusys.validate_config` により設定検証を行ってください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤です。  
主な目的は以下です。

- 日次・秒次のモニタリング（システム状態、注文状況、リスク監視）
- ExecutionEngine による発注・注文管理（本番／ペーパートレード両対応）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン解析、IC算出）
- AI を活用したニュースセンチメント（OpenAI）や市場レジーム判定
- 運用検証レポート（Paper Trading 用）

設計上、DB（SQLite／DuckDB）と API（kabuステーション, J-Quants, OpenAI）を分離し、ペーパートレード時は本番 DB と分離して動作します。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルート検出）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / モニタリング
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading で MockBroker を使用し DB を分離
    - 停止はフラグファイルで制御（data/stop_requested.flag 等）
  - SystemMonitor 起動スクリプト（run_monitoring.py）
    - ポーリング間隔は環境変数で上書き可能（MONITOR_POLL_INTERVAL、デフォルト 60 秒）
    - システム・データ鮮度を監視し monitoring DB に記録
- モニタリング詳細
  - SystemMonitor: CPU/MEM/DISK、Execution プロセス監視、データ鮮度
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン、ポジション上限のチェック、ダッシュボード更新
  - KillSwitch: 条件で kill.flag を書き込み Execution を停止させる
  - MonitoringEngine: 上記を束ねて周期的に実行、アラート送信可能
- ポートフォリオ構築
  - 候補選定（score / rank による上位選定）
  - 重み計算（等金額、スコア加重）
  - セクター・レジームに基づく制約（apply_sector_cap, calc_regime_multiplier）
  - ポジションサイズ決定（単元株丸め、リスクベース、集約キャップ）
- リサーチ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン、IC（スピアマン）計算、統計サマリー
- AI（OpenAI）
  - ニュースの銘柄別センチメント算出（kabusys.ai.news_nlp）
  - マクロニュース + MA200 による市場レジーム判定（kabusys.ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発向け）

1. Python 環境を用意
   - 推奨: Python 3.10+（ソース注釈に型ヒント使用）
   - 仮想環境を作成して有効化（venv / pyenv など）

2. 必要パッケージをインストール
   - 以下は最小限の依存（実際の requirements.txt がある場合はそちらを使用してください）。
     - duckdb
     - psutil
     - openai（AI 機能使用時）
     - PyYAML（config 検証で YAML を検証したい場合）
   - 例:
     ```bash
     pip install duckdb psutil openai PyYAML
     ```
   - プロジェクトを編集可能インストールする場合:
     ```bash
     pip install -e .
     ```

3. .env を作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - 手動編集の場合はプロジェクトルートに `.env` を作成（例は下記「環境変数例」参照）。

4. 設定検証
   - .env を用意したら validate を実行:
     ```bash
     python -m kabusys.validate_config
     ```
   - 本番準備で警告も厳格に扱う場合:
     ```bash
     python -m kabusys.validate_config --strict
     ```

5. DB 初期化
   - `run_execution` / `run_monitoring` 実行時に必要テーブルを作成する init_routine が自動実行されます（monitoring 用は init_monitoring_db）。

注意: AI 機能を使うには `OPENAI_API_KEY` が必要です。kabu API や J-Quants を使うにはそれぞれのキー・パスワードが必要です。

---

## 環境変数（主要）

必須（少なくとも本番や一部機能で必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

オプション / 推奨
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading のとき、Execution は MockBroker を使用し `data/paper_trading.db` を使用する
- OPENAI_API_KEY — OpenAI を利用する場合に必須（news_nlp, regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — PaperTrading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログ出力レベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒、run_monitoring で参照、デフォルト 60）
- PID_FILE_PATH — Execution の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch のフラグパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア）

サンプル .env（抜粋）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-xxxx...
```

---

## 使い方（よく使うコマンド）

- 設定ウィザード（.env 作成/更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（本番／paper_trading を .env の KABUSYS_ENV で切替）
  ```bash
  python -m kabusys.run_execution
  ```
  - 動作:
    - 環境に応じた SQLite を接続（paper_trading の場合は paper_sqlite_path）
    - MockBroker を使うか実ブローカを使うか自動判定
    - Execution は別スレッドで run_session を実行し、data/stop_requested.flag により停止検出

- Monitoring を起動（SystemMonitor のループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位に調整できます（デフォルト 60）。
  - Monitoring は常に本番の sqlite_path を使用する仕様（環境に依らず監視 DB は production path を使う）。

- Paper Trading 検証レポート出力
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで DB パス指定可。環境変数 `PAPER_TRADING_SQLITE_PATH` も参照。

- AI 関連（プログラムから呼び出す API）
  - news_nlp:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - 要: DuckDB 接続・OPENAI_API_KEY（引数で渡すこと可）
  - regime_detector:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 要: DuckDB 接続・OPENAI_API_KEY

停止・Kill フラグの扱い
- run_execution はプロジェクトルートの `data/stop_requested.flag` を監視して停止します（run_execution 内の _STOP_FLAG）。
- KillSwitch（monitoring 側）は `Settings.kill_flag_path`（デフォルト data/kill.flag）に理由を記述して Execution を停止させるトリガになります。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では推奨しません）。

ログ / 優先度
- 起動時に set_process_priority("high") を試行します。権限がない場合は警告ログを出してスキップします。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要モジュール一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - execution/                 — 発注エンジン関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信ロジック）
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
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

データディレクトリ（リポジトリルートに想定）
- data/
  - kabusys.duckdb        (DuckDB、デフォルト: data/kabusys.duckdb)
  - monitoring.db         (監視用 SQLite、デフォルト: data/monitoring.db)
  - paper_trading.db      (ペーパートレード用 SQLite、デフォルト: data/paper_trading.db)
  - execution.pid         (Execution の PID ファイル)
  - kill.flag / stop_requested.flag (停止フラグ)

---

## 実装上の注意点 / 運用上の注意

- 環境の分離
  - paper_trading モードでは本番の monitoring DB とペーパートレード DB を分離する設計です。混同しないよう .env を管理してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に対して列追加（マイグレーション）も行います。
- OpenAI 呼び出し
  - API エラー（429、タイムアウト、5xx）は指数バックオフでリトライしますが、永続失敗時はフェイルセーフで処理をスキップします（例外を投げない設計の箇所あり）。
- プロセス優先度・CPU affinity
  - set_process_priority / set_cpu_affinity は権限によって失敗する可能性があり、その場合はログに警告を出して処理を続行します。
- ロギング
  - 起動時に basicConfig(level=INFO) が設定されます。詳細ログが必要な場合は LOG_LEVEL を設定してください。
- セキュリティ
  - .env は機密情報を含むため絶対にリポジトリにコミットしないでください（config_setup でもその旨が書かれています）。

---

## 開発者向け補足（関数／API の簡易）

- ポートフォリオ関数（pure functions）
  - select_candidates(buy_signals, max_positions)
  - calc_equal_weights(candidates)
  - calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)
  - apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map, ...)
  - calc_regime_multiplier(regime)

- リサーチ関数
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons)
  - calc_ic(factor_records, forward_records, factor_col, return_col)

- AI 関数（DuckDB 接続を受け取る）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

この README はコードから抽出できる情報をベースにした要約です。各モジュールには docstring と実装上の注釈が豊富にあるため、詳細な挙動は該当ソース（例: monitoring/*.py, ai/*.py, portfolio/*.py）を参照してください。

追加で以下が必要であれば作成します:
- .env.example の具体的テンプレート
- 運用手順（systemd / supervisor を用いた起動方法）
- 開発用の requirements.txt / Dockerfile

必要ならどれを優先して作るか教えてください。
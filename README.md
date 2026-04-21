# KabuSys

日本株向け自動売買フレームワークの一部（設定管理、監視、ポートフォリオ構築、リサーチ、AI支援など）のコードベースです。  
この README はリポジトリ内の提供スクリプト / モジュール（抜粋）に基づく使い方ガイドです。

注意: 実際の注文を行うモジュールは本番リスクを伴います。環境設定（特に KABUSYS_ENV=live）では慎重に扱ってください。

---

## プロジェクト概要

- 簡易自動売買システムのユーティリティ群：
  - 環境設定ウィザード / 検証（`.env` 管理）
  - ExecutionEngine 起動スクリプト（paper/live で DB 分離）
  - Monitoring（システム稼働・注文・リスク監視）
  - Portfolio 構築 (候補選定・重み付け・株数計算)
  - Research（ファクター計算・特徴量探索）
  - AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
  - 各種ツール（Paper Trading 検証レポート 等）

- 設計のポイント（コード注釈より）
  - .env はプロジェクトルートの `.env` / `.env.local` を自動読み込み（OS環境変数優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - paper_trading 環境は本番 DB と明確に分離（`PAPER_TRADING_SQLITE_PATH`）。
  - Logging は共通ユーティリティで stdout と日次ローテートファイル（logs/）に出力。
  - OpenAI を使った処理は API キー（`OPENAI_API_KEY`）を要求。

---

## 主な機能一覧

- 設定管理
  - 対話式ウィザードで `.env` を生成 / 更新（`kabusys.config_setup`）
  - 設定ファイル・環境変数の事前検証（`kabusys.validate_config`）

- 実行系
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、`data/paper_trading.db` に記録
    - 停止はフラグファイル（`data/stop_requested.flag` / `data/kill.flag` 等）で制御

- 監視系
  - System / Trade / Risk 各モニタを統合する MonitoringEngine（ポーリング）
  - kill-switch による自動停止フラグ生成（ドローダウン等で Execution 停止）
  - run_monitoring 起動スクリプト（ポーリング間隔は env `MONITOR_POLL_INTERVAL` で上書き可）

- ポートフォリオ構築
  - 候補選定、等重/スコア重み、レジーム補正、セクター上限、ポジションサイズ算出（単元丸め等）

- リサーチ / 統計
  - モメンタム / ボラティリティ / バリュー等のファクター算出（DuckDB 上の prices_daily/raw_financials）
  - 将来リターン、IC（情報係数）、ファクター統計

- AI 関連
  - ニュースを集約して OpenAI（gpt-4o-mini 等）で銘柄別センチメントを算出し DB に格納
  - マクロニュース + ETF MA200 乖離を合成して市場レジーム判定

- ユーティリティ
  - Paper Trading 検証レポート生成スクリプト（成功率/稼働率/レイテンシ等の集計）

---

## 要件（推奨）

- Python 3.10+
  - 理由: 型注釈に `X | Y`（PEP 604）を使用
- 主要 Python パッケージ:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証で YAML パースを行う場合）
- SQLite は標準ライブラリで利用
- ネットワークアクセス: 各 API（kabuステーション, J-Quants, OpenAI 等）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. .env を作成
   - 対話式ウィザード: `python -m kabusys.config_setup`
   - または手動で `.env` を作成（下記サンプル参照）
   - 自動ロード: プロジェクトルートに `.env` / `.env.local` があると起動時に読み込まれます。
4. 設定検証（起動前チェック）:
   - `python -m kabusys.validate_config`
   - 警告もエラー扱いにする場合: `python -m kabusys.validate_config --strict`
5. DB 初期化:
   - Monitoring 用 SQLite は起動スクリプトが `init_monitoring_db()` を呼んで作成します（`SQLITE_PATH` の DB）。
   - DuckDB（分析用）は `DUCKDB_PATH` にファイルを作成します。

重要な環境変数（要/推奨）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI:
  - OPENAI_API_KEY（AI 機能を使う場合）
- 実行環境選択:
  - KABUSYS_ENV ∈ {development, paper_trading, live}（default: development）
- データベースパス（デフォルト）
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- ログ:
  - LOG_LEVEL (default INFO)
  - LOG_DIR (default logs/)
- その他:
  - MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、default 60)
  - PAPER_FILL_MODE ∈ {instant, partial, never, reject}（paper_trading の振る舞い）

.env の簡易サンプル
```
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here

# オプション / デフォルト
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
PAPER_FILL_MODE=instant
```

---

## 使い方（起動・コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: `--strict`

- ExecutionEngine 起動（取引エンジン）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して別 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 停止フラグ: プロジェクトの `data/stop_requested.flag` が存在すると起動 / 継続を停止します。
    - 実行中の PID 管理: `data/execution.pid` を使用

- Monitoring 起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path を常に使用（モニタは環境にかかわらず本番 sqlite_path を参照）

- Paper Trading 検証レポート（スタンドアロン）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合: `--db PATH`、環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可

- AI 機能（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡す。`api_key` が None の場合 `OPENAI_API_KEY` を参照。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- その他（ライブラリとして）
  - ポートフォリオ関数等は import して利用できます:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

---

## 監視 / 停止フラグについて

- 停止シグナルファイル:
  - stop_requested.flag: run_monitoring / run_execution が参照する停止フラグ（プロジェクト data ディレクトリ）
  - kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に停止要求を送るため）
- PID ファイル:
  - data/execution.pid（ExecutionEngine の PID 保存）
- Settings により `kill_flag_clear_on_start` を設定すると起動時に kill.flag を自動でクリアする（本番ではデフォルト 0 推奨）

---

## 主要モジュールと説明（抜粋）

- kabusys.config
  - .env 読み込みロジック（`.env` / `.env.local`）、Settings クラスで環境変数をプロパティ化
- kabusys.run_execution
  - ExecutionEngine を起動。paper_trading は DB 分離
- kabusys.run_monitoring
  - SystemMonitor を定期実行（MONITOR_POLL_INTERVAL）
- kabusys.monitoring.*
  - monitoring_db: SQLite のスキーマ作成 / 永続化 API
  - system_monitor, trade_monitor, risk_monitor: 各種監視ロジック
  - monitoring_engine: 各 monitor を束ねる
  - kill_switch, alert_manager: 停止判定・通知管理（alert_manager は実装箇所に依存）
- kabusys.portfolio.*
  - portfolio_builder, position_sizing, risk_adjustment: ポートフォリオ構築の純粋関数群
- kabusys.research.*
  - factor_research, feature_exploration: ファクター計算・評価
- kabusys.ai.*
  - news_nlp: ニュースを LLM に投げて銘柄別スコア化し ai_scores に保存
  - regime_detector: マクロ要因 + ETF MA で市場レジーム判定
- kabusys.tools.paper_verification_report
  - Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

---

## ディレクトリ構成（抜粋）

（リポジトリの src/kabusys 以下を抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (注: 実装箇所に依存)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/（DB/監視関連）
  - execution/（Execution 関連コンポーネント、ブローカーファクトリ等）
  - data/（実行時に生成される想定: logs/, DB ファイル, pid/flag ファイル など）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では .env の内容・LINE 通知設定等を入念に確認してください。`validate_config` は本番環境時に追加警告を出します。
- kill_switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険：0 を推奨。
- paper_trading を使うと本番 DB と分離されますが、設定ミスを防ぐため env の確認を必ず行ってください。
- OpenAI を使う処理はトークン料金・API レートに注意。実行は必ず API キーを安全に管理してください。

---

もし README に追加したい内容（例: 実際の ExecutionEngine の起動オプション、alert_manager の実装例、テストの書き方、requirements.txt の具体的内容など）があれば教えてください。それに応じて追記します。
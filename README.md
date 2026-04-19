# KabuSys

日本株の自動売買／研究プラットフォーム（軽量版）。  
このリポジトリは発注エンジン、モニタリング、ポートフォリオ構築、ファクター計算、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を備えたシステムです。

- 発注エンジン（ExecutionEngine）：ブローカーとやり取りして注文管理・実行を行う。paper_trading モードでは MockBroker を使い、本番 DB と分離して検証可能。
- 監視コンポーネント（Monitoring）：システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）等を定期的にチェックし、Kill Switch による停止やアラートを発行。
- ポートフォリオ構築：シグナルに基づく銘柄選定、重み付け、ポジションサイズ計算、セクター制限などの純粋関数群。
- 研究用モジュール（research）：DuckDB を用いたファクター計算、将来リターン計算、IC などの分析機能。
- AI モジュール：OpenAI API を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）。
- ユーティリティ類：設定管理、対話式 .env 作成、ログ設定、プロセス優先度設定など。

設計上のポイント：
- DuckDB / SQLite をローカル DB として利用（データ永続化）。
- 設定は .env または環境変数で管理。自動ロード機能あり（プロジェクトルートに .env / .env.local がある場合）。
- paper_trading モードでは本番 DB と完全に分離して動作可能。

---

## 主な機能一覧

- run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV による paper_trading/live の切替。
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔を変更可能。
- config_setup.py: 対話式ウィザードで .env を作成 / 更新。
- validate_config.py: .env と config/*.yaml の存在・整合性チェック CLI。
- tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率 / 成功率 / レイテンシ等）。
- portfolio/*: 銘柄選定、重み付け、リスク調整、単元株丸めなどの純粋関数。
- research/*: ファクター・特徴量計算、IC、統計サマリ。
- ai/*: OpenAI を使ったニュースセンチメント、レジーム判定。
- monitoring/*: MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、アラート管理など。
- utils/*: ロギング設定、プロセス優先度 / CPU affinity 設定など。

---

## 必要条件（依存関係）

このコードベースでは最低限以下のライブラリが想定されます（バージョンは環境に合わせて調整してください）：

- Python 3.10+
- duckdb
- psutil
- openai
- sqlite3（Python 標準）
- （オプション）PyYAML（validate_config の YAML 検証時）

インストール例（venv を推奨）:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai
- （必要に応じて）pip install pyyaml

※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成して有効化
3. 依存ライブラリをインストール（上記参照）
4. 対話式設定ウィザードで .env を作成
   - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 本番利用時には KABUSYS_ENV=live や LINE 関連設定も確認してください
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も許容しない Strict モード: python -m kabusys.validate_config --strict
6. データディレクトリの作成（必要に応じて）
   - デフォルト SQLite / DuckDB のパスは data/ 下にあります（.env で上書き可能）
   - 例: mkdir -p data logs

自動 .env ロードについて:
- 起動時にプロジェクトルート（.git または pyproject.toml がある場所）を探索し、.env / .env.local を自動で読み込みます。
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数 (主要)

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

一般的な設定（デフォルト値は括弧内）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — paper_trading 用 DB
- LOG_LEVEL (INFO)
- LOG_DIR (logs/)
- PID_FILE_PATH (data/execution.pid)
- KILL_FLAG_PATH (data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- MONITOR_POLL_INTERVAL (run_monitoring 用、秒単位。デフォルト 60)
- OPENAI_API_KEY（AI モジュール利用時必須）

例（.env に記載する形）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 使い方（起動 / CLI）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBroker を使い PAPER_TRADING_SQLITE_PATH に書き込み（本番 DB と分離）

- 監視ループ（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: export MONITOR_POLL_INTERVAL=30 など

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from 2026-04-01 --to 2026-04-11
  - DB パス指定: --db path/to/paper_trading.db

ログ:
- デフォルトは logs/<app_name>.log（app_name は "execution" / "monitoring" など）
- コンソール出力は stdout に出ます（logging_setup に準拠）

Kill Switch / 停止:
- モニタはリスク条件で data/kill.flag を書き込み、ExecutionEngine はこのファイルを検出して安全停止します。
- 手動で停止させる場合は data/kill.flag に理由を書き込むか、run_monitoring / run_execution の停止フラグ（data/stop_requested.flag 等）を利用します。

バックグラウンド実行例（Linux）:
- nohup python -m kabusys.run_execution &

---

## 開発用の注意点

- Python の型注釈に Python 3.10+ の構文（X | Y）を使用しています。3.10 以上を推奨します。
- DuckDB を使うためローカル DuckDB ファイル（data/kabusys.duckdb）に prices_daily, raw_financials 等のテーブルを事前に用意してください（データ取得パイプラインは別途）。
- OpenAI を利用する AI モジュールは API キーが必要です（OPENAI_API_KEY）。
- .env はセキュアな情報を含むため絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。

---

## ディレクトリ構成

以下は src/kabusys 以下の主な構成（抜粋）です：

- kabusys/
  - __init__.py
  - config.py                 — 環境変数／.env 自動ロードと Settings
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading レポート生成
  - utils/
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity
  - execution/                — ExecutionEngine 周りの実装（発注・リスク等）※詳細ファイル群は省略
  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層 / MonitoringDB クラス
    - monitoring_engine.py    — 各モニタを束ねるエンジン
    - system_monitor.py       — システム状態／データ鮮度検査
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の作成／クリア
    - (その他: trade_monitor, alert_manager 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュースを OpenAI でスコアリングして ai_scores に書込む
    - regime_detector.py      — ETF MA とマクロセンチメントを合成してレジーム判定
  - data/                     — デフォルトの DB/log/pid ファイル格納場所（実行時に自動作成される）

ルート（プロジェクト）には .env / .env.local / pyproject.toml / .git 等がある想定です。

---

## 主要コンポーネントの短い説明

- Settings (config.py)
  - 環境変数をラップしてプロパティで取得。自動 .env ロード、必要な値の検証、paper_trading 用パス切替、閾値などを提供。

- MonitoringDB (monitoring/monitoring_db.py)
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルの初期化・永続化。スキーマのマイグレーション（カラム追加）ロジックを含む。

- SystemMonitor (monitoring/system_monitor.py)
  - CPU/memory/disk、Execution の PID 存在チェック、DuckDB のデータ鮮度チェックを行い system_status に記録。

- RiskMonitor (monitoring/risk_monitor.py)
  - ダッシュボードを元にハイウォーターマークとドローダウンを計算し、リスクイベントをログに残す。一定条件で kill.flag を作成するトリガーに使われる。

- KillSwitch (monitoring/kill_switch.py)
  - risk / system / trade のチェック結果から停止条件を評価し、data/kill.flag を書き込むユーティリティ。

- portfolio/*.py
  - シグナルのランク付け、等分配/スコア重み、セクターキャップ適用、リスクベースポジションサイズ計算（単元丸め・aggregate cap）など。

- research/*.py
  - DuckDB の prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー等のファクターを算出。IC・統計要約も提供。

- ai/news_nlp.py, ai/regime_detector.py
  - OpenAI API を用いてニュースを銘柄ごとに評価（score_news）・マクロセンチメントを算出して market_regime に書き込む（score_regime）。API エラーはリトライやフェイルセーフで扱う。

---

## よくある質問 / トラブルシューティング

- .env が自動で読み込まれない
  - プロジェクトルートが .git または pyproject.toml によって検出されないと自動ロードはスキップされます。明示的に環境変数を設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。

- Monitoring が期待通り動かない（MONITOR_POLL_INTERVAL）
  - 環境変数 MONITOR_POLL_INTERVAL を秒数で指定してください。無効値の場合はデフォルト 60 秒にフォールバックします。

- OpenAI 関連でエラーが出る
  - OPENAI_API_KEY を設定してください。API のレート制限や一時エラーは実装でリトライされますが、キーが無い場合は例外が発生します。

---

この README はコードベースの主要点をまとめたものです。より詳細な設計仕様（PortfolioConstruction.md、StrategyModel.md 等）がプロジェクト内に存在する場合はそちらを参照してください。必要であれば README にサンプル .env のテンプレートやシステム図、運用手順（デプロイ / ロールバック / ログの確認方法）を追記できます。必要な情報を教えてください。
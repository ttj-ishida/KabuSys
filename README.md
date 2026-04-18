# KabuSys — README

KabuSys は日本株の自動売買・研究・監視を目的とした軽量な Python コードベースです。本リポジトリは戦略の研究用ユーティリティ、ポートフォリオ構築ロジック、実行エンジン（ExecutionEngine）、監視サブシステム、AI を使ったニュース/レジーム判定機能などを含みます。

以下は本コードベースの概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成の説明です。

## プロジェクト概要
- 自動売買に関わる以下の主要領域を実装しています。
  - Execution: 発注・注文管理・リスク管理を行う ExecutionEngine（本番 / ペーパートレード切替可）
  - Monitoring: システム状態・注文/リスク監視、Kill Switch によるプロセス停止制御
  - Portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限などの純粋関数
  - Research: DuckDB 上でのファクター計算・特徴量解析
  - AI: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント・レジーム判定
  - Tools: ペーパートレード検証レポート生成などのスクリプト群
- 設定は .env（または環境変数）で管理。プロジェクトルートに .env を置くことで自動読み込みされます（自動読み込みは環境変数で無効化可能）。

## 主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading / live を切り替え
  - paper_trading の場合は MockBrokerClient を用い、DB を分離（data/paper_trading.db）
  - stop flag（data/stop_requested.flag）で停止
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングして system_status / risk_logs / trade_logs 等に記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）
  - 監視は常に production 用 sqlite_path を利用して記録
- 設定管理ツール
  - config_setup.py: 対話式ウィザードで .env を作成/更新
  - validate_config.py: .env / config/*.yaml の事前検証（--strict オプションあり）
- 研究・分析
  - research フォルダ: ファクター計算（momentum/value/volatility）、IC 計算 等
  - DuckDB 経由で prices_daily / raw_financials 等を参照して計算
- AI 機能
  - news_nlp.py: raw_news をまとめて OpenAI に投げ、銘柄ごとに ai_score を作成して ai_scores に書き込む
  - regime_detector.py: ETF 1321 の MA200 乖離とマクロ記事センチメントを合成して market_regime を判定し DuckDB に記録
- ユーティリティ
  - logging_setup: 統一的なロギング設定（コンソール + 日次ローテーションファイル）
  - process_priority: プロセス優先度 / CPU affinity の簡易設定
- Tools
  - paper_verification_report: ペーパートレード結果を集計して PASS/FAIL 判定付きレポートを出力

## 前提（依存ライブラリ）
最低限インストールする推奨パッケージ例:
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証に使用。無くても動作はするが警告が出ます）

インストール例:
```bash
pip install duckdb psutil openai pyyaml
```
（requirements.txt がある場合は `pip install -r requirements.txt` を推奨します）

## セットアップ手順
1. リポジトリをクローン
2. 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb psutil openai pyyaml
   ```
3. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 主要な環境変数（例、最低限設定すべきもの）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live（デフォルト: development）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=...（AI 機能を使う場合）
     - KILL_FLAG_CLEAR_ON_START=0（本番では 0 推奨）
4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じて data/ と logs/ ディレクトリの作成（logging_setup は自動で作成を試みます）

## 使い方（実行例）
- 監視ループを起動（ポーリングで system_status 等を記録）
  ```
  python -m kabusys.run_monitoring
  ```
  環境変数でポーリング間隔を変更:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  停止: プロジェクトルートの data/stop_requested.flag ファイルを作成するとループが検知して終了します。

- ExecutionEngine を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と分離します。
  - 起動済みのエンジン停止は data/stop_requested.flag を作成することで検出・停止されます。
  - エンジンは起動時に pid ファイル（デフォルト data/execution.pid）を作成します。

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを直接指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB の接続オブジェクト（kabusys.config.Settings.duckdb_path で指定したファイルを duckdb.connect()）を渡して使用します。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。

## 停止・Kill Switch の取り扱い
- 手動停止（run_monitoring / run_execution の両方が監視するファイル）
  - data/stop_requested.flag を置くとループが検知して終了します（両スクリプトがこのファイルを監視）。
- Kill Switch（自動的に ExecutionEngine を停止させる仕組み）
  - monitoring サブシステム内の条件（ドローダウン、ポジション上限等）に応じて data/kill.flag を書き込むことができます（KillSwitch クラス）。
  - ExecutionEngine は起動時や実行中に kill.flag を確認して動作を停止する設計です。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 により起動時に kill.flag を自動でクリアできます（本番では 0 を推奨）。

## 主要設定項目（環境変数）とデフォルト
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: (必須)
- KABU_API_PASSWORD: (必須)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 60（run_monitoring デフォルト）
- OPENAI_API_KEY: OpenAI を使う場合に必須（news_nlp / regime_detector）
- KILL_FLAG_CLEAR_ON_START: 0 or 1

## 開発者向けメモ
- Logging:
  - 共通の logging_setup.setup_logging を各起動スクリプトで呼んでおり、コンソール（stdout）とログファイル（logs/<app_name>.log）に出力します。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます（psutil に依存、権限がなければ警告を出してスキップ）。
- DB 初期化:
  - init_monitoring_db() は冪等的にテーブルとインデックスを作成し、軽微なマイグレーション（カラム追加）も行います。
- DuckDB:
  - 研究 / AI モジュールは DuckDB 接続を受け取り SQL でデータを集計します。prices_daily / raw_financials / raw_news 等のテーブルを想定しています。

## ディレクトリ構成（主要ファイル）
ここでは src/kabusys 以下の主な構成を抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（.env 自動読み込みロジック含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングプロセス起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        (存在を想定: trade 関連監視)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        (通知管理; 実装に依存)
  - execution/
    - execution_engine.py    (ExecutionEngine 本体)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - data/                     (実行時に生成されるデータディレクトリ)
  - logs/                     (ログ出力先)

（上記に示したファイルはいくつかを抜粋したものです。実際の実装にはさらに補助モジュールが含まれます。）

## よくある運用上の注意
- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知や kill_flag の設定を十分に確認してください（validate_config は live 時の追加チェックを行います）。
- .env は絶対に VCS（Git 等）にコミットしないでください。config_setup では .env ヘッダにその旨コメントが追加されます。
- OpenAI キーを使う機能はレート制限・コストが発生します。API の失敗は多くの場合フェイルセーフ（ゼロフォールバック）で処理されますが、運用前に十分にテストしてください。
- run_monitoring は監視用 DB（デフォルト data/monitoring.db）へ常に書き込みます。paper_trading と本番 DB の分離ポリシーを理解して運用してください。

---

不明点や README に追加したい情報（具体的な起動例、API の仕様、追加の運用手順など）があれば教えてください。必要に応じてサンプル .env やデプロイ手順（systemd / Supervisor / cron 例）も追記できます。
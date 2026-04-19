# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買システム KabuSys のコードベースです。以下はプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

## プロジェクト概要
KabuSys は取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、研究用ファクター計算、AI を使ったニュースセンチメント等を含む自動売買フレームワークです。ローカル開発からペーパートレード、本番運用まで想定した設計になっています。

主な特徴：
- ExecutionEngine（実売買/ペーパートレードに対応）
- Monitoring（システム稼働・データ鮮度・リスク監視、Kill Switch）
- Portfolio construction（候補選定、重み算出、ポジションサイジング）
- Research（ファクター計算、特徴量解析）
- AI モジュール（ニュース NLP / レジーム判定：OpenAI を使ったセンチメント評価）
- 各種ユーティリティ（ログ設定、プロセス優先度、.env ウィザード、設定検証）

## 機能一覧
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離。
  - run_monitoring.py: SystemMonitor を定期ポーリングして system_status / risk_logs / trade_logs 等を記録。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
- 設定管理
  - config_setup.py: 対話式ウィザードで .env を生成・更新。
  - validate_config.py: .env や config/*.yaml を事前検証。
  - config.Settings: 環境変数をラップして型安全に取得。
- 監視 (monitoring)
  - system_monitor.py: CPU/メモリ/Disk、Execution プロセスの PID、データ鮮度をチェックし DB に記録。
  - trade_monitor.py / risk_monitor.py: 注文滞留・約定異常・ドローダウン・ポジション上限を監視。
  - monitoring_engine.py: 各 Monitor を束ね、KillSwitch と AlertManager による通知／停止操作を実行。
  - kill_switch.py: 条件に応じて data/kill.flag を書き込み ExecutionEngine の停止をトリガー。
  - monitoring_db.py: SQLite を使った監視ログ永続化層（テーブル作成・マイグレーション含む）。
- ポートフォリオ（portfolio）
  - 候補選定、等分配／スコア加重、セクターキャップ、レジーム乗数、ポジションサイズ決定（単元丸め、集計キャップ処理含む）。
- 研究（research）
  - factor_research.py: モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB を用いる）。
  - feature_exploration.py: 将来リターン、IC、統計サマリー等。
- AI（ai）
  - news_nlp.py: raw_news を集約して OpenAI (gpt-4o-mini) で銘柄別センチメントを算出し ai_scores テーブルに保存。
  - regime_detector.py: ETF 1321 の MA200 乖離 と マクロニュースセンチメントを合成して市場レジームを決定し保存。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して稼働率、注文成功率、レイテンシ等の検証レポートを出力。

## 依存関係（主な Python パッケージ）
- Python 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config ファイルの検証を行う場合、任意）
- （必要に応じて）その他プロジェクトで使用する依存パッケージ

※requirements.txt は本リポジトリに含まれていない場合があるため、以下のパッケージをインストールしてください:
pip install duckdb psutil openai pyyaml

## セットアップ手順
1. リポジトリをクローンし作業ディレクトリに移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows の場合は .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. 初期設定 (.env) を作成
   - 対話式ウィザードで作成: `python -m kabusys.config_setup`
   - ウィザードの代わりに .env を手動で作成することも可能（.env.example を参照）
5. 設定の検証
   - `python -m kabusys.validate_config`
   - 警告もエラー扱いにしたい場合: `python -m kabusys.validate_config --strict`
6. 必要ディレクトリを作成
   - data/ と logs/ は自動作成される場合もありますが、権限等の問題で手動作成が必要なことがあります:
     - mkdir -p data logs

## 環境変数（重要なもの）
主要な環境変数（.env に設定する想定）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: execution モード。'development'|'paper_trading'|'live'（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — Monitoring は KABUSYS_ENV にかかわらずこの本番 sqlite_path を使用します
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db） — KABUSYS_ENV=paper_trading のとき ExecutionEngine が使用
- PAPER_FILL_MODE（paper_trading 用、'instant'|'partial'|'never'|'reject'。デフォルト 'instant'）
- LOG_LEVEL（'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'。デフォルト INFO）
- LOG_DIR（ログの保存先。デフォルト logs/）
- OPENAI_API_KEY（AI 機能を使う場合に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用、任意）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒。デフォルト 60）
- PID_FILE_PATH（ExecutionEngine の PID ファイル、デフォルト data/execution.pid）
- KILL_FLAG_PATH（Kill Switch 用 flag ファイル、デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか（0/1）。本番では 0 推奨）

注意点:
- config モジュールはプロジェクトルート（.git または pyproject.toml を探す）に基づいて .env 自動ロードを行います。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- run_monitoring は KABUSYS_ENV に関係なく settings.sqlite_path（本番用）を使って監視 DB を初期化／記録します。run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して DB を分離します。

## 使い方（起動例）
- ExecutionEngine を起動（通常）
  - KABUSYS_ENV=development（開発: 実運用発注なし）
    - `python -m kabusys.run_execution`
  - ペーパートレードで起動（MockBrokerClient を使用、DB は PAPER_TRADING_SQLITE_PATH）
    - `KABUSYS_ENV=paper_trading python -m kabusys.run_execution`
  - 本番で起動（注意して実行）
    - `KABUSYS_ENV=live python -m kabusys.run_execution`

- Monitoring を起動
  - デフォルト 60 秒間隔でポーリング
    - `python -m kabusys.run_monitoring`
  - ポーリング間隔を変更（例: 30 秒）
    - `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`

- 設定ウィザード（.env 作成）
  - `python -m kabusys.config_setup`

- 設定検証
  - `python -m kabusys.validate_config`
  - 厳密モード（警告も失敗扱い）: `python -m kabusys.validate_config --strict`

- ペーパートレード検証レポート生成
  - デフォルト DB を使う: `python -m kabusys.tools.paper_verification_report`
  - 期間指定: `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`
  - DB 指定: `python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db`

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要: OPENAI_API_KEY を .env に設定
  - これらはモジュール関数として呼び出すことを想定（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）
  - 直接起動用スクリプトはないため、独自ユーティリティやスケジューラから呼び出してください。

## 停止方法・Kill Switch
- 実行中プロセスを安全に停止するためのフラグ:
  - data/stop_requested.flag: run_monitoring / run_execution のループ内で検知されるとプロセスを終了（これらスクリプトが監視している停止フラグ）。
  - data/kill.flag: monitoring の KillSwitch により書き込まれ、ExecutionEngine の停止シグナルとして使用。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされるが、本番では推奨されません（0 推奨）。
- run_execution は起動時に stop flag が既に存在する場合は起動せず終了します。

## ログ
- logging_setup.setup_logging を各スクリプトが起動時に呼び出します。
- デフォルト:
  - コンソール出力: stdout
  - ファイル出力: logs/<app_name>.log（日次ローテーション、30 日保持）
- ログレベルは LOG_LEVEL（環境変数）または setup_logging の引数で指定可能。
- ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続します。

## 開発メモ / 注意点
- run_monitoring は監視用 DB を初期化するため init_monitoring_db を呼び出します。既存スキーマに新しいカラムがない場合はマイグレーション（ALTER TABLE ADD COLUMN）を行います。
- process_priority.set_process_priority が起動時に呼ばれ、可能な限りプロセスの nice/優先度を上げます（OS や権限により失敗する場合あり）。
- DuckDB を研究・AI 用の分析に利用します（prices_daily / raw_financials / raw_news テーブルを参照）。
- AI 呼び出しはレート制限や一時的な通信障害に対してリトライ実装あり。応答パースの堅牢性（JSON 抽出）を考慮して実装されています。
- research / portfolio / position sizing 等の関数群は純粋関数の設計が基本で、DB 参照のないものはユニットテストしやすくなっています。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイル・ディレクトリです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み・Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装がある場合)
  - execution/               — ExecutionEngine 関連（broker_factory, order_manager 等）
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
  - data/                    — 実行時に使用されるファイル（data/monitoring.db, data/paper_trading.db, data/kill.flag 等）

（実際のプロジェクトルートではさらに config/, scripts/ 等が存在する場合があります。）

## よくある操作例
- .env を作って検証してから監視・実行を始める（推奨ワークフロー）:
  1. `python -m kabusys.config_setup`
  2. `python -m kabusys.validate_config`
  3. `python -m kabusys.run_monitoring` （別ターミナルで）
  4. `python -m kabusys.run_execution`

- ペーパートレード検証レポート:
  - `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`

## 最後に / 開発者向けメモ
- 本リポジトリでは DB / ログ / フラグファイルのパスを環境変数で柔軟に切り替えられるよう設計されています。テスト環境や CI では各パスをテンポラリに変更して実行してください。
- AI 関連は API キーとコストに注意して運用してください。API の失敗に対してはフェイルセーフで継続する実装になっていますが、誤った運用はリスクを招きます。
- 変更を加える際はユニットテスト・静的解析を行い、特に実取引に関わるロジックは慎重に検証してください。

---

必要であれば README にサンプル .env 内容、実際のコマンド例（systemd unit や Docker での起動例）、テーブルスキーマの抜粋、よくあるトラブルシュート項目などを追加できます。どの内容を追加したいか教えてください。
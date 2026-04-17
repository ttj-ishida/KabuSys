# KabuSys

KabuSys は日本株の自動売買を想定した小規模なフレームワークです。  
監視（Monitoring）・発注実行（Execution）・ポートフォリオ構築・研究用ファクター計算・AI ベースのニュース NLP などのコンポーネントを備え、実運用（live）とペーパートレード（paper_trading）を明確に分離して扱えます。

バージョン: 0.1.0

---

## 概要

主な設計方針・特徴:

- 発注と監視はプロセス分離（ExecutionEngine / MonitoringEngine）。
- Paper trading（仮想ブローカー）と live（実ブローカー）を環境変数で切替可能。Paper trading は専用 SQLite DB に書き込むため本番 DB と分離されます。
- DuckDB を分析用 DB、SQLite を監視/オーダーログ用 DB として使用。
- .env ベースの設定管理、対話式ウィザード（config_setup）と設定検証ツール（validate_config）を提供。
- AI（OpenAI）を用いたニュースセンチメント評価と市場レジーム判定機能を実装（失敗時はフェイルセーフ）。
- 監視（CPU/メモリ/ディスク・データ鮮度・発注滞留・約定異常・ドローダウンなど）と、Kill Switch（フラグファイル）による自動停止をサポート。
- 研究用モジュール（ファクター計算・特徴探索）やポートフォリオ構築ユーティリティ（候補選定、重み、ポジション算出）を純粋関数として提供。

---

## 機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- 設定
  - python -m kabusys.config_setup : .env 対話式作成ウィザード
  - python -m kabusys.validate_config : .env / config/*.yaml の事前検証（--strict オプションあり）
- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、Execution の PID、データ鮮度チェック
  - TradeMonitor: 滞留注文の検出、約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視 + ダッシュボード更新
  - KillSwitch: 条件により stop flag（data/kill.flag）を書き込み ExecutionEngine を停止
  - AlertManager: （実装箇所はプロジェクト側で拡張想定）
- 実行（execution）
  - Broker クライアントファクトリ（Mock を含む）
  - OrderRepository / OrderManager / ExecutionEngine / RiskManager / Reconciler 等
- ポートフォリオ構築（portfolio）
  - 候補選定（select_candidates）
  - 等分配・スコア加重（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- 研究（research）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算・IC 計算・統計サマリー（calc_forward_returns, calc_ic, factor_summary）
- AI（ai）
  - ニュース NLP: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ユーティリティ
  - process priority / CPU affinity 設定（psutil ベース）

---

## セットアップ手順（ローカル開発向け）

以下は最小限の手順例です。プロジェクトに requirements.txt がある場合はそちらを優先してください。

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 最低依存: duckdb, psutil, openai
   - optional: PyYAML（validate_config が YAML を検証する場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. リポジトリルートで .env を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - あるいは手動で .env を作成（主要な環境変数は下記を参照）

4. 設定の検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合: python -m kabusys.validate_config --strict

5. データディレクトリの準備
   - 必要に応じて data/ ディレクトリを作成（sqlite/duckdb ファイルの親ディレクトリ）
   - Execution の PID / kill flag / stop flag 等は data/ 内に作られます

注意:
- OpenAI を使う機能を利用する場合は OPENAI_API_KEY を .env に設定してください。
- psutil でプロセス優先度を設定するため、特権や OS によって設定できない場合があります（警告ログのみ）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要／よく使う:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- PAPER_FILL_MODE: paper_trading 時の執行モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" はクリア。production では注意）
- PID_FILE_PATH / KILL_FLAG_PATH: 各種パス（デフォルトは data/ 内）

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある .env, .env.local を自動で読み込みます。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（主なコマンド・API）

CLI:
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict
- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - 起動前に data/stop_requested.flag が存在すると起動しません
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録
- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒）
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

プログラム API（ライブラリ呼び出し）:
- ポートフォリオ
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- 研究
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- AI
  - from kabusys.ai import score_news
  - 使用例: score_news(duckdb_conn, date(2026,4,1), api_key="...")  # returns 書き込んだ銘柄数
  - レジーム判定: from kabusys.ai import regime_detector; regime_detector.score_regime(duckdb_conn, date(2026,4,1), api_key="...")
- 監視 DB 操作
  - from kabusys.monitoring.monitoring_db import MonitoringDB
  - db = MonitoringDB(sqlite_conn); db.log_system_status(...)

Kill Switch 動作:
- RiskMonitor がドローダウンやポジション制限違反を検知すると MonitoringEngine の KillSwitch が data/kill.flag を書き込みます。
- ExecutionEngine は起動時 / ループ中にこのフラグを検出すると停止します。

停止 / 起動ガード:
- data/stop_requested.flag や data/kill.flag を用いて外部からプロセスを停止できます。
- 実運用では KILL_FLAG_CLEAR_ON_START の設定に注意（本番で自動クリアは危険）。

---

## ディレクトリ構成（抜粋）

リポジトリは src/kabusys 以下に実装がまとまっています。主なファイル/ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - execution/               — 発注関連（Engine, OrderManager, BrokerFactory など）
  - monitoring/
    - monitoring_db.py       — SQLite 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースセンチメント評価（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF MA）
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py    — psutil ベースの優先度 / CPU affinity ヘルパ
  - data/                    — 実行時に生成される（例: monitoring.db, kabusys.duckdb, *.pid, kill.flag）

（上記はコードベースの一部を抜粋したものです）

---

## 注意点 / 運用上のヒント

- Paper trading と live 環境は DB を分離してデータ汚染を防ぐ設計になっています。KABUSYS_ENV を正しく設定してください。
- OpenAI を利用する機能は API 呼び出しに課金が発生します。API キーの取り扱いに注意してください。
- プロセス優先度変更や CPU affinity は OS・権限に依存します。psutil が権限不足で例外を投げる場合は警告ログが出ますが処理は継続します。
- .env は絶対にリポジトリへコミットしないでください（config_setup にもその旨の注記あり）。
- DuckDB/SQLite のファイルパスは .env で変更可能です。バックアップ・保全を運用設計に組み込んでください。
- 重ねて、KILL_FLAG_CLEAR_ON_START を本番で "1" にするのは推奨されません（Kill Switch が意図せずクリアされるため）。

---

README はここまでです。実際のデプロイ・運用ルール（監視通知先、ブローカーの資格情報管理、バックテスト・CI、監査ログ保存方針など）は別途ドキュメント化してください。必要であれば、README に含めるデプロイ手順や例の .env テンプレート、requirements.txt の推奨セットを作成します。どの追加情報が必要か教えてください。
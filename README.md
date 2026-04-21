# KabuSys

日本株向けの自動売買 / 研究フレームワーク（KabuSys）  
このリポジトリはシグナル生成・ポートフォリオ構築・注文実行・監視・研究ユーティリティを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール化された自動売買システム／研究ツール群です。

- リサーチ機能（ファクター計算、将来リターン、IC 計算）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- 実行エンジン（ExecutionEngine）とブローカークライアント抽象化（paper/live 切替）
- 監視（System / Trade / Risk モニタ）と Kill Switch
- AI 補助（ニュース NLP によるセンチメント評価、市場レジーム判定）
- ユーティリティ：.env ウィザード、設定検証、検証レポート生成など

設計方針の特徴：
- DuckDB（分析用）と SQLite（軽量ログ／監視用）を併用
- Paper Trading（完全分離された SQLite）をサポート
- OpenAI（gpt-4o-mini 想定）との連携機能（API キー必須）
- フェイルセーフ設計（API エラーはスキップ、冪等な DB 書き込みなど）

---

## 主な機能一覧

- 環境設定／検証
  - 対話式 .env 作成・更新: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 実行系
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV が `paper_trading` のときは MockBroker を使用し、paper DB（data/paper_trading.db）に記録
- 監視系
  - SystemMonitor のポーリングループ起動: src/kabusys/run_monitoring.py
    - 環境に依らず本番 sqlite_path を監視用に使用
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 研究 / ファクター
  - ファクター計算（Momentum, Volatility, Value）: kabusys.research
  - 特徴量解析・IC 計算: kabusys.research.feature_exploration
- ポートフォリオ構築
  - 候補選定 / 重み計算 / ポジションサイズ決定: kabusys.portfolio
- AI 機能
  - ニュースを LLM で評価して ai_scores に格納: kabusys.ai.news_nlp.score_news
  - マクロ記事＋ETF MA 乖離で市場レジーム判定: kabusys.ai.regime_detector.score_regime
- 監視永続化層
  - MonitoringDB: SQLite を使ったテーブル定義と読み書きユーティリティ
- ユーティリティ
  - paper_trading 検証レポート生成ツール: python -m kabusys.tools.paper_verification_report

---

## 前提 / 依存関係

推奨 Python バージョン: 3.10 以上（PEP 604 の型注釈などを使用）

必須 / 推奨パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証のため、無くても動くが警告が出る）
- （その他：プロジェクト固有のライブラリ・ブローカークライアント依存）

インストール例:
- 仮想環境を作成・有効化してから:
  - pip install duckdb psutil openai PyYAML

※ requirements.txt が存在する場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン、仮想環境作成・有効化
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env 作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードに従って必要な環境変数を入力します（J-Quants トークン、kabu API パスワード、LOG_LEVEL など）
   - もしくは .env を手動作成（.env.example を参考に）

4. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は指摘に従って修正（--strict を付けると警告も失敗扱いになります）

5. データディレクトリの準備（必要に応じて）
   - デフォルトの DB / ログパスは data/ や logs/。これらは自動作成される場合もありますが、権限に応じて作成してください。

6. OpenAI を使う機能を使う場合
   - 環境変数 OPENAI_API_KEY を設定するか、API キーを関数呼び出し側に渡します。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
    - --strict を付けると警告も exit 1 扱い
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、paper DB（デフォルト: data/paper_trading.db）を使用して MockBroker で動作
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中は data/execution.pid が作成される（Settings.pid_file_path）
    - 停止するには stop フラグ（後述）やプロセスを終了する
- 監視プロセス起動
  - python -m kabusys.run_monitoring
    - 監視ループは MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60）
    - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用
    - 停止フラグ: data/stop_requested.flag を作成するとループが終了する
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

### 環境変数（主要）
（config_setup で入力するものが中心）

- KABUSYS_ENV: execution モード（development / paper_trading / live） — デフォルト development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

その他の詳細設定は .env ウィザードをご参照ください。

---

## 停止／Kill 機構

- run_execution / ExecutionEngine 停止シグナル:
  - data/kill.flag: KillSwitch により生成される停止フラグ。ExecutionEngine 起動時に Settings.kill_flag_clear_on_start=1 の場合は自動クリアされる（設定に注意）。
  - data/stop_requested.flag: 起動中の run_execution/run_monitoring に対する即時停止フラグ（スクリプトはこのファイルを検知して終了します）。
- KillSwitch は RiskMonitor の結果（ドローダウンやポジション数超過など）で kill.flag を作成します。kill.flag が存在すると ExecutionEngine に停止指示が出されます（冪等）。

---

## ロギング・プロセス優先度

- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name=...)
  - stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）を設定
  - LOG_DIR / LOG_LEVEL を使用
- 起動スクリプトは set_process_priority("high") を呼び出し、優先度を高めます（psutil を用いて OS に合わせて設定）。

---

## 開発時の注意点 / ヒント

- KABUSYS_ENV の切替:
  - development: 開発用（発注なし想定）
  - paper_trading: 発注はモック、paper DB にのみ記録（本番 DB と分離）
  - live: 本番
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル・カラムを作成します（起動時に呼ぶことで古い DB をアップデート）
- OpenAI の呼び出し:
  - news_nlp / regime_detector は API エラー時にリトライ/フォールバックする設計ですが、API キーは必須です。テスト時は _call_openai_api をモックできます。
- テスト実行:
  - MonitoringEngine には run_once() があり、ユニットテストで各 Monitor を 1 回だけ呼ぶのに便利です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                   — 環境変数 / 設定管理
- config_setup.py             — 対話式 .env ウィザード
- validate_config.py          — 設定検証 CLI
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — SystemMonitor ポーリング起動スクリプト

package modules:
- ai/
  - news_nlp.py               — ニュース NLP によるスコアリング
  - regime_detector.py        — 市場レジーム判定
- monitoring/
  - monitoring_db.py          — SQLite 永続化層
  - system_monitor.py         — システム / データ鮮度監視
  - trade_monitor.py          — （trade 関連監視 — 実装参照）
  - risk_monitor.py           — ドローダウン / ポジション上限監視
  - kill_switch.py            — kill.flag の作成 / 管理
  - monitoring_engine.py      — 各モニタを束ねるエンジン
  - alert_manager.py          — アラート通知（実装に応じて）
- execution/
  - execution_engine.py       — ExecutionEngine（core）
  - broker_factory.py         — BrokerClientFactory（paper/live 切替）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py      — 候補選定・重み計算
  - position_sizing.py        — 株数計算、資金制約処理
  - risk_adjustment.py        — セクター制限・レジーム乗数
- research/
  - factor_research.py        — Momentum/Volatility/Value 計算
  - feature_exploration.py    — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - logging_setup.py          — 共通ログ設定
  - process_priority.py       — プロセス優先度 / CPU affinity
- monitoring_db, 各種ユーティリティや DB インターフェース

（上記はコードベースにおける主要ファイルと機能の抜粋です。実際のファイル一覧はリポジトリを参照してください。）

---

## よくある操作例

- .env を作成して検証する
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 監視プロセスをデバッグ実行（1 回だけ）
  - import して MonitoringEngine.run_once() を呼ぶテストスクリプトを作る

- Paper Trading レポートを期間指定で出す
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ライセンス / 責任範囲

- 本リポジトリは自動売買の研究・実装を支援するものであり、実際の売買に用いる場合は十分なテストと監査を行ってください。
- live 環境での設定ミスや API キー管理の不備は重大なリスクを招くため、KABUSYS_ENV=live に設定する前に必ず validate_config を実行し、運用手順を確認してください。

---

README の補足や、実運用向けのデプロイ手順（systemd ユニット、コンテナ化、監視設定テンプレートなど）が必要であれば教えてください。具体的な運用環境に合わせた例を追加します。
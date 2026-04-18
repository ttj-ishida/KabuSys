README
======

概要
----
KabuSys は日本株向けの自動売買プラットフォームの一部を切り出したコードベースです。本リポジトリには以下の主要機能が含まれます。

- 発注エンジン (ExecutionEngine) の起動スクリプト
- 監視（System / Trade / Risk）コンポーネントおよび監視ループ
- .env 対話式セットアップ・設定検証ツール
- ペーパートレード用検証レポート生成ツール
- ポートフォリオ構築・ポジションサイズ計算・リスク調整ロジック
- リサーチ用ファクター計算・特徴量解析モジュール
- ニュース NLP / レジーム判定（OpenAI を利用）

主な特徴
---------
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）を環境切替でサポート
- 監視用 SQLite DB を使った永続化（system_status, trade_logs, risk_logs, positions, dashboard）
- DuckDB を使ったファクター計算・リサーチ処理
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価および市場レジーム推定（APIキー必要）
- .env 対話ウィザード / 設定検証 CLI を備え、起動前のチェックが容易
- Paper Trading と本番 DB を分離（paper_trading 用 DB: data/paper_trading.db）

動作前提（要件）
----------------
- Python 3.9+
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を使う場合）
- SQLite（標準ライブラリで同梱）
- ネットワークアクセス（kabuステーション API / OpenAI を利用する場合）

インストール（例）
-----------------
1. 仮想環境（推奨）を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

（注）requirements.txt がないため、プロジェクトの利用箇所に応じて必要なライブラリを追加してください。

設定（.env）
-----------
1. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
   - 対話形式で J-Quants トークン、kabu API パスワード、DB パスなどを設定できます。
   - 生成された .env は決して Git にコミットしないでください。

2. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

主要な環境変数（抜粋）
---------------------
必須（実行に必須なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

運用関連（デフォルトあり）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite（monitoring） — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading） — デフォルト: data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — デフォルト: INFO
- OPENAI_API_KEY: OpenAI を使う場合に必要（news_nlp/regime_detector）

監視系の制御
- KILL_FLAG_PATH: data/kill.flag のパス（既定: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

Paper Trading 固有
- PAPER_FILL_MODE: MockBrokerClient の約定挙動 ("instant" | "partial" | "never" | "reject")
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB

使い方（主要スクリプト）
-----------------------

1) 実行エンジン（ExecutionEngine）起動
- ローカルで本番/ペーパーの起動は Settings に依存します。基本的に:
  - python -m kabusys.run_execution

- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag があれば起動せず終了します。
  - 起動後は execution.pid（デフォルト data/execution.pid）を書きます。終了時に PID ファイルを削除します（内部ロジック依存）。

2) 監視ループ起動
- python -m kabusys.run_monitoring
- 動作:
  - Settings から sqlite_path（監視 DB）を参照して監視処理を実行します（監視処理は常に production sqlite_path を使用する設計）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（例: MONITOR_POLL_INTERVAL=30）。
  - data/stop_requested.flag の存在でループを正常終了します。

3) 設定検証（起動前確認）
- python -m kabusys.validate_config
- --strict を付けると警告で exit(1) となります。

4) .env 対話ウィザード
- python -m kabusys.config_setup

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- オプション:
  - --from YYYY-MM-DD
  - --to YYYY-MM-DD
  - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

AI 関連
- ニュース NLP（ai.news_nlp.score_news）およびレジーム判定（ai.regime_detector.score_regime）は OpenAI API キー（OPENAI_API_KEY）を必要とします。
- モデルは gpt-4o-mini を想定しており、API へのリトライ・バリデーションロジックが組み込まれています。

監視・停止フラグ
----------------
- kill.flag (Settings.kill_flag_path / デフォルト data/kill.flag)
  - KillSwitch（監視）により条件を満たすと書かれる。ExecutionEngine はこのフラグ検知で停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアします（本番環境では 0 を推奨）。

- stop_requested.flag (data/stop_requested.flag)
  - run_execution / run_monitoring はこのファイルの存在を見てループを終了／起動を抑止します。

ディレクトリ構成（抜粋）
-----------------------
以下は主要ファイルを示した簡易ツリー（src/kabusys をルートとする）:

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理
  - config_setup.py        — .env 対話ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py    — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py     — SQLite schema + MonitoringDB ラッパ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py    — システム状態・データ鮮度監視
    - trade_monitor.py     — 注文滞留・約定異常監視
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - alert_manager.py     — （アラート送信管理：未完／省略箇所あり）
    - kill_switch.py       — kill.flag の書き込み
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py   — 株数決定・投下資金スケール
    - risk_adjustment.py   — セクター上限・レジーム乗数
  - research/
    - factor_research.py   — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity

実装上の注意点 / 運用メモ
-----------------------
- monitoring は環境にかかわらず Settings.sqlite_path（監視 DB）を使用する仕様になっています。ペーパートレード DB は run_execution の中で settings.is_paper によって切り替えられます。
- .env は OS の環境変数を破壊しないよう保護して読み込まれる実装です。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を利用するスクリプトは API 利用失敗時にフォールバック（スコア 0.0 や処理スキップ）する設計で、フェイルセーフを重視しています。
- psutil によるプロセス優先度・CPU affinity の設定は OS 権限によって失敗することがあります。その場合はログに WARN が出て処理は継続します。

トラブルシューティング
----------------------
- DuckDB / sqlite ファイルの親ディレクトリが存在しない警告が出る場合、起動時に自動作成されることがありますが、手動で data/ ディレクトリなどを作成しておくと安心です。
- OpenAI 利用時に JSON パースエラーが出る場合、API のレスポンスが想定外である可能性があります。ログを確認してモデルの出力・ネットワーク状態を確認してください。
- 設定の検証は validate_config.py で実行可能です。起動前に必ず確認してください（特に KABUSYS_ENV=live の場合は警告を確認）。

ライセンス・バージョン
---------------------
- パッケージのバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

最後に
------
この README はコードベース内にある説明コメント・ドキュメント文字列に基づいて作成しています。詳細な運用手順や本番移行手順（証券会社の API キー管理や資金管理など）は別途運用マニュアルを整備してください。何か追加でドキュメント化したい箇所があれば教えてください。
KabuSys — 日本株自動売買システム
=============================

本ドキュメントはこのコードベースの概要、機能、セットアップ方法、主要な使い方、およびディレクトリ構成をまとめた README です。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買 / 研究基盤です。次の主要機能を持ちます。

- 発注エンジン（ExecutionEngine）: ブローカークライアントを通じた発注管理、リスク管理、注文再構成
- 監視 (Monitoring): システム状態・データ鮮度・注文滞留・リスク監視、Kill Switch
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター上限適用
- リサーチ: ファクター計算（モメンタム、バリュー、ボラティリティ）や特徴量探索（IC 等）
- AI モジュール: ニュースセンチメント（OpenAI）を用いた銘柄スコアリング、レジーム判定
- ユーティリティ: 環境設定ウィザード、設定検証、Paper Trading 検証レポート生成

主な特徴
--------
- 本番/開発/ペーパートレードを環境変数 KABUSYS_ENV で切替可能（development / paper_trading / live）
- Paper Trading モードでは MockBrokerClient を使い、本番 DB と分離（デフォルト data/paper_trading.db）
- DuckDB を分析用 DB、SQLite を監視・ログ用 DB に使用
- OpenAI（gpt-4o-mini）連携によるニュース NLP とマクロセンチメント（API 呼び出しはオプション）
- 監視コンポーネントは kill.flag で ExecutionEngine を安全に停止可能
- 自動 .env 読み込み機能（プロジェクトルートに .env / .env.local があればロード）

前提 / 依存パッケージ
-------------------
推奨: Python 3.10+（型ヒントで Union 表記などを使用）
主な依存ライブラリ:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の検証を行う場合にオプションで使用）

インストール例（venv 推奨）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 必要ライブラリをインストール
  - pip install duckdb psutil openai pyyaml

設定（.env の作成）
-----------------
1. 対話式ウィザードで .env を作成する（推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabuステーションのパスワード等、基本的な環境変数を生成します。
2. 自動ロードについて
   - デフォルトでプロジェクトルートの .env / .env.local を自動で読み込みます。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（代表）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant | partial | never | reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

設定検証
-------
作成した .env や config/*.yaml の基本検証は次を実行：
- python -m kabusys.validate_config
--strict オプションを付けると警告も失敗（exit code 1）扱いになります。

使い方（主要スクリプト）
------------------------

1) 監視ループの起動（Monitoring）
- スクリプト: src/kabusys/run_monitoring.py
- 動作: SystemMonitor を定期ポーリングして監視ログを SQLite に保存する
- 起動例:
  - python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト: 60
- 停止:
  - プロジェクトルート/data/stop_requested.flag を作成するとループ終了
  - kill.flag は Execution 停止用（KillSwitch により作成される）

2) ExecutionEngine（発注エンジン）の起動
- スクリプト: src/kabusys/run_execution.py
- 動作:
  - Settings に従って DB 接続や broker クライアントを生成し ExecutionEngine を起動
  - KABUSYS_ENV=paper_trading の場合は mock broker を使用し paper_trading 用 SQLite を使用する（本番 DB と分離）
- 起動例:
  - python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成するとエンジン停止シグナルを送る
  - ExecutionEngine が実行中は data/execution.pid に PID を書きます

3) Paper Trading 検証レポート生成
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

4) AI 関連（ニュース NLP / レジーム判定）
- ニューススコアリング: kabusys.ai.score_news（内部で OpenAI を使用）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - 書き込み先: DuckDB 内の ai_scores テーブル
- 市場レジーム評価: kabusys.ai.regime_detector.score_regime
  - 同様に OpenAI API キーが必要
- これらはライブラリ関数としての利用が想定されています（unit-test 等では _call_openai_api をモック可能）

運用上の注意
------------
- Paper Trading モードは本番 DB と発注を完全に分離します。Paper 用 DB は PAPER_TRADING_SQLITE_PATH で指定できます。
- kill.flag / stop_requested.flag:
  - KillSwitch は条件に応じて data/kill.flag を書き、ExecutionEngine に停止シグナルを送る仕組みがあります。
  - run_monitoring/run_execution は data/stop_requested.flag を検出して終了します。
- PID ファイル: run_execution は data/execution.pid を作成します。SystemMonitor はその PID の存在を確認してプロセス稼働を判断します。
- OpenAI 呼び出し: ネットワークや API レート制限に対しリトライとフォールバック（スコア 0.0）を実装しています。API の呼び出し失敗で全体の処理を止めない設計です。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存テーブルのスキーマ差異を検出し一部カラム追加（冪等）を行います。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主なファイルと役割の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動
  - run_execution.py         — ExecutionEngine 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI連携）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）

  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB アクセス層
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常チェック
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 制御
    - monitoring_engine.py   — 各 Monitor を統合してループ実行
    - alert_manager.py       — （アラート送信ロジック; ファイル末尾に未完の可能性あり）

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - position_sizing.py     — 発注株数決定・上限制御
    - __init__.py

  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py

  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading の Pass/Fail レポート生成
    - __init__.py

その他トップレベル（プロジェクトルート想定）
- .env, .env.local          — 環境変数ファイル（.gitignore 推奨）
- config/*.yaml            — 各種設定テンプレート（存在確認・検証に使用）
- data/                    — デフォルトの DB・フラグ・pid ファイル置き場
  - kabusys.duckdb (デフォルト)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading モード用)
  - kill.flag / stop_requested.flag / execution.pid

よくある操作例
--------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - 環境変数で間隔を上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

テスト・開発時のヒント
---------------------
- AI 呼び出しを行う関数（news_nlp._call_openai_api 等）は unittest.mock.patch で差し替え可能です。
- .env の自動ロードはプロジェクトルート検出（.git または pyproject.toml）に依存します。配布後やテストで不要であれば KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB 周りはデフォルトで data/ 以下に作成されます。適宜環境変数でパスを変更できます。
- プロセス優先度設定は psutil の権限に依存します。権限不足時は警告が出力されます。

免責・今後の拡張
----------------
- 本リポジトリの一部は実運用向けの保守・拡張対象（例: 銘柄別 lot_size の導入、価格フォールバック処理、alert_manager の詳細実装など）を前提としています。
- 実際の資金運用を行う場合は、十分なテスト・監査を行ってください。

問い合わせ
----------
コード内の docstring や各モジュールのコメントを参照してください。README に追記してほしい箇所や、特定ファイルの詳細説明が必要であれば追加で指示ください。
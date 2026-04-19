KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアモジュール群です。
主要機能は戦略評価・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・
AI を使ったニュース解析などを含みます。本 README はコードベースの概要・セットアップ・起動方法を日本語でまとめたものです。

目次
----
- プロジェクト概要
- 主な機能一覧
- 必要条件 / 依存ライブラリ
- セットアップ手順
- 実行・使い方
- 主要環境変数・設定
- ディレクトリ構成（抜粋）
- 注意事項 / 運用のヒント

プロジェクト概要
----------------
KabuSys は以下の要素から成る自動売買プラットフォームのライブラリ／実行ユニット群です（抜粋）:

- 戦略・研究（research）: ファクター計算・特徴量解析・IC 計測などの研究用ユーティリティ。
- ポートフォリオ構築（portfolio）: 候補選定、配分重み計算、ポジションサイズ計算、セクター上限やレジーム補正。
- 発注系（execution）: ブローカクライアント抽象化、ExecutionEngine、オーダー管理、リスク管理（コードベースに依存するが一部は本 README のコードに含まれる）。
- 監視（monitoring）: システム稼働監視、取引ログ監視、ドローダウン監視、Kill Switch（flagファイルによる実行系停止）など。
- AI（ai）: OpenAI を用いたニュース NLP（センチメント評価）や市場レジーム判定。
- ツール（tools）: ペーパートレード検証レポート生成などのユーティリティスクリプト。
- 共通ユーティリティ（utils）: ロギング設定、プロセス優先度設定などの補助。

主な機能一覧
-------------
- 環境設定ウィザード: python -m kabusys.config_setup で .env を対話的に作成可能
- 設定検証 CLI: python -m kabusys.validate_config で .env と config/*.yaml の事前検証
- 監視デーモン: run_monitoring.py — システム稼働監視と Kill Switch 評価（MONITOR_POLL_INTERVAL で間隔調整可）
- 実行エンジン起動: run_execution.py — ExecutionEngine をスレッドで起動、paper_trading は専用 DB を使用
- Paper Trading 検証レポート: tools/paper_verification_report.py でペーパートレード履歴の集計と合否判定
- AI ニュース解析: ai/news_nlp.py（OpenAI を用いた銘柄別ニュースセンチメント）
- レジーム判定: ai/regime_detector.py（MA200 とマクロセンチメントの合成で bull/neutral/bear 判定）
- ポートフォリオ構築: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- 監視 DB 層: monitoring/monitoring_db.py（SQLite に監視・取引ログ等を永続化）
- ロギング: utils/logging_setup.py（日次ローテート + コンソール出力設定）
- プロセス優先度・CPU affinity ユーティリティ: utils/process_priority.py

必要条件 / 依存ライブラリ（代表）
--------------------------------
（実行環境に合わせて適宜インストールしてください）
- Python 3.8+（型注釈や一部機能に依存）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の詳細な YAML 検証を行う場合）
- sqlite3（標準ライブラリ）
※ requirements.txt は本リポジトリに含まれていない場合があるため、上記を pip で個別インストールしてください。

例:
pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローン / コピー
   - プロジェクトルートに移動します（.git または pyproject.toml が存在する場所がプロジェクトルートとして自動検出されます）。

2. Python 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 生成した .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合は --strict を付ける（例: CI での検証）。

6. データディレクトリと初期 DB
   - デフォルトでは以下のパスが使われます（.env で上書き可能）:
     - data/monitoring.db（SQLite 監視 DB）
     - data/paper_trading.db（ペーパートレード用 DB）
     - data/kabusys.duckdb（分析用 DuckDB）
   - 起動スクリプトは必要に応じてディレクトリを作成しますが、権限などを事前に確認してください。

実行・使い方
-------------
主なエントリポイント（モジュールとして実行）:

- 監視ループを起動（常駐）:
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - 監視は .env の KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは単一に集約）。

- 実行エンジンを起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録（本番 DB と分離）。
  - 実行中は data/execution.pid に PID が書かれ、停止は data/stop_requested.flag などで検知されます。

- .env 作成ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db で別の DB ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI スコアリング（プログラム利用例）
  - ai.news_nlp.score_news(conn, target_date, api_key=...) を呼び出す（DuckDB 接続を渡す）
  - OPENAI_API_KEY を .env に設定しておくと api_key を省略できます。

主要環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパー向け SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定モード: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

デフォルトファイル / フラグ（運用上のポイント）
--------------------------------------------
- data/kill.flag — Kill Switch により Execution を停止するための旗（存在すると停止をトリガー）
- data/stop_requested.flag — run_monitoring/run_execution 停止を外部からリクエストするための旗
- data/execution.pid — ExecutionEngine の PID（run_execution が作成）
- ログディレクトリ: logs/（utils.logging_setup により日次ローテートされる。環境変数 LOG_DIR で変更可）

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 配下の主なモジュールと役割（実際のツリーはリポジトリ内のファイルに合わせてください）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視 DB 永続化
    - system_monitor.py      — システム・データ鮮度チェック
    - trade_monitor.py       — （取引監視：滞留注文・約定異常など）※参照箇所あり
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — フラグファイルによる停止判定・書込
    - monitoring_engine.py   — 各 Monitor を束ねる実行エンジン
    - alert_manager.py       — アラート送信（LINE 等）※実装参照
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算・スケールダウンロジック
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — forward returns, IC, summary 等
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — ロギング初期化
    - process_priority.py    — プロセス優先度・CPU affinity

注意事項 / 運用のヒント
---------------------
- KABUSYS_ENV=live を設定する場合はすべての設定（LINE 通知、kill flag の運用等）を十分に検証してください。validate_config は live 環境に対して注意喚起を行います。
- .env は機密情報（API トークン・パスワード）を含むため、絶対にバージョン管理に含めないでください。
- AI 機能を使う場合、OpenAI のリクエスト制限・課金に注意してください。news_nlp/regime_detector はリトライやフォールバックを組み込んでいますが、実運用前に挙動を確認してください。
- run_execution は paper_trading モードをサポートしており DB を分離するため安全にテストができます。まずは paper_trading 環境で十分に検証してください。
- ロギングは utils.logging_setup を使って統一しているため、起動スクリプトの最初に setup_logging(app_name=...) を呼ぶことを推奨します。
- MONITOR_POLL_INTERVAL 等の簡易な調整は環境変数で可能です。0 以下や不正な値はデフォルトにフォールバックします。

追加のドキュメント / 参照
------------------------
- 各モジュール頭部の docstring に実装方針・設計メモが含まれています。実装や運用の詳細はそれらを参照してください。
- config/*.yaml やさらなる運用手順はリポジトリ内の scripts / docs にある可能性があります（ない場合は設計ドキュメントを参照）。

おわりに
--------
この README はコードベースの主要機能と運用開始までの手順を簡潔にまとめたものです。実運用に移す前に、環境変数・DB パス・ログの出力先、Kill Switch の動作、AI キーやブローカ接続の挙動を十分にテストしてください。必要であれば実行上のユースケース（デプロイ用 systemd / Dockerfile / コンテナ構成）についても追記できます。要望があればその内容に合わせたドキュメントを作成します。
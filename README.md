README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームです。本リポジトリは以下の主要機能を提供します。

- 実売買（ExecutionEngine）・ペーパートレード実行（MockBroker）  
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch（停止フラグ）  
- ポートフォリオ構築（銘柄選定・重み付け・株数算出）  
- ファクター計算・特徴量探索（Research / DuckDB ベース）  
- ニュースの NLP スコアリング（OpenAI を利用したセンチメント評価）  
- Paper Trading の検証レポート生成ツール

特徴
----
- 設定は .env ファイル（または環境変数）で管理。対話型ウィザードで .env を生成可能（kabusys.config_setup）。
- 設定検証ツール（kabusys.validate_config）で起動前チェックが可能。--strict モードで警告を FAIL 扱いに。
- 実行と監視は別プロセス設計。監視は独立した SQLite DB にログを残す（data/monitoring.db がデフォルト）。
- Paper Trading は本番 DB と完全分離（data/paper_trading.db を利用）。
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントやマクロセンチメントで市場レジーム判定が可能（API キー必要）。
- ログはコンソール＋日次ローテートファイル（logs/）で一元管理。

前提・依存
------------
必須（最低限）
- Python 3.9+
- pip パッケージ:
  - duckdb
  - psutil
  - openai
（開発環境や追加機能により他パッケージが必要になります。PyYAML は config/*.yaml の検証に用いられますが任意）

推奨
- SQLite（Python 組込みモジュールで利用可）
- ネットワークアクセス（kabuステーション API、J-Quants、OpenAI を使う場合）

セットアップ手順
----------------

1. リポジトリをクローン／チェックアウト
   - 通常の git clone の手順でクローンします。

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb psutil openai
   - 開発で YAML 検証を使う場合: pip install PyYAML

4. .env ファイルの作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話に従い J-Quants トークン、kabu API パスワード、KABUSYS_ENV などを入力します。
   - あるいは手動で .env を作成（.env.example がある場合はそれを参照）。

5. 設定検証
   - python -m kabusys.validate_config
   - 本番前は厳格チェック:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
----------------------
重要なものを記載します。詳しくは config_setup の項目説明を参照してください。

- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABUSYS_ENV           : 実行環境（development / paper_trading / live）デフォルト: development
- OPENAI_API_KEY        : OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START : 起動時に Kill Flag を自動クリアするか（0/1。production では 0 推奨）
- PAPER_FILL_MODE       : ペーパートレードの約定モード（instant/partial/never/reject）

使い方
------

基本的な起動・ツールの例を示します。

- ExecutionEngine（エンジン）起動
  - python -m kabusys.run_execution
  - 実運用モードは KABUSYS_ENV=live、ペーパートレードは KABUSYS_ENV=paper_trading（この場合 MockBroker を使用し、paper_db に記録されます）。
  - 起動時に data/stop_requested.flag が存在すると起動を行いません。
  - 実行はデーモン化や systemd / supervisor 経由で管理することを想定します。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化します（冪等）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB ファイルを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL に）:
    - python -m kabusys.validate_config --strict

- AI / 研究関連の関数呼び出し（ライブラリとして）
  - Python スクリプトや REPL からインポートして利用します。
    例:
      from kabusys.ai.news_nlp import score_news
      # DuckDB 接続を構築して score_news(conn, target_date, api_key=...) を呼ぶ

注意事項 / 運用上のポイント
--------------------------
- Paper Trading は本番データベースと完全分離する設計になっています（KABUSYS_ENV=paper_trading を利用）。
- 停止フラグ（Kill Switch）
  - data/kill.flag: ExecutionEngine に停止指示を出すためのファイル（KillSwitch が検出して停止）。
  - data/stop_requested.flag: run_monitoring / run_execution の起動ルーチンで使用される停止フラグ（デプロイ運用用）。
- ログ
  - ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。LOG_DIR 環境変数で変更可能。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は必要なテーブルやカラムを冪等に作成・追加します（簡易マイグレーションを含む）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要なモジュール構成（抜粋）です。

- kabusys/
  - __init__.py                — パッケージ定義（バージョン等）
  - config.py                  — 環境変数 / .env の自動読み込みと Settings クラス
  - config_setup.py            — .env 対話型ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py       — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（schema + helper）
    - system_monitor.py        — システム状態・データ鮮度チェック
    - trade_monitor.py         — 発注関連監視（滞留注文・約定異常など）※実装あり
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag の書込み／評価
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - alert_manager.py         — アラート送信（LINE など）※実装あり
  - portfolio/
    - portfolio_builder.py     — 候補選定、重み付け
    - risk_adjustment.py       — セクターキャップ、レジーム乗数
    - position_sizing.py       — 株数算出（単元丸め・スケーリング）
  - research/
    - factor_research.py       — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py   — 将来リターン計算、IC、統計サマリー
  - utils/
    - logging_setup.py         — ログ初期化ユーティリティ
    - process_priority.py      — プロセス優先度・CPU affinity 設定ユーティリティ
  - data/                      — データファイル（デフォルトパス: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）
  - logs/                      — ログ出力先（デフォルト）

開発者向けメモ
---------------
- DuckDB 接続を受け取り SQL と Python を組み合わせてデータ処理を行う設計です。research モジュールは prices_daily / raw_financials 等のテーブル前提で動作します。
- OpenAI 呼び出し部分は外部への API 通信を伴うため、テストでは _call_openai_api をモックする想定です（score_news, regime_detector 内で注記あり）。
- 設定の自動読み込みはプロジェクトルートを .git または pyproject.toml から検出して行います（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

ライセンス・貢献
----------------
- この README に示した内容はコードベースのコメントを元に要約しています。実際のライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING ファイルを参照してください。

問題や質問
----------
- 実行時のエラーや環境設定に関する質問があれば、実行コマンドと環境変数の設定（機密情報は除く）を添えて問い合わせてください。
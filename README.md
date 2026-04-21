KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／リサーチ／監視コンポーネント群を含むライブラリ兼起動スクリプト群です。  
本 README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
KabuSys は以下の役割を持つモジュール群で構成された小規模な自動売買システムです。

- 注文執行エンジン（ExecutionEngine）起動スクリプト
- システム監視・アラート（Monitoring）コンポーネント
- ポートフォリオ構築・ポジションサイズ決定ロジック（純粋関数）
- リサーチ／ファクター計算（DuckDB を用いる）
- AI（LLM）を用いたニュースセンチメント評価・レジーム判定（OpenAI 経由）
- 設定ウィザード (.env 生成) と設定検証ツール
- ペーパートレーディング用の分離DBと検証レポート生成ツール

特徴（機能一覧）
----------------
- 実行モード切替：KABUSYS_ENV により development / paper_trading / live を切替可能
  - paper_trading 時は MockBrokerClient を使い paper_trading 用 DB に記録（本番 DB と分離）
- 設定管理：
  - .env の自動読み込み（プロジェクトルート検出）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 起動前検証ツール（python -m kabusys.validate_config）
- ロギング：stdout と日次ローテートファイル（logs/<app>.log）を統一的に設定
- プロセス優先度設定（高優先度へ設定するユーティリティ）
- 監視：
  - system_monitor: CPU/メモリ/Disk、データ鮮度、実行プロセスの生存
  - risk_monitor: ドローダウン、ポジション上限監視、ダッシュボード永続化
  - monitoring_engine: 各 Monitor を束ねて定期実行・アラート／Kill Switch 評価
- ポートフォリオ構築（候補選定、等重・スコア重み、リスク調整、ポジションサイズ計算）
- リサーチ：Momentum / Volatility / Value 等のファクター計算、将来リターン、IC 計算
- AI 統合：OpenAI を利用したニュースセンチメント（ai_scores）と市場レジーム判定
- ツール：paper_trading の検証レポート生成スクリプト

依存関係（代表）
----------------
コード上で利用している主要パッケージ（環境によって変動）：
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config 検証でオプション）
- （標準ライブラリ: sqlite3, threading, logging, etc.）

pip で最低限インストールする例：
pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローン／チェックアウト
2. Python 仮想環境作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール:
   pip install duckdb psutil openai PyYAML
   ※ requirements.txt がある場合はそれを利用してください。
4. 対話式で .env を作成（推奨）:
   python -m kabusys.config_setup
   - J-Quants トークン、kabu API パスワード、KABUSYS_ENV などを対話式で入力します。
5. 設定検証:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗（exit 1）になります。
6. データディレクトリの確認:
   デフォルト DB / PID / フラグは data/ に置かれます。必要に応じて .env で上書きしてください。

主要な環境変数とデフォルト
----------------------------
（主なもの）
- KABUSYS_ENV: 実行環境 (development / paper_trading / live) — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db (監視用)
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- PAPER_FILL_MODE: instant | partial | never | reject （paper_trading の約定挙動）
- LOG_LEVEL: INFO（デフォルト）
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

使い方（例）
------------
1. 設定作成・検証
   - 対話式で .env を作る:
     python -m kabusys.config_setup
   - 設定検証:
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict

2. ExecutionEngine を起動（本番 or paper_trading に依存）
   python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db を使用します。
   - 実行時、data/execution.pid に PID を書き込みます。
   - 終了要求方法: リポジトリルートの data/stop_requested.flag を作成するとプロセスは停止手続きを行います。
   - Kill Switch（kill.flag）で強制停止トリガーが設定される場合があります（monitoring が判定して書き込み）。

3. Monitoring を起動（別プロセス）
   python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
   - 監視は常に「本番用」sqlite_path を使用して監視ログを残します（環境にかかわらず）。
   - 停止: data/stop_requested.flag を作成すると監視ループが終了します。

4. Paper Trading 検証レポート
   python -m kabusys.tools.paper_verification_report
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   --db オプションで DB パスを明示できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

プロセス停止／Kill Switch
------------------------
- data/stop_requested.flag:
  - run_execution / run_monitoring はこのファイルの存在をチェックして、存在する場合は正常終了処理します（手動停止に利用）。
- data/kill.flag:
  - KillSwitch が発動するとこのファイルを書き込み、ExecutionEngine を停止するシグナルとして機能します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動クリアします（本番では推奨されません）。

ロギング
-------
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテート・30日保持）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出して統一されています。
- LOG_DIR / LOG_LEVEL でカスタマイズ可能。

AI（OpenAI）関連
-----------------
- ニュース NLP（kabusys.ai.news_nlp）とレジーム判定（kabusys.ai.regime_detector）は OpenAI API を利用します。
- OPENAI_API_KEY が必要です。キーは .env に設定するか、score_news / score_regime 呼び出し時に api_key 引数で渡してください。
- API 呼び出しはリトライ・バックオフやレスポンス検証の仕組みを備えています（失敗時はフェイルセーフで続行します）。

開発者向けメモ
--------------
- 設定自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を基準に検出され、.env/.env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- DuckDB はリサーチ・AI モジュールで使われます（prices_daily / raw_financials / raw_news 等のテーブル想定）。
- MonitoringDB は SQLite を使い監視ログを永続化します。マイグレーション処理（列追加等）を最低限サポートしています。
- プロセス優先度や CPU affinity の設定は psutil を使って抽象化されています。権限がないと警告を出してスキップします。

ディレクトリ構成（抜粋）
---------------------
以下は本コードベースで提供されている主要ファイルのツリー（抜粋）です。

src/kabusys/
  __init__.py
  config.py
  config_setup.py
  validate_config.py
  run_execution.py
  run_monitoring.py

  utils/
    __init__.py
    logging_setup.py
    process_priority.py

  portfolio/
    __init__.py
    portfolio_builder.py
    risk_adjustment.py
    position_sizing.py

  research/
    __init__.py
    factor_research.py
    feature_exploration.py

  ai/
    __init__.py
    news_nlp.py
    regime_detector.py

  monitoring/
    monitoring_db.py
    monitoring_engine.py
    system_monitor.py
    risk_monitor.py
    kill_switch.py
    (trade_monitor.py 等が別ファイルとして想定されます)

  tools/
    __init__.py
    paper_verification_report.py

注意事項 / ベストプラクティス
-----------------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup にも注意書きあり）。
- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知や kill flag 等の設定を事前に確認してください。
- OpenAI API 呼び出しはコストが発生します。ローカル開発やテストではモックすることを推奨します（score_news の _call_openai_api はパッチで差し替え可能）。
- paper_trading 用 DB は本番 DB と完全に分離されるよう設計されています。安全にバックテスト・検証できます。

追加情報 / サポート
-------------------
- 設定の自動検出や生成、起動前検証を整備しています。まずは python -m kabusys.config_setup → python -m kabusys.validate_config を実行してください。
- 実運用時は run_execution と run_monitoring を別々のプロセスで起動して下さい（監視が Kill Switch を評価し実行エンジンを停止できる構成）。

以上が本リポジトリの概要と使い方です。必要があれば各モジュールのより詳細なドキュメント（API 使用例、内部設計、入出力フォーマット等）を追記できます。どの部分を詳しく記載したいか教えてください。
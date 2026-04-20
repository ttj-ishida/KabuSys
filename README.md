KabuSys — 日本株自動売買システム
================

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的としたコードベースです。  
本リポジトリは次の役割を持つ主要コンポーネントで構成されています。

- ExecutionEngine：発注・リスク管理・約定の取り扱い（paper_trading モードでの MockBroker 対応）
- Monitoring：システム状態・注文状態・リスクをポーリングしてログ・アラートを管理
- Research：DuckDB 上の市場データを使ったファクター計算や特徴量解析
- AI モジュール：ニュースの NLP スコアリング、レジーム検出（OpenAI を利用）
- ユーティリティ：設定ウィザード、設定検証、ログ設定、プロセス優先度制御 等

主な機能
--------
- 実行（Execution）
  - 本番 / ペーパートレードの切り分け（KABUSYS_ENV により動作が変化）
  - リスク管理（position limits / drawdown チェック等）
  - OrderManager / OrderRepository を通した発注ログ管理
- 監視（Monitoring）
  - システムリソース（CPU / メモリ / ディスク）と Execution プロセスの監視
  - 注文滞留や約定異常の検出、ダッシュボード更新
  - Kill Switch（閾値超過時に data/kill.flag を書き込み Execution を止める）
- 研究・分析（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ
- AI（OpenAI）
  - ニュース記事を LLM でセンチメント化して ai_scores テーブルへ書き込み
  - マクロニュースと ETF の MA200 乖離を組み合わせた市場レジーム判定
- ツール
  - 環境設定ウィザード（.env の対話的生成）
  - 設定検証 CLI（.env / config/*.yaml の不足チェック）
  - Paper Trading の検証レポート生成

セットアップ手順
----------------
1. Python 仮想環境の作成（任意だが推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（最低限）:
   - pip install duckdb psutil openai
   - 追加で YAML を検証したい場合: pip install pyyaml

   > 注: requirements.txt はリポジトリに含まれていない場合があります。上記パッケージを手動で用意してください。

3. ディレクトリ作成:
   - data/ と logs/ は自動作成されますが、権限等で失敗する場合は手動で作成してください。
     - mkdir -p data logs

4. 環境変数設定 (.env)
   - プロジェクトルートに .env を置くことで自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化されます）。
   - 主要な環境変数（.env 例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=...  (AI モジュールを使う場合)
     - PAPER_FILL_MODE=instant|partial|never|reject  (paper_trading 動作制御)
     - KILL_FLAG_CLEAR_ON_START=0|1

   - 対話式で .env を作るには:
     - python -m kabusys.config_setup

5. 設定検証（起動前に推奨）:
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

使い方
------
各種起動・ツールの基本的な使い方を示します。いずれもプロジェクトルートで実行してください。

- 監視プロセス起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - 実行:
    - python -m kabusys.run_monitoring
  - 停止:
    - data/stop_requested.flag を作成するとループを終了します（外部からの安全停止用）。
  - 備考:
    - Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使って監視テーブルを操作します。

- 実行エンジン起動（Execution）
  - ペーパートレード時は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込みます。
  - 実行:
    - python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag の作成で稼働中のエンジンに停止シグナルを送ります。
  - PID ファイル:
    - data/execution.pid に PID を書きます（設定でパス変更可）。

- 設定ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI 関連（OpenAI）
  - ニュース NLP / レジーム検出を使う場合は環境変数 OPENAI_API_KEY が必要です。
  - モジュール関数（プログラム的呼び出し）:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - API 呼び出しはリトライ・バックオフ等の保護を含みますが、料金・レート制限に注意してください。

実行時のフラグ・ファイル
----------------------
- data/stop_requested.flag
  - run_monitoring.py / run_execution.py はこのファイルの存在を監視し、存在するとループを安全終了します（外部停止用）。
- data/kill.flag
  - KillSwitch（Monitoring 内）によって書き込まれ、ExecutionEngine に対する停止要求（高レベルのリスクトリガー）を表します。
- data/execution.pid
  - Execution 起動時に PID を書き込みます（デフォルトパスは Settings.pid_file_path）。

設定（Settings）のポイント
-------------------------
- 設定は .env や環境変数から読み込まれ、Settings クラスを通してアクセスされます（kabusys.config.Settings）。
- 自動環境読み込みの優先順位:
  - OS 環境変数 > .env.local > .env
- 主な設定項目:
  - KABUSYS_ENV: development / paper_trading / live
  - PAPER_FILL_MODE: instant / partial / never / reject
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
  - OPENAI_API_KEY（AI を利用する場合）
  - LOG_LEVEL（ログレベル）

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースツリー内の主要モジュールと役割の概観です（src/kabusys 以下）。

- __init__.py
  - パッケージ定義、バージョン情報

- run_monitoring.py
  - Monitoring のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB へ記録）

- config.py
  - 環境変数・設定読み取りロジック（.env ロード、Settings クラス）

- config_setup.py
  - .env を対話式に作成するウィザード

- validate_config.py
  - 設定内容の起動前検証 CLI

- monitoring/
  - monitoring_db.py     — SQLite テーブル初期化・永続化層
  - system_monitor.py    — システム・データ鮮度監視
  - trade_monitor.py     — 注文滞留・約定異常検知（実装ファイルあり）
  - risk_monitor.py      — ドローダウン・ポジション上限監視
  - kill_switch.py       — Kill Switch 実装 (data/kill.flag)
  - monitoring_engine.py — Monitor を束ねるエンジン
  - alert_manager.py     — アラート通知（LINE 等）管理（実装ファイルあり）

- execution/
  - execution_engine.py  — ExecutionEngine（発注セッション管理）
  - broker_factory.py    — ブローカークライアント生成（Mock 対応）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    — 発注・リポジトリ・再整合・リスク管理コンポーネント

- portfolio/
  - portfolio_builder.py  — 候補選定・重み計算
  - position_sizing.py    — 株数決定・資金割当
  - risk_adjustment.py    — セクター上限・レジーム乗数

- research/
  - factor_research.py    — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py— 将来リターン・IC・統計サマリー

- ai/
  - news_nlp.py           — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py    — レジーム判定（MA200 + マクロ NLP）

- utils/
  - logging_setup.py      — ログ設定ユーティリティ（コンソール + 日次ファイルローテーション）
  - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

追加の注記 / 運用上の注意
------------------------
- DB 分離:
  - paper_trading モードでは本番の SQLite DB と分離された PAPER_TRADING_SQLITE_PATH を使用します（ログの混在防止）。
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力されます（30 日保存がデフォルト）。
  - LOG_DIR 環境変数でログディレクトリを変更可能です。
- OpenAI 利用:
  - API キーの管理および利用に関する料金・レート制限に注意してください。AI 関連処理はネットワークエラー時にリトライやフォールバック処理を行いますが、外部依存である点に留意してください。
- セキュリティ:
  - .env には機密情報（API トークン等）が含まれます。絶対に Git 等へコミットしないでください（config_setup も README に同様の注意を出力します）。

問い合わせ・拡張
----------------
- コードの各モジュールにはドキュメンテーションストリングとコメントが含まれています。新しい機能追加や運用設定は config/*.yaml（テンプレート生成スクリプトあり）や Settings クラスを通して行ってください。
- テストや CI については別途テストスイートを追加することを推奨します（現在のリポジトリではユニットテストは含まれていません）。

以上が本リポジトリの概要と基本的な使い方です。セットアップや運用で不明点があれば、実行ログ（logs/）および validate_config の出力を参考に問題点を特定してください。
KabuSys
=======

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
このリポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、LLM を用いたニュース評価などを含むモジュール群で構成されています。

概要
----
KabuSys は以下の主要機能を持つモジュール群から成ります。

- Execution Engine：ブローカークライアント経由での発注ロジック（paper_trading モードあり）
- Monitoring：プロセス・リソース・注文状況・リスク監視、Kill Switch（フラグファイル）によるエンジン停止
- Portfolio Construction：候補選定、ウェイト計算、ポジションサイズ算出、セクター制限等
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI：OpenAI を使ったニュースセンチメント評価 / レジーム判定
- 各種 CLI：初期 .env ウィザード、設定検証、ペーパートレード検証レポート生成 など

主な機能一覧
--------------
- .env 対話式セットアップ（kabusys.config_setup）
- 起動前設定検証（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合、MockBroker を利用し paper_trading DB を使用（本番 DB と分離）
- SystemMonitor / TradeMonitor / RiskMonitor をまとめたポーリング監視（kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Kill Switch：条件に応じて data/kill.flag を書き、ExecutionEngine を安全に停止
- DuckDB を利用したリサーチ用ファクター計算（momentum / volatility / value 等）
- OpenAI（gpt-4o-mini 等）でのニュース NLP による銘柄スコアリング / 市場レジーム判定
- ペーパートレード検証レポート生成ツール（kabusys.tools.paper_verification_report）

動作要件（推奨）
----------------
- Python 3.10+
- SQLite（標準ライブラリ）
- pip install で以下パッケージをインストールすることを推奨：
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイルの検証を行う場合に任意）
例:
  pip install duckdb psutil openai PyYAML

セットアップ手順
----------------

1. リポジトリをクローン / 配置
   - ソースはパッケージ形式（kabusys）として配置されている想定です。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV 等を設定します。
   - 出力される .env は Git に絶対コミットしないでください（秘密情報を含むため）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

主要環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の fill モード（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1、デフォルト 0）

使い方（よく使うコマンド）
------------------------

- .env を対話式で作る（初期設定）
  - python -m kabusys.config_setup

- 設定を検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- Execution Engine を起動
  - 環境例（ペーパートレード）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番環境:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成すると起動スレッドが停止要求を検知して終了します。
  - data/execution.pid に PID が書き込まれます（設定により異なる）。

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は .env の KABUSYS_ENV に関係なく本番 sqlite_path を使用し、監視テーブルを初期化します。
  - 停止フラグ: data/stop_requested.flag（存在すると監視ループが終了）

- Kill Switch（手動で Execution を止める）
  - KillSwitch は data/kill.flag を生成し Engine に停止シグナルを送ります（monitoring が判定して書き込みます）。
  - 手動で停止させたい場合は適切な内容を書いた data/kill.flag を作成してください。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされます（本番では推奨されません）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール（ニュース評価 / レジーム判定）
  - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または引数で渡す）。
  - 提供 API はライブラリ風（関数呼び出し）で利用します：
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime

ロギング
-------
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log に日次ローテーションで保存されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging により統一的に行われます。
- ログディレクトリは環境変数 LOG_DIR または引数で変更可能。作成に失敗した場合、ファイル出力は無効になりコンソールのみになります。

データベース
-----------
- DuckDB（分析用）: デフォルト data/kabusys.duckdb
- SQLite（監視用）: デフォルト data/monitoring.db
- Paper trading 用 SQLite（分離）: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に自動切替）
- 監視 DB は init_monitoring_db() によって必要テーブルが冪等に作成されます（マイグレーション処理あり）。

安全・運用上の注意
------------------
- KABUSYS_ENV=live（本番）を扱う際は env の値や LINE 通知設定などを必ず検証してください。
- .env ファイルには秘密情報が含まれるため、絶対にバージョン管理にコミットしないでください。
- 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨します（誤って Kill Switch をクリアしないため）。
- OpenAI 呼び出しは外部 API に依存するため、API 失敗時はフェイルセーフ（デフォルト値で継続）する実装になっていますが、運用時の鍵管理とレート制限には注意してください。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

subpackages / モジュール（主なもの）
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）で銘柄ごとにスコアリング
  - regime_detector.py     — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py       — SQLite 永続化層（監視ログ）
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — 注文状態監視（ファイルは該当部分で参照）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
  - kill_switch.py         — フラグファイルを書いて Execution を止める
  - alert_manager.py       — （警告/通知機能）
- portfolio/
  - portfolio_builder.py   — 候補選定・重み算出
  - position_sizing.py     — 株数決定・投下資金スケーリング
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン / IC / 統計
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度・CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

追加情報 / 開発メモ
------------------
- DuckDB 経由での集計・リサーチ処理は副作用を持たず（読み取りのみ）設計されています。
- AI モジュールは外部 API に対してバックオフ付きリトライを実装していますが、APIキーやコストに注意して利用してください。
- 既存 DB スキーマに列が不足している場合の軽微なマイグレーションコードが含まれます（monitoring_db.init_monitoring_db）。

ライセンス / バージョン
----------------------
- パッケージバージョンは kabusys.__version__ にて管理（このコードでは "0.1.0" が設定されています）。
- ライセンス情報はリポジトリに合わせて追加してください（この README には含まれていません）。

問題・拡張
---------
- 実際に発注を行う本番組み合わせ（kabu API との連携）は適切なテストと安全確認を行ってください。
- 将来的に単元株（lot_size）を銘柄ごとに管理する、またはトランザクションコスト推定を改善する等の拡張が容易に行える設計になっています。

以上がこのコードベースの概要と使い方です。必要であれば「起動フロー詳細」「DB スキーマ説明」「各モジュールの API 仕様」などの追加ドキュメントも作成します。どの章を詳しくしたいか教えてください。
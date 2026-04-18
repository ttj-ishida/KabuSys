README
=====

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤のサンプル実装です。  
主な目的は、取引エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ（DuckDB ベースのファクター計算）、およびニュース系 AI スコアリングを統合するためのユーティリティ群と CLI を提供することです。

特徴
----
- ExecutionEngine：実際のブローカー／モックブローカーを切り替え可能（KABUSYS_ENV=paper_trading でペーパートレード）。
- Monitoring：CPU/メモリ/ディスク、データ鮮度、注文状態、リスク（ドローダウン／ポジション数）を定期監視して SQLite にログ。
- Kill Switch：監視で重大リスクを検出した際に data/kill.flag を作成し実行エンジンを停止可能。
- Research：DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ。
- AI モジュール：ニュースを OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores 等へ格納するロジック。
- ユーティリティ：.env 対話式ウィザード、設定検証 CLI、ロギング設定、プロセス優先度設定など。
- ペーパートレード検証レポート生成ツール（SQLite ベース）。

必須・推奨コンポーネント
- Python 3.10+（typing の | 演算子を使用するため）
- ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML のパースを行う場合）
- SQLite（標準ライブラリで利用可）
- ネットワークアクセス（kabuステーション API / OpenAI を利用する場合）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

4. ディレクトリ作成
   - mkdir -p data logs

5. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を手動作成

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

重要な環境変数（主なもの）
--------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 推奨/オプション
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト development
    - paper_trading の場合、MockBrokerClient を利用して data/paper_trading.db に記録
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- モニタ用上書き
  - MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト 60）

主な使い方
---------

1. 環境ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3. ExecutionEngine 起動（取引実行）
   - python -m kabusys.run_execution
   - 注意:
     - KABUSYS_ENV=paper_trading のときは MockBrokerClient が使用され、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
     - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
     - PID ファイルは data/execution.pid（Settings.pid_file_path 参照）に書かれます。

4. Monitoring 起動（常駐監視）
   - python -m kabusys.run_monitoring
   - オプション:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定（秒）。
   - 補足:
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用してログを記録します。
     - 停止は data/stop_requested.flag の作成で行います（存在検知でループを終了）。

5. ペーパートレード検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で別ファイルを指定可能（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

6. AI / レジーム判定 / ニューススコアリング（ライブラリ呼び出し）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB 接続（duckdb.connect(...)）と OpenAI API キーを必要とします。

ログ設定
--------
- 全スクリプトは共通のログ設定ユーティリティを使用:
  - kabusys.utils.logging_setup.setup_logging(app_name="execution")
- ログ出力:
  - stdout（StreamHandler）
  - ファイル: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）
- LOG_DIR 環境変数でログディレクトリを上書き可能

監視・停止フラグの仕組み
-----------------------
- stop_requested.flag（data/stop_requested.flag）:
  - run_execution/run_monitoring がループを終了する（存在検知で停止）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）:
  - KillSwitch によって重要なリスク検出時に書き込まれ、ExecutionEngine に外部停止命令を送るために使用。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされる（本番では推奨しません）。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — Monitoring 起動スクリプト
- config.py                       — 環境変数 / 設定管理（Settings クラス）
- config_setup.py                 — .env 対話式ウィザード
- validate_config.py              — 設定検証 CLI
- tools/
  - paper_verification_report.py   — ペーパートレード検証レポート生成ツール
- ai/
  - news_nlp.py                    — ニュース NLP スコアリング（OpenAI 呼び出し）
  - regime_detector.py             — レジーム判定（ETF MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py               — SQLite ベースの永続化層
  - system_monitor.py              — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py               — 注文関連監視（ファイル内にある想定）
  - risk_monitor.py                — ドローダウン / ポジション上限監視
  - kill_switch.py                 — kill.flag 書込みクラス
  - monitoring_engine.py           — 各 Monitor を束ねるエンジン
  - alert_manager.py               — アラート送信（LINE 等、実装想定）
- execution/
  - execution_engine.py            — 実行エンジンのコア（EngineConfig 等）
  - broker_factory.py              — ブローカークライアント生成
  - order_manager.py               — 注文管理ロジック
  - order_repository.py            — DB 永続化（注文履歴など）
  - reconciler.py                  — 注文状態の整合
  - risk_manager.py                — 実行時リスク制御
- portfolio/
  - portfolio_builder.py           — 候補選定 / ウェイト計算
  - position_sizing.py             — 株数計算 / 単元丸め / キャップ処理
  - risk_adjustment.py             — セクターキャップ / レジーム乗数
- research/
  - factor_research.py             — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py         — 将来リターン / IC / 統計サマリー
- utils/
  - logging_setup.py               — ログ初期化ユーティリティ
  - process_priority.py            — プロセス優先度 / CPU affinity
  - __init__.py
- monitoring/monitoring_db.py      — （上記）SQLite テーブル初期化・CRUD
- data/（実行時に作成される想定）
  - monitoring.db (SQLITE_PATH のデフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
  - kabusys.duckdb (DUCKDB_PATH のデフォルト)
  - kill.flag / stop_requested.flag / execution.pid 等のフラグや PID ファイル

開発メモ / 注意点
-----------------
- .env は決して Git にコミットしないこと（config_setup は冒頭に注意書きを出力します）。
- Monitoring は SQLite（monitoring.db）を使用して状態を永続化します。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します。
- KABUSYS_ENV=paper_trading の際は発注 API 呼び出しはモックとなり、ペーパートレード用 DB に分離されます。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しの失敗時はフェイルセーフ（多くの箇所でゼロフォールバック）を採用しています。
- DuckDB を用いるリサーチ/AI モジュールは大量データ処理に有利ですが、ローカルファイルのパスや権限に注意してください。

サポートされる実行例（まとめ）
------------------------------
- .env の対話作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- ライブラリ呼び出し例（Python シェル）:
  - import duckdb, os
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.research import calc_momentum
  - calc_momentum(conn, date(2026,4,10))

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスやコントリビューションガイドラインを記載してください）

---
README はこのリポジトリ内のスクリプトやモジュールの現状の実装に基づいて作成しています。実際の運用前に必ず python -m kabusys.validate_config で設定を確認し、テスト環境で動作検証してください。
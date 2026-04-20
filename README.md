KabuSys
=======

日本株自動売買システム（KabuSys）の簡易リポジトリ説明書です。本プロジェクトはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、ニュースNLP（LLM）ベースのセンチメント評価などのコンポーネントを含むモジュール群で構成されています。

主な特徴
--------
- 実行エンジン（ExecutionEngine）: ブローカークライアントを通じて注文発行を行う。paper_trading 環境ではモックブローカーを使用し、本番 DB と分離。
- 監視（Monitoring）: システム状態、注文ログ、リスク（ドローダウン/ポジション数）を定期的にチェックし、kill flag を書き込むことで ExecutionEngine を安全に停止可能。
- ポートフォリオ構築: 候補選定、重み計算（等金額 / スコア加重）、ポジションサイズ計算、セクター上限・レジーム補正を提供する純粋関数群。
- リサーチ: DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン計算、IC 計算、ファクター統計サマリ。
- ニュース NLP / レジーム判定: OpenAI（gpt-4o-mini 等）を利用したニュースセンチメントスコア付与およびマクロセンチメントを組み合わせた市場レジーム判定。
- ユーティリティ: 環境設定ウィザード、設定検証 CLI、ログ設定、プロセス優先度設定など。
- ツール: Paper Trading 検証レポート生成スクリプト。

機能一覧
--------
- 設定管理
  - .env 自動読み込み（.env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 対話式 .env 作成ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行系
  - 起動スクリプト: python -m kabusys.run_execution
  - Paper trading と Live を切り替え可能（KABUSYS_ENV）
  - ブローカーファクトリ（BrokerClientFactory）により実運用/モック切替
- 監視系
  - 起動スクリプト: python -m kabusys.run_monitoring
  - MonitoringEngine によるポーリング（MONITOR_POLL_INTERVAL で間隔制御）
  - KillSwitch による停止通知（data/kill.flag）
  - 監視ログ永続化（SQLite）
- リサーチ / ポートフォリオ
  - kabusys.research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic 等
  - kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- AI / NLP
  - kabusys.ai.score_news: raw_news を LLM に投げて ai_scores を更新
  - kabusys.ai.regime_detector: ETF やマクロ記事を使ったレジーム判定と DB 書き込み
- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

前提・準備
----------
- Python 3.10 以上（型注釈や | 合成型を使用）
- SQLite（Python 標準ライブラリ）
- 推奨インストールパッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML 検査を行う場合）
- 仮想環境の作成を推奨:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

インストール（例）
-----------------
1. リポジトリをクローン:
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

（requirements.txt がある場合は pip install -r requirements.txt）

セットアップ手順
----------------
1. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env を配置（.env.example がない場合は config_setup を使用）。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO, DEBUG）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアする場合は 1）

2. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - 問題がある場合は指示に従って .env / config/*.yaml を修正。
   - --strict を付けると警告も失敗扱いになります。

3. ディレクトリ作成（必要な場合）:
   - logs/（ログ出力）
   - data/（DB・フラグファイル）
   これらはスクリプト起動時に自動作成されることがありますが、権限等の都合で事前に作成しておくとよいです。

使い方
------
基本的な起動例とツール利用法を示します。

- 監視の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は監視用 DB（Settings.sqlite_path）を使用します（環境にかかわらず監視 DB は本番パスを参照します）。
  - 停止制御: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します。

- 実行エンジンの起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。
  - 停止制御: run_execution は data/stop_requested.flag と data/execution.pid を利用します。監視側の kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）が書かれるとエンジン停止がトリガーされます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / ニューススコアリング（プログラムから直接）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)
    - conn は duckdb 接続（duckdb.connect(...)）
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
    - 書き込み先: ai_scores テーブル

- レジーム判定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - market_regime テーブルへ書き込みます

- ライブラリ利用（リサーチ / ポートフォリオ）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes, apply_sector_cap

監視・停止フラグについて
-----------------------
- data/kill.flag
  - KillSwitch が必要と判断した場合（例: ドローダウン超過）に書き込まれるテキストファイル。ExecutionEngine がこれを検出して安全に停止します。
- data/stop_requested.flag
  - ローカル運用で外部から監視プロセスや実行エンジンを停止させたい際に使うフラグ。存在すると run_monitoring / run_execution のループが終了します。

ログ
----
- ログはデフォルトで logs/<app_name>.log（日次ローテーション）とコンソール（stdout）に出力されます。
- setup_logging(app_name="execution") 等でアプリ名を指定。LOG_DIR 環境変数でログディレクトリを変更可能。
- 既存ハンドラは再設定時にクローズされ、二重出力を防止します。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート generator
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（監視用テーブル）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常検出（ファイルに含まれる）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - alert_manager.py        —（アラート通知の実装）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 発注株数計算・スケーリング
    - risk_adjustment.py      — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — Momentum, Volatility, Value 計算
    - feature_exploration.py  — 将来リターン・IC・ランク等
    - __init__.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py

注意点 / 補足
------------
- 設定読み込み:
  - OS 環境変数 > .env.local > .env の順で優先読み込みします（デフォルト）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB:
  - 監視用は SQLite（Settings.sqlite_path）。duckdb は分析・リサーチ用に使用します。
  - run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用して本番データと完全分離します。
- AI 呼び出し:
  - OpenAI クライアントを使用します。API の失敗時はフェイルセーフ（スコアを 0.0 にフォールバックする、または処理をスキップ）する実装になっていますが、API キーが未設定の場合は例外が発生します。
- ローカルで止めたい場合:
  - data/stop_requested.flag を作ると run_*.py の起動ループが停止します（手動削除が必要）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__version__ に定義されています（現状 "0.1.0"）。
- ライセンス情報はリポジトリに含まれる LICENSE ファイルをご確認ください（本 README では省略）。

問い合わせ
----------
実装や利用に関する詳しい仕様・開発ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）が別途存在する想定です。実務利用の際はそれらの設計資料と合わせて参照してください。

以上。必要に応じて README に追加したい項目（例: requirements.txt の自動生成、デプロイ手順、CI 設定）を教えてください。
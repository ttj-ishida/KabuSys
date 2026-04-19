KabuSys — 日本株自動売買システム
===============================

このリポジトリは日本株向けの自動売買システム KabuSys のコアライブラリ群です。  
トレード実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ／ファクター計算、AI（ニュースセンチメント・レジーム判定）などの主要機能を含みます。

主な特徴
--------
- ExecutionEngine（注文発行・リスク管理・リコンシリエーション）
- Monitoring（システム状態・注文・リスク監視、Kill Switch）
- Portfolio construction（候補選定・ウェイト算出・ポジションサイズ計算・セクター制限）
- Research（ファクター計算、将来リターン、IC 計算、統計要約）
- AI モジュール（ニュースセンチメントの LLM スコアリング、レジーム判定）
- 各種ユーティリティ（環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- Paper trading モード（本番 DB と分離された専用 SQLite に記録）

必要な環境・依存
----------------
- Python 3.10+（typing, dataclasses を前提）
- 主要依存パッケージ（例）:
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（設定 YAML 検証を行う場合）
- 環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 重要なファイル/ディレクトリ（デフォルト）
  - データベース: data/monitoring.db (SQLite)、data/kabusys.duckdb (DuckDB)、data/paper_trading.db（ペーパートレード用）
  - ログディレクトリ: logs/（LOG_DIR で変更可）
  - フラグファイル: data/kill.flag（Kill Switch）, data/stop_requested.flag（各プロセスの停止要求）
  - PID ファイル: data/execution.pid

セットアップ手順
-------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）
   - pip install -r requirements.txt  （requirements.txt をプロジェクトに用意している前提）
   - 必要に応じて openai, duckdb, psutil, PyYAML を個別にインストール

3. 初期環境変数の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - .env を対話式に作成・更新します（.env は絶対に git にコミットしないでください）。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱い（exit(1)）になります。

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

主な実行方法
------------

- 監視（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 説明:
    - SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard 等に記録します。
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書きできます（秒）。
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず監視 DB を共通で参照します）。
    - 停止方法: data/stop_requested.flag を作成するか Ctrl+C。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV により動作モードが変わります:
      - paper_trading: MockBrokerClient を使用し、デフォルトで data/paper_trading.db を使用（本番 DB と分離）
      - live / development: 本番設定に従う
    - 起動時に data/stop_requested.flag があると起動を行いません。
    - 起動時に Kill Flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）を確認してください（本番では推奨しません）。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env の生成・更新を対話式で支援します。

- 設定検証 CLI
  - python -m kabusys.validate_config
  - .env と config/*.yaml の存在・基本妥当性をチェックします（PyYAML がない場合は YAML 検証はスキップ）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - 出力: 稼働率・注文/成立率・レイテンシ等のサマリと PASS/FAIL 判定

- AI 機能（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news を元に OpenAI でセンチメントを付与し、ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF MA とマクロニュースの LLM 評価を合成して market_regime を書き込む
  - これらはライブラリ関数として呼び出して使用します。OpenAI API Key は環境変数 OPENAI_API_KEY か引数で指定してください。

設定項目（主な環境変数）
-----------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時の約定モード。instant|partial|never|reject）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（ログ保存先ディレクトリ）
- KILL_FLAG_CLEAR_ON_START（0/1、本番では 0 推奨）
- OPENAI_API_KEY（AI 機能を使う場合に必要）

運用上の注意
------------
- .env は絶対にコミットしないこと（機密情報が含まれる）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=1 を避ける（Kill Switch を不意にクリアするリスク）。
- Monitoring は監視 DB に常に本番 sqlite_path を使用する点に注意（環境にかかわらず同じ DB を参照）。
- data/kill.flag を書くと ExecutionEngine に停止シグナルを送る Kill Switch が作動します（KillSwitch モジュールの動作）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーション保存されます。LOG_DIR で変更可能。

主要ディレクトリ構成
-------------------
（src/kabusys 以下）

- ai/
  - news_nlp.py          — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py   — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - run_monitoring.py    — SystemMonitor ポーリングループ起動スクリプト
  - monitoring_db.py     — SQLite ベースの永続化レイヤ（テーブル定義・操作クラス）
  - system_monitor.py    — システム状態・データ鮮度のチェック
  - trade_monitor.py     — （取引関連監視ロジック）
  - risk_monitor.py      — ドローダウン・ポジション限界の監視
  - kill_switch.py       — Kill Switch（フラグファイル生成）
  - monitoring_engine.py — 複数モニタの統括（ポーリング実行）
  - alert_manager.py     — （LINE 等への通知管理）
- execution/
  - run_execution.py     — ExecutionEngine 起動スクリプト
  - execution_engine.py  — エンジン本体（セッション実行・発注管理）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py   — 株数算出・単元丸め・資金スケーリング
  - risk_adjustment.py   — セクターキャップ・レジーム乗数
- research/
  - factor_research.py   — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py — 将来リターン/IC/統計サマリ
- monitoring/
  - monitoring_db.py etc. (上記)
- utils/
  - logging_setup.py     — 共通ログ設定（Stream + 日次ファイルローテーション）
  - process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading レポート生成スクリプト
- config.py              — 環境変数読み込み / Settings クラス
- config_setup.py        — .env 作成ウィザード
- validate_config.py     — 設定検証 CLI

開発者向け補足
--------------
- DuckDB 接続は研究/ファクター計算に利用します（prices_daily, raw_financials などを前提）。
- MonitoringDB は監視用の小さな SQLite スキーマを提供します（冪等でテーブル作成）。
- AI モジュールは OpenAI（gpt-4o-mini など）を使用するため、API コール周りはリトライ・検証ロジックを含みます。API レスポンスの形式は厳密な JSON を期待します。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして .env 自動ロードを抑止できます。

よくある操作例
--------------
- .env を作る:
  - python -m kabusys.config_setup

- 設定を検証する:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視をデバッグ的に 1 回実行したい場合:
  - Python REPL から MonitoringEngine を組み立て run_once を呼んでテストできます（ユニットテスト向けのメソッドが用意されています）。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

問い合わせ・貢献
----------------
バグ報告や機能提案は Issue を立ててください。プルリクエスト歓迎です。README に記載のない運用ルールや導入手順はプロジェクトの CONTRIBUTING.md を参照してください（存在する場合）。

以上がこのコードベースの概要と主な使い方です。特定のモジュールや機能について詳細なドキュメント（API 仕様・設定例・実運用手順）が必要であれば、どの箇所を深掘りするか教えてください。
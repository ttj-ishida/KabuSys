KabuSys — 日本株自動売買システム
=============================

このリポジトリは、日本株向けの自動売買・リサーチ・監視ツール群をまとめたパッケージ (kabusys) です。
主要コンポーネントは Execution（発注エンジン）、Monitoring（監視・アラート・Kill Switch）、Research（ファクター計算）、Portfolio（ポートフォリオ構築）、AI（ニュース NLP / レジーム判定）などです。

主な特徴
--------
- 発注エンジン（ExecutionEngine）  
  - 本番 / ペーパートレード（KABUSYS_ENV=paper_trading）の分離（ペーパートレードは専用 SQLite DB に記録）
  - BrokerClient のファクトリによるブローカー切替
  - リスク管理（RiskManager）、注文管理（OrderManager）、約定照合（Reconciler）などの統合
- 監視（Monitoring）  
  - System / Trade / Risk の各 Monitor を定期実行して DB にログを蓄積
  - Kill Switch によるフラグファイル操作で Execution を安全停止
  - Alert 管理・ログ・レポート出力の仕組み
- ポートフォリオ構築（Portfolio）  
  - 候補選定、等金額／スコア重み付け、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算（単元株丸め、集約キャップ）
- リサーチ（Research）  
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた SQL ベース処理）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI モジュール（OpenAI 経由）  
  - ニュース記事のセンチメントスコア付与（ai_scores テーブルへの書き込み）
  - マクロニュースと ETF の MA200 を組み合わせた市場レジーム判定
  - OpenAI (gpt-4o-mini 等) を使用（APIキーを環境変数で指定）
- ユーティリティ  
  - ログ設定（stdout + 日次ローテートファイル）/ プロセス優先度設定 / .env ウィザード / 設定検証 CLI
- 運用ツール  
  - Paper Trading 検証レポート生成スクリプト（期間指定で各種指標を表示）

必須・主要な環境変数
--------------------
（.env を作成して運用することを推奨。config_setup で対話的に生成できます）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（任意・デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabuステーション API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- OPENAI_API_KEY: AI モジュールを使う場合に必要

セットアップ手順
--------------
1. Python バージョン
   - Python 3.10+ を推奨（PEP 604 の union 型などを使用）

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール  
   ※ requirements.txt がない場合は以下をインストールしてください（プロジェクトによって追加要件あり）:
   - pip install duckdb psutil openai
   - PyYAML があると config/*.yaml の検証が有効になります（任意）：pip install pyyaml

4. .env の作成（対話式）
   - python -m kabusys.config_setup
     - 対話で必須鍵や DB パス、KABUSYS_ENV 等を入力して .env を生成できます

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合: python -m kabusys.validate_config --strict

6. DB 初期化（運用開始時）
   - 監視用 SQLite DB と DuckDB は各起動スクリプトが必要に応じて作成・マイグレーションします。
   - 例: run_monitoring / run_execution を最初に起動すると必要テーブルが作成されます。

使い方（起動コマンド）
-------------------
注意: 実行前に .env を正しく設定してください。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、ペーパートレード用 DB (PAPER_TRADING_SQLITE_PATH) に記録します。
    - 実行時に data/execution.pid に PID を書きます。
    - 停止するには data/stop_requested.flag を作成するか、監視側の kill.flag（data/kill.flag）を使います。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き可能（デフォルト 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依存しません）。
  - 停止: data/stop_requested.flag を作成するか Ctrl+C。

- Paper Trading 検証レポート（単発実行）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - オプション --db で直接パス指定可

- AI モジュール呼び出し例（プログラム内から）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - api_key を与えない場合は環境変数 OPENAI_API_KEY を参照します。

運用上の注意
------------
- Kill Switch
  - monitoring モジュールが条件を満たすと data/kill.flag を書き込み、Execution に停止シグナルが送られます。
  - 本番運用時は Kill Switch の自動クリア設定（KILL_FLAG_CLEAR_ON_START）に注意（デフォルト 0 推奨）。
- ログ
  - デフォルトでコンソール出力と logs/<app_name>.log（日次ローテーション、30日保持）に出力されます。
  - ログディレクトリは LOG_DIR 環境変数で上書き可能。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等でテーブルを作成し、既存 DB に対する簡易マイグレーション（カラム追加）も行います。
- OpenAI API
  - AI 機能を使う場合は OPENAI_API_KEY を設定してください。API失敗はフェイルセーフ（0.0 などのフォールバック）で処理される設計です。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースツリー（src/kabusys）内の主要モジュールと説明の抜粋です。

- src/kabusys/
  - __init__.py                — パッケージ初期化（バージョン等）
  - config.py                  — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前の設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト（発注エンジン）
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - utils/
    - logging_setup.py         — ロギング初期化ユーティリティ（stdout + 日次ファイル）
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — SQLite 永続層（テーブル作成・読み書きラッパー）
    - monitoring_engine.py     — 複数 Monitor を束ねる実行ループ
    - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度 等の監視
    - trade_monitor.py         — （trade 監視：滞留注文等）※詳細はコード参照
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag の書き込み / 既存チェック
    - alert_manager.py         — （アラート送信管理）※詳細はコード参照
  - execution/
    - execution_engine.py      — ExecutionEngine 本体（run_session など）
    - broker_factory.py        — BrokerClient の生成（本番 / Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py     — 候補選定・配列計算
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
    - position_sizing.py       — 発注株数決定ロジック
  - research/
    - factor_research.py       — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py   — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py              — ニュースの LLM ベースセンチメント付与（ai_scores 更新）
    - regime_detector.py       — マクロニュース + MA200 によるレジーム判定
  - data/                      — 実行時に使用される既定のディレクトリ（logs/, data/ 以下に DB / flag / pid を配置）
  - config/                    — YAML 設定テンプレート（system_config.yaml 等。validate_config で検証）

補足
----
- YAML の検証は PyYAML がインストールされている場合にのみ行われます（validate_config.py）。
- DuckDB を参照するリサーチコードは外部の価格テーブル（prices_daily / raw_financials 等）に依存します。データ準備は別途必要です。
- ランタイムに生成されるフラグファイル:
  - data/kill.flag          — Kill Switch による停止要求
  - data/stop_requested.flag— run_* スクリプトの外部停止トリガ（あるいは運用用フラグ）
  - data/execution.pid      — Execution の PID（run_execution が書き込み）

貢献 / 開発
------------
- コードを読みやすく保つため、ビジネスロジックと永続化層を分離しています（monitoring_db など）。
- ユニットテストや CI は本リポジトリの将来拡張点です。AI 呼び出しや外部 API はモック可能なインタフェースにしています。

問い合わせ
----------
不明点や運用に関する相談があれば、該当モジュールのドキュメント（ファイル内 docstring）を参照してください。README に記載のない運用ルールや追加のセットアップ手順（マーケットデータの投入など）は別途提供される運用マニュアルを参照してください。

---  
（この README はリポジトリ内のソースから自動的に要約しています。実際の運用では .env.example / config/*.yaml / scripts を合わせて参照してください。）
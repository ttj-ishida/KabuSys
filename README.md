KabuSys — 日本株自動売買システム
================

このリポジトリは日本株向けの自動売買および研究用モジュール群を集めたプロジェクトです。  
本 README はコードベース（src/kabusys 以下）に基づき、日本語での概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめたものです。

要約（プロジェクト概要）
----------------
- KabuSys はトレード用の ExecutionEngine、監視（Monitoring）、調査（Research）、ポートフォリオ構築、AI（ニュース NLP / レジーム判定）などを含むモジュール群です。
- データ永続化には DuckDB（分析用）と SQLite（監視・発注ログ）を利用します。
- 環境変数 / .env による設定管理を行い、config_setup（ウィザード）／validate_config（検証 CLI）で初期設定・検証が可能です。
- Paper Trading（検証）用に本番 DB と分離された専用 SQLite（data/paper_trading.db）を用意できます。
- OpenAI を利用したニュースセンチメントやレジーム判定機能を備えています（利用時に API キーが必要）。

主な機能一覧
-----------
- Execution（run_execution.py）
  - 実際の発注を担う ExecutionEngine の起動スクリプト。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、paper_trading DB に記録（本番 DB と分離）。
  - プロセス優先度設定・PID ファイル管理、停止フラグ（data/stop_requested.flag）監視。

- Monitoring（run_monitoring.py / monitoring/*）
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する監視エンジン。
  - system_status, trade_logs, risk_logs, positions, dashboard といった監視用テーブルを SQLite に永続化する機能。
  - Kill Switch（条件を満たしたら data/kill.flag を作成して Execution を停止させる）やアラート発行の統合。

- Portfolio（portfolio/*）
  - 候補選定、重み計算、セクター上限チェック、ポジションサイズ計算（単元株丸め等）を行う純粋関数群。

- Research（research/*）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）や特徴量解析（将来リターン、IC 計算、統計サマリー）を DuckDB 上で実行。

- AI（ai/*）
  - news_nlp: raw_news の記事を OpenAI（gpt-4o-mini 等）でスコアリングし ai_scores テーブルへ保存。
  - regime_detector: ETF の MA とマクロニュースの LLM センチメントを合成して市場レジームを判定し market_regime に保存。
  - API 呼び出しはリトライ・フェイルセーフを組み込んでいる。

- ツール
  - config_setup.py : 対話式に .env を作成／更新するウィザード。
  - validate_config.py : .env や config/*.yaml の存在・妥当性を検証する CLI。
  - tools/paper_verification_report.py : Paper Trading の検証レポートを生成。

セットアップ手順
-------------
以下はローカルで動かすための簡易手順です（環境に応じて調整してください）。

1. Python 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - requirements.txt がない場合は主要依存を手動インストール:
     - pip install duckdb psutil openai
     - （オプション）PyYAML は config 検証で利用されます: pip install pyyaml

   ※ 実際の requirements.txt がある場合は pip install -r requirements.txt を使用してください。

3. プロジェクトルートに .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成（このコードベースでは .env.example の示唆あり）。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も FAIL としたい場合: python -m kabusys.validate_config --strict

5. DB 初期化
   - 実行スクリプト内で init_monitoring_db が接続時に自動でテーブル作成・マイグレーションを行います。明示的な初期化は不要です。

主要な環境変数（代表）
-------------------
- 必須（最低限セットするもの）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 動作モード・DB 関連
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE — paper_trading のフィルモード（instant/partial/never/reject）

- ログ・監視関連
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログ保存先ディレクトリ（default: logs）
  - PID_FILE_PATH — 実行エンジン用 PID ファイルパス（default: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch のフラグファイル（default: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0 / 1、本番では 0 推奨）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

- OpenAI 関連（AI 機能利用時）
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / regime_detector で使用）

使い方（主要スクリプト）
--------------------

1. 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります。

3. ExecutionEngine の起動（発注エンジン）
   - python -m kabusys.run_execution
   - 動作モードは KABUSYS_ENV に依存:
     - paper_trading のときは MockBrokerClient を使用して data/paper_trading.db に記録。
     - live のときは実際のブローカークライアント（設定に依存）。

   停止方法:
   - data/stop_requested.flag を作成すると run_execution 側で検知して停止します（実装はプロジェクトの stop フラグを参照）。
   - また Kill Switch（data/kill.flag）が書かれると外部で Execution を停止する設計になっています。KILL_FLAG_CLEAR_ON_START の設定に注意。

4. Monitoring の起動（システム監視）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定できます（デフォルト 60 秒）。
     例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を明示する場合:
     - python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

6. AI 系機能（ニュース NLP / レジーム判定）
   - ai.news_nlp.score_news や ai.regime_detector.score_regime 関数を利用（ライブラリ関数）またはスクリプトから呼び出し可能。
   - OPENAI_API_KEY を設定しておくこと。API 呼び出しはリトライ・フェイルセーフあり。

ログ / ファイル
---------------
- ログ出力:
  - デフォルトでは logs/<app_name>.log に日次ローテートで出力（TimedRotatingFileHandler, 30日分保持）。
  - すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出します。

- 監視 / 制御ファイル（data ディレクトリ内）
  - data/monitoring.db（デフォルトの SQLite 監視 DB）
  - data/paper_trading.db（paper_trading 用 DB）
  - data/execution.pid（PID ファイル）
  - data/kill.flag（Kill Switch フラグ）
  - data/stop_requested.flag（停止要求フラグ）

注意点 / 運用上のヒント
-------------------
- 本番（KABUSYS_ENV=live）稼働時は .env の値を慎重に管理し、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- OpenAI を利用する処理はコストとレイテンシに注意してください（API キーと利用制限）。
- DuckDB / SQLite のファイルパスは適切な場所（十分なディスク容量、バックアップ方針）に設定してください。
- run_execution/run_monitoring はフォアグラウンドで動作するスクリプトです。常時稼働させるには systemd / supervisor / docker 等でデーモン化してください。
- config/*.yaml の生成補助スクリプト（scripts/generate_config.py 等）がプロジェクトにあれば活用してください（validate_config の警告を参照）。

ディレクトリ構成（抜粋）
--------------------
プロジェクトの主要部分（src/kabusys 以下）の構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるセンチメント計算
    - regime_detector.py     — 市場レジーム判定（MA + LLM 合成）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 / 永続化層
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（省略されたが概念あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 管理
    - monitoring_engine.py   — モニタを束ねるエンジン
    - alert_manager.py       — アラート送信（LINE 等、実装に依存）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算・集計キャップ
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・サマリー等
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/ (上記)
  - execution/ (発注関連コンポーネント: broker_factory, engine, order_manager 等; 実装あり)

（注）この README は repo に含まれる Python ソースから抽出した情報をまとめたもので、実際の実装や追加ファイル（requirements.txt、scripts、Dockerfile など）によっては補足・変更が必要です。

トラブルシューティング（よくあるポイント）
--------------------------------
- .env が読み込まれない／自動ロードを無効化したい:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを抑制します（テスト目的等）。
- OpenAI 呼び出しで失敗が多い／429 を受ける:
  - API キー・レート制限・モデル指定を確認。news_nlp と regime_detector はリトライを行いますが、呼び出し頻度の調整を検討してください。
- SQLite/DuckDB のパスに注意:
  - デフォルトは data/ 以下。権限や場所を運用要件に合わせて変更してください。

最後に
-----
詳細な API 仕様や追加の運用手順（デーモン化方法、バックアップ方針、アラート設定、strategy の具体実装など）は別途ドキュメント（運用手順書 / design doc / PortfolioConstruction.md / StrategyModel.md 等）にまとめられている想定です。必要があればそれらに合わせて README を拡張します。
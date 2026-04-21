# KabuSys

日本株向け自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、シグナル生成 / ポートフォリオ構築 / 発注エンジン / 監視 / レポーティング / 研究用ユーティリティを含む自動売買基盤の実装です。  
README は主に開発者・運用者向けの概要、セットアップ、起動方法、ディレクトリ構成をまとめています。

---

## プロジェクト概要

- システム構成要素
  - ExecutionEngine: 発注・注文管理・リスク管理を行う実行エンジン（run_execution.py）
  - Monitoring: システム状態・注文状況・リスクを定期チェックし、アラートや Kill Switch を発動する監視機構（run_monitoring.py / monitoring パッケージ）
  - Portfolio モジュール: 候補選定・重み計算・ポジションサイズ計算などの純関数群（kabusys.portfolio）
  - Research / Feature 工具: DuckDB を使ったファクター計算・IC 計算等（kabusys.research）
  - AI モジュール: ニュースの NLP スコアリング・市場レジーム判定（kabusys.ai）
  - ユーティリティ: 設定管理、ロギング設定、プロセス優先度設定 など（kabusys.utils）
  - ツール: Paper Trading 検証レポート生成スクリプト等（kabusys.tools）

- 設計方針の要点
  - 設定は .env ファイル / 環境変数で管理。プロジェクトルートの .env を自動ロード（無効化可能）。
  - Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離して専用 SQLite に記録。
  - DuckDB を分析向け DB として利用（prices_daily / raw_financials 等のテーブル参照）。
  - 外部 API（OpenAI など）は失敗時にフォールバックする実装を多用し、フェイルセーフ性を重視。

---

## 機能一覧

- 実行 / 発注
  - ExecutionEngine による注文生成・ブローカークライアント抽象化・リスク管理・再整合（reconciler）
  - Paper Trading モード（MockBrokerClient）と Live モードの切り替え
- 監視
  - SystemMonitor: CPU/メモリ/Disk、Execution プロセス存在、株価データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常の検出（実装参照）
  - RiskMonitor: ドローダウン、ポジション数上限の監視とリスクログ記録
  - KillSwitch: 閾値超過時に data/kill.flag を書き込んで Execution を停止
  - MonitoringEngine: 監視タスクを統合してポーリング
- 研究 / ファクター
  - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB 接続を受け取り純計算）
  - 将来リターン・IC（Spearman）・統計サマリー
- AI（OpenAI）
  - ニュース NLP による銘柄別センチメントスコア化（ai_scores テーブルへ保存）
  - マクロニュースと ETF ma200 を合成した市場レジーム判定（bull/neutral/bear）
- ツール
  - 環境設定ウィザード（.env 生成）: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report`

---

## セットアップ手順

前提
- Python 3.10+（型記法や union types を使用しているため）を推奨。3.11 を推奨。

1. リポジトリをクローン / 作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 推奨インストール例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がない場合は上記を個別インストールしてください）
   - 標準ライブラリの sqlite3 は OS に付属します。

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に）
   - 自動ロードはデフォルトで有効。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - 本番相当の厳格チェックをしたい場合は --strict を付ける

6. データディレクトリの作成（必要に応じて）
   - デフォルトでは data/ 以下に DB / フラグファイル等を作成するため、適切な権限で実行してください。

環境変数（主な必須・任意）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意/重要
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker と data/paper_trading.db を使用
    - live: 実口座で発注
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視用 DB デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI API を使う機能に必要
  - LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL など

注意:
- .env は絶対にリポジトリにコミットしないこと（config_setup も同旨の注記あり）。

---

## 使い方（実行例）

基本的な起動例はモジュールとして実行します。

1. 環境設定の作成・検証
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いで exit(1)

2. ExecutionEngine の起動（発注エンジン）
   - デフォルト（KABUSYS_ENV により paper/live を切り替え）
   - python -m kabusys.run_execution
   - 動作
     - プロセス優先度を high に設定
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
     - 起動前に data/stop_requested.flag が存在すると起動しない
     - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

3. Monitoring の起動（定期監視）
   - python -m kabusys.run_monitoring
   - 振る舞い
     - Settings.sqlite_path（監視 DB）に接続してテーブルを初期化
     - DuckDB も接続（Settings.duckdb_path）
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
     - 停止フラグ: プロジェクトルート/data/stop_requested.flag を置くと監視ループが終了
     - 監視は本番 sqlite_path を参照（環境に依存せず本番 DB を使う設計）

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション
     - --db PATH を使って PAPER_TRADING_SQLITE_PATH を上書き可能

5. ライブラリ的な利用（例）
   - Python スクリプト / REPL 内で:
     - from kabusys.portfolio import select_candidates, calc_position_sizes, ...
     - from kabusys.research import calc_momentum, calc_volatility, calc_value
     - from kabusys.ai import score_news
   - OpenAI を使う機能は OPENAI_API_KEY を環境変数か関数引数に渡す必要あり。

6. Kill / Stop の運用
   - KillSwitch が発動すると data/kill.flag が書き込まれ、ExecutionEngine は起動時および運用中に kill.flag を検知して停止する仕組み
   - 管理用停止（安全にプロセスを終わらせたい場合）は data/stop_requested.flag を作成すると run_* スクリプトが検知して終了する

7. ロギング
   - 共通のロギング設定ユーティリティを使用（kabusys.utils.logging_setup.setup_logging）
   - デフォルトログディレクトリ: logs/
   - 日次ローテーション・30日保存。ログレベルは LOG_LEVEL 環境変数で設定可能

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 起動前に設定を検証する CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数計算（単元丸め・aggregate cap 等）
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュースを OpenAI でセンチメント評価し ai_scores に保存
    - regime_detector.py      — ETF + マクロニュースで市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite ベースの監視 DB 層（テーブル初期化・CRUD）
    - system_monitor.py       — CPU/メモリ/Disk・データ鮮度・プロセス監視
    - trade_monitor.py        — 注文関連の監視（滞留・異常検出） ※実装参照
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch ロジック（kill.flag の作成）
    - monitoring_engine.py    — 各 Monitor を束ねるランナー
    - alert_manager.py        — （通知送信機能、実装参照）
  - execution/
    - execution_engine.py     — 実行エンジン本体（run_session 等）
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文永続化（SQLite）
    - broker_factory.py       — ブローカークライアント生成（Mock/Live 分岐）
    - reconciler.py           — 発注整合処理
    - risk_manager.py         — 実行時リスク管理（Rate limit, circuit breaker 等）
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - data/                    — 実行時に作成される DB / フラグファイル類（data/monitoring.db 等）

---

## 運用メモ / 注意点

- Paper Trading と本番 DB は分離すること。paper_trading モード時は `PAPER_TRADING_SQLITE_PATH` を使用します。
- .env は秘匿情報（トークン・パスワード）を含むため絶対にバージョン管理に含めないでください。
- OpenAI 等の外部 API を利用する機能は API キーの漏洩に注意。API 呼び出しは失敗時にフォールバックする実装ですが、課金やレート制限等は運用で配慮してください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで動作を継続します（ログ設定は冪等）。
- プロセス優先度設定は OS の制約により権限エラーが出る場合があります。失敗時は警告が出力され処理は継続します。
- DuckDB/SQLite のスキーマやマイグレーションは monitoring_db.init_monitoring_db 等で自動対応する箇所がありますが、運用環境ではバックアップを推奨します。

---

## よく使うコマンドまとめ

- .env を作る（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き（例: MONITOR_POLL_INTERVAL=30）
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- Python REPL でモジュールを利用
  - python -c "from kabusys.portfolio import select_candidates; print(select_candidates([]))"

---

必要な情報や、README に追記してほしい実運用手順（systemd / supervisor のユニット例、Dockerfile、CI 設定など）があれば教えてください。README をそれに合わせて拡張します。
# KabuSys — 日本株自動売買システム（簡易 README）

このリポジトリは、研究・ポートフォリオ構築・実行・監視を含む日本株向け自動売買システムの一部実装を含みます。ここではプロジェクト概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめます。

注意: 実行には外部ライブラリ（duckdb, psutil, openai など）が必要です。実行前に .env を正しく設定し、設定検証ツールで確認してください。

## プロジェクト概要
- 目的: 日本株の自動売買ロジック（シグナル生成・銘柄選定・ポジションサイズ算出等）と、それを支える実行エンジン、監視・アラート、研究ユーティリティを提供する。
- 設計の特徴:
  - 環境変数 / .env による設定管理
  - 実行環境モード（development / paper_trading / live）に応じた動作切替
  - 実行（ExecutionEngine）と監視（MonitoringEngine / SystemMonitor 等）の分離
  - DuckDB を使った分析用 DB、SQLite を監視ログやペーパートレード用に使用
  - OpenAI を使ったニュース NLP / レジーム判定機能（任意）

## 主な機能一覧
- 実行関連
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの切替（paper_trading モードでは MockBrokerClient を利用して専用 DB に記録）
  - 注文管理・リスク管理・リコンシリエーション等（Execution 側コンポーネント群）

- 監視関連
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度・プロセス生存監視
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視（kill flag の発動可能）
  - KillSwitch / AlertManager による自動停止・通知連携
  - run_monitoring.py：単純ポーリングスクリプト（MONITOR_POLL_INTERVAL で間隔変更可能）

- ポートフォリオ構築（純粋関数）
  - 候補選定 / 等重・スコア重み配分
  - セクター制限、レジーム乗数計算
  - ポジションサイズ計算（単元株丸め、リスクベース、集約キャップ処理）

- 研究・分析
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）等の統計ツール
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

- AI（任意）
  - ニュース NLP（OpenAI）による銘柄ごとのセンチメントスコア化（kabusys.ai.news_nlp）
  - マクロ + MA200 を用いた市場レジーム判定（kabusys.ai.regime_detector）

## セットアップ手順（基本）
1. リポジトリをクローン / 取得し、Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai
   - 追加（開発・検証用）: PyYAML（config 検証時に YAML の構文チェックを行う場合）
     - pip install PyYAML

3. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話式で主要な環境変数を設定して .env を生成します。
   - もしくは .env.example を参考に手動作成

4. 設定の検証
   - python -m kabusys.validate_config
   - 必須環境変数などに問題がないか確認。--strict を付けると警告もエラー扱いになります。

5. データディレクトリの準備（任意）
   - デフォルトでは data/ 以下にファイルが作成されます。必要に応じてディレクトリを作成してください。
   - 例: mkdir -p data

## 主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 主要（任意・デフォルト値あり）
  - KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
    - paper_trading: MockBroker を使用し、ペーパートレード専用 DB に記録
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE — paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を利用する場合）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH — PID / Kill flag の保存パス（デフォルト data/execution.pid / data/kill.flag）

## 使い方（コマンド例）
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBroker を利用し data/paper_trading.db に結果を記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動しません。
    - 停止は data/stop_requested.flag を作成するとスレッド内で検出して停止します。

- 監視スクリプト（SystemMonitor の単体ループ）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
    - 監視は本番 sqlite_path（SQLITE_PATH）を常に使用します（監視データは環境に依存しない）。
    - 停止は data/stop_requested.flag の作成で行います。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定例:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定して各関数をプログラムから呼び出す:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DB（DuckDB）の raw_news / prices_daily 等を参照します。APIキーが未設定だと例外になります。

## 運用上の注意
- Kill Switch:
  - RiskMonitor → KillSwitch の評価で data/kill.flag が作成されると ExecutionEngine 停止を促します。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（推奨: 0）。
- PID / Stale PID:
  - Execution 起動時に PID ファイル（data/execution.pid）を作成します。SystemMonitor は stale PID を検出して削除します。
- 監視データベース:
  - monitoring_db.init_monitoring_db() は冪等でテーブルを作成・必要なマイグレーション（カラム追加）を行います。
- OpenAI 呼び出し:
  - ネットワーク・RateLimit・5xx 等はリトライ処理が入っていますが、API キー管理やコストに注意してください。

## ディレクトリ構成（主要ファイル）
（以下は src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI を使った銘柄スコア）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の作成 / 管理
    - monitoring_engine.py   — 複数 Monitor を束ねるループ（テスト用 run_once / 本番 run）
    - alert_manager.py       — （未掲載詳細）アラート送信管理
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数算出・集約キャップ処理
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - utils/
    - process_priority.py    — プロセス優先度 & CPU affinity 設定ユーティリティ
  - monitoring/ (上記)
  - execution/ (一部の実装参照)
    - order_repository.py
    - order_manager.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
    - order_repository.py

（注）README に含まれない実装ファイルや補助スクリプトがさらに存在する可能性があります。上記はコードベースの主要モジュールを抜粋したものです。

## よくある操作例
- 環境の初期化（.env 作成 → 検証 → 実行）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.run_execution  （本番では supervisord / systemd 等で管理推奨）
  - python -m kabusys.run_monitoring

- Paper Trading レポート（任意期間）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

## 開発者向けメモ
- 自動で .env を読み込む仕組みは config.py に実装されています。テスト時に自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を用いるモジュール（research, ai）は DB のスキーマ（prices_daily, raw_financials, raw_news, ai_scores, market_regime 等）に依存します。テスト用の DuckDB を用意してから関数を呼び出してください。
- process_priority.set_process_priority() は psutil を利用して OS ごとに処理を吸収しています。通常は起動スクリプトの最初で呼び出されます。

---

この README はコードベースの主要点をまとめた簡易版です。各モジュール内のドキュメントストリング（docstring）や CLI ヘルプを参照するとより詳細な使い方や引数説明が得られます。必要ならば、より詳細なインストール手順・運用ドキュメント・アーキテクチャ図などを追加で作成します。必要な箇所を指定してください。
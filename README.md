# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ + 実行スクリプト群）。

この README はコードベースから生成しています。主要な用途は本番／ペーパートレード環境での ExecutionEngine と、システム監視（Monitoring）・アラート・AI 補助機能の提供です。

## プロジェクト概要
- 自動売買のコアロジック（ポートフォリオ構築、ポジションサイズ計算、リスク調整）を純粋関数として提供。
- ExecutionEngine による発注処理（本番は kabuステーション、ペーパートレードはモック）を想定。
- Monitoring サブシステムでシステム状態・注文状況・リスク（ドローダウン、ポジション数等）を定期チェックし、kill flag による安全シャットダウンやアラート送信を行う。
- Research / AI モジュールでファクター計算・特徴量解析・ニュースセンチメント評価（OpenAI）を提供。
- データ永続化は SQLite（監視・発注履歴等）と DuckDB（時系列・分析用）を想定。

## 主な機能一覧
- 実行（Execution）
  - Broker クライアントの抽象化（本番 / paper_trading 切替）
  - Order 管理・リコンシリエーション・リスク管理
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス生存チェック
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限検出
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）出力
  - MonitoringEngine: 定期ポーリングとアラート統合
- ポートフォリオ
  - 候補選定、等重・スコア重み、セクター制限、レジーム乗数、株数決定（単元丸め・集計スケール）
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 前方リターン、IC（スピアマン）、統計サマリー
- AI
  - ニュース NLP（OpenAI）による銘柄センチメントスコア生成（ai_scores）
  - 市場レジーム判定（ma200 + マクロセンチメント）
- ユーティリティ
  - 対話式 .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

## 前提 / 必要パッケージ
- Python 3.10+
- 必須パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
- 開発 / 推奨:
  - PyYAML（config YAML のバリデーション用。なくても動作するが警告が出ます）
- インストール例:
  - pip install duckdb psutil openai pyyaml

（実際の requirements はプロジェクトに requirements.txt がある場合そちらを参照してください）

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. Python 仮想環境の作成とパッケージインストール
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
   - pip install --upgrade pip
   - pip install duckdb psutil openai pyyaml

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに従い必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定
   - 生成された .env は Git にコミットしないでください

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. ディレクトリ準備（必要に応じて）
   - data/ や logs/ は自動作成されることがありますが、権限等の問題で手動作成する場合:
     - mkdir -p data logs

## 主要な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）、デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject、デフォルト: instant）

## 使い方（実行例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 実行開始時にプロセス優先度が "high" に設定されます
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで実行中スレッドに検知され停止します
  - ペーパートレード時は settings.is_paper が True になり、data/paper_trading.db を使用（本番 DB と分離）

- Monitoring を起動（監視ループ）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を使って監視テーブルを保持します（KABUSYS_ENV に依存せず）
  - 停止は data/stop_requested.flag を作成するか KeyboardInterrupt

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も利用可）

- AI / リサーチ機能（ライブラリとして利用）
  - ニューススコア生成:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...") など
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- ロギング
  - 全スクリプトは kabusys.utils.logging_setup.setup_logging を使い、logs/<app_name>.log を日次ローテートで出力します（既定 logs/、30日保持）

## 停止と Kill Switch
- ExecutionEngine 停止要求:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して順次停止します
- Kill Switch:
  - RiskMonitor の判定（ドローダウンやポジション上限）により KillSwitch が data/kill.flag を書き込みます
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では 0 を推奨

## ディレクトリ構成（抜粋）
以下は主要ファイルの概観です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                   # 環境変数・Settings 管理、自動 .env ロード
  - config_setup.py             # .env 対話式ウィザード
  - validate_config.py          # 設定検証 CLI
  - run_execution.py            # ExecutionEngine 起動スクリプト
  - run_monitoring.py           # Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (※実装ファイルがある想定)
    - kill_switch.py
    - alert_manager.py (※実装ファイルがある想定)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（上記はコードベースの代表的なファイルを抜粋しています。プロジェクト全体の完全なツリーは git ls-files 等で確認してください）

## 開発メモ / 注意点
- 型ヒントで X | Y の表記を使っているため Python 3.10+ が必要です。
- DuckDB / SQLite を利用するため、DB ファイルのパスや権限に注意してください。
- OpenAI を使う機能（news_nlp / regime_detector）は API キーが必要で、API 失敗時はフェイルセーフにより安全なフォールバックを行う設計になっています（例: macro_sentiment=0.0）。
- 本番稼働時は KABUSYS_ENV=live を設定し、LINE 通知や Kill Switch 設定を含む全設定を厳密に確認してください。
- .env は機密情報を含むため決してリポジトリにコミットしないでください。

---

この README はコード内ドキュメントからの要約です。運用時は config/*.yaml（存在する場合）や既存の scripts を参照し、環境に合わせて .env を作成・検証してください。質問や補足があれば教えてください。
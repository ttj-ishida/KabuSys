# KabuSys README

日本株自動売買システム KabuSys のリポジトリ向け README（日本語）。

この README はリポジトリ内のコード構成に基づき、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成、および注意点をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを想定したコードベースです。システムは以下の主要コンポーネントで構成されています。

- ExecutionEngine: 注文の作成・管理・送信を担うエンジン（本番／ペーパートレード切替対応）
- Monitoring: システム状態、注文滞留、リスク（ドローダウン・ポジション上限）を監視し、アラートや Kill Switch を管理
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算、セクター制限、レジーム調整
- Research: ファクター計算（モメンタム・バリュー・ボラティリティ等）、特徴量探索、IC 計算
- AI モジュール: ニュースを LLM（OpenAI）で解析して銘柄別スコアを生成、及びマクロニュースと MA を組み合わせた市場レジーム判定
- tools: ペーパートレード検証レポート等のユーティリティスクリプト
- config: 環境変数読み込み、対話式 .env ウィザード、設定検証 CLI

設計方針の一部：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により挙動分岐）
- DuckDB を分析用に利用、SQLite を監視や発注ログ用に利用
- LLM（OpenAI）呼び出しは失敗時にフォールバック・サニティチェックを行いフェイルセーフ化

---

## 主な機能一覧

- 起動モジュール
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV により MockBroker を利用）
  - run_monitoring.py：SystemMonitor の簡易ポーリング起動
- モニタリング
  - system_monitor: CPU/メモリ/ディスク、データ鮮度、実行プロセスチェック
  - trade_monitor: 滞留注文検出、約定価格異常検出
  - risk_monitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - monitoring_engine: 上記を束ねてポーリング／通知／Kill Switch 評価
  - monitoring_db: 監視ログ用の SQLite スキーマ作成と読み書きユーティリティ
- ポートフォリオ構築
  - 候補選定（スコア順）、等配分 / スコア加重配分、リスクベース配分（株数算出）
  - セクターキャップ適用、レジーム乗数計算
- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（スピアマン順位相関）計算、ファクター統計サマリ
- AI
  - news_nlp: raw_news を集約し LLM で銘柄別センチメントを算出 → ai_scores へ書き込み
  - regime_detector: ETF (1321) の MA200 乖離＋マクロニュースの LLM スコアで日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを生成

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントと一部ライブラリを想定）
- SQLite は標準ライブラリで利用
- 必要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時、任意）
インストール例:
  pip install duckdb psutil openai PyYAML

リポジトリルートに .env を配置して環境変数を設定します。対話式ウィザードを利用する場合:

  python -m kabusys.config_setup

主要な環境変数（必須／重要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使い data/paper_trading.db に記録
  - live: 本番
- OPENAI_API_KEY: AI モジュールを利用する場合に必須
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（ペーパートレード時のフィルモード: instant|partial|never|reject）
- LOG_LEVEL（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）

初期化・検証:
- .env を作成したら設定検証を実行:
  python -m kabusys.validate_config
  --strict オプションで警告も失敗扱いにできます。

データディレクトリ:
- デフォルトの DB / PID / フラグファイルは data/ 以下に置かれます。起動時に親ディレクトリが無ければ自動作成されることがありますが、権限などには注意してください。

---

## 使い方

基本的な起動例（モジュールとして実行）:

- ExecutionEngine を起動（本番／ペーパートレードは KABUSYS_ENV に依存）:

  python -m kabusys.run_execution

  特記事項:
  - 起動時にプロセス優先度を "high" に設定します（psutil による実装。権限不足時はスキップされます）。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録されます。
  - 停止はデーモン内の stop フラグ（data/stop_requested.flag）を作成、または ExecutionEngine 自身が Kill Switch（data/kill.flag）を検出して停止します。

- Monitoring（SystemMonitor の簡易ループ）を起動:

  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定（デフォルト 60 秒）。
  - Monitoring は常に本番用の sqlite_path を使用して監視ログを保存します（環境にかかわらず）。

- ペーパートレード検証レポートを生成:

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能（デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- .env の作成（対話式）:

  python -m kabusys.config_setup

- 設定検証:

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

API 系関数の利用（プログラムから呼び出す場合）:
- ai.news_nlp.score_news(conn, target_date, api_key=None)
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
- research モジュールのファクター計算関数は DuckDB 接続（duckdb.connect(...)）を引数に受け取ります。

停止と Kill Switch:
- Monitoring は内部で KillSwitch を評価し、条件に合致する場合 Settings.kill_flag_path（デフォルト data/kill.flag）に理由を記したフラグを書きます。ExecutionEngine はこのフラグを検出して安全に停止します。
- すでに kill.flag が存在していると ExecutionEngine は動作を開始しない設定にできます（KILL_FLAG_CLEAR_ON_START を 1 にしている場合は起動時に自動でクリアされますが、本番では 0 推奨）。

ログレベル:
- LOG_LEVEL 環境変数で変更可能（例: DEBUG, INFO, WARNING）

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル／ディレクトリは以下の通りです（src/kabusys 以下を抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数読込 / Settings
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py        — （アラート送信ロジック、実装ファイルあり）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - process_priority.py
    - (その他 execution / data / strategy パッケージ等が存在する想定)

監視 DB（SQLite）スキーマ（monitoring_db.py に定義）
- system_status: CPU/メモリ/ディスク/プロセス状態 の履歴
- trade_logs: 発注・約定イベントログ（latency_ms 列含む）
- positions: 現在ポジション
- risk_logs: リスクイベント（DRAWDOWN_ALERT、PRICE_ANOMALY 等）
- dashboard: 集計（id=1 の単一行）

---

## 注意事項 / トラブルシューティング

- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定だと起動前に validate_config で検出されます。まず .env を作成してください。
- OpenAI を利用する機能（news_nlp/regime_detector）は OPENAI_API_KEY が必要です。無い場合はエラーか例外が投げられます（関数内で ValueError を送出）。
- PyYAML が無いと config/*.yaml の中身検証はスキップされます（validate_config が警告）。
- DuckDB / SQLite のファイルパス権限に注意してください。デフォルトは data/ 配下です。
- psutil によるプロセス優先度設定や CPU affinity は権限不足や OS 非対応時に警告を出しスキップします。
- run_execution / run_monitoring のループ停止は data/stop_requested.flag の作成で行えます。Kill Switch は data/kill.flag を使用します。
- DB マイグレーション（monitoring_db.init_monitoring_db）は冪等処理となるよう実装されていますが、重大なスキーマ変更がある場合は手動確認を行ってください。

---

## その他

- 開発向けにローカルで素早く動かす場合は KABUSYS_ENV=development を使用し、発注処理を無効化するかモックを利用してください。
- ドキュメント化されている設計（例: PortfolioConstruction.md, StrategyModel.md）が存在する場合は合わせて参照してください（リポジトリに含まれている想定）。

---

この README はコードベースの現状の主要機能と利用方法をまとめたものです。実際の運用やデプロイを行う場合は環境（権限、ネットワーク、API 料金、レート制限、リトライポリシー）の確認と十分なテストを行ってください。質問や追加のドキュメント化が必要でしたらお知らせください。
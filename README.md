# KabuSys

日本株自動売買システムのモジュール群。ポートフォリオ構築、発注実行（実口座 / ペーパートレード）、監視、リサーチ、AI ベースのニュース／レジーム判定などを含むライブラリ兼起動スクリプト群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な主要機能を分離したモジュール群です。主な責務は以下の通りです。

- 発注実行エンジン（ExecutionEngine） — ブローカークライアントを介した発注、リスク管理、注文管理、再調整（Reconciler）等
- 監視（Monitoring） — システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期チェックし、Kill Switch を発動してエンジン停止へ繋げる
- ポートフォリオ構築（Portfolio） — 候補選定、重み計算、ポジションサイズ決定、セクター制約等の純粋関数群
- リサーチ（Research） — DuckDB を用いたファクター計算、将来リターン / IC 計算、統計サマリー
- AI（news_nlp / regime_detector） — OpenAI を用いたニュースセンチメント評価や市場レジーム判定
- ユーティリティ — ログ設定、プロセス優先度設定、環境設定ウィザード / 検証ツール 等
- ツール — ペーパートレード検証レポート生成など

設計方針として、発注周りとリサーチ／AI 処理は明確に分離され、DB（SQLite / DuckDB）を通じたデータの永続化と再現性の確保に重きを置いています。

---

## 主な機能一覧

- Execution
  - 実口座（kabuステーション）または paper_trading（モックブローカー）での発注
  - RiskManager によるポジション上限・資金利用率等の制御
  - OrderManager / OrderRepository による注文管理・ログ保存
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態/データ鮮度監視
  - TradeMonitor: 発注ログの整合性チェック（滞留注文・異常約定など）
  - RiskMonitor: ドローダウン・ポジション上限の検出。必要に応じて Kill Switch を書き込み
  - MonitoringEngine: 定期ポーリングとアラート発行
- Portfolio
  - 候補選別（スコア順）、等金額・スコア加重重み付け
  - セクター制約適用、レジーム乗数
  - 株数決定（リスクベース／等分／スコアベース）、単元株丸め、aggregate cap 対策
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計
- AI
  - ニュース集合の LLM（OpenAI）評価による銘柄別スコアリング（ai_scores テーブル）
  - マクロニュース + ETF MA200乖離を組合わせた市場レジーム判定（bull/neutral/bear）
  - API エラー時のリトライ・フォールバック設計
- Utilities & Tools
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - ログ設定ユーティリティ（TimedRotatingFileHandler）
  - プロセス優先度/CPU affinity 設定ユーティリティ

---

## セットアップ手順

※ 開発環境や OS に依存する部分（psutil の優先度設定など）があります。まずは仮想環境を作成して依存パッケージをインストールしてください。

1. リポジトリをクローン / ソース配置
   - 本 README 想定のルートには `src/` 以下が配置されています。

2. 仮想環境作成（任意）
   - python >= 3.10 推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
   - 任意:
     - PyYAML（config/*.yaml の内容検証に必要）
   - pip install でインストールしてください。プロジェクトに requirements ファイルがある場合はそれを使用してください:
     - pip install duckdb psutil openai PyYAML

4. パッケージをインストール（開発モード）
   - プロジェクト root に pyproject.toml がある場合:
     - pip install -e .

5. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または .env.example を参考に `.env` を作成して配置してください。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（主なもの）:
     - KABUSYS_ENV: development | paper_trading | live
     - OPENAI_API_KEY: OpenAI API を使う機能で必須
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（instant|partial|never|reject、paper_trading 時）
     - LOG_LEVEL（DEBUG|INFO|...）
     - LOG_DIR（ログ出力ディレクトリ）

6. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

7. 初回 DB / ディレクトリ
   - スクリプト実行時に必要なディレクトリ（data/、logs/など）は自動作成されるよう設計されていますが、権限やパスを事前に確認してください。

---

## 使い方（起動・主要コマンド）

- ExecutionEngine（取引エンジン）起動
  - 実行:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、デフォルトで `data/paper_trading.db` を使用して本番 DB と完全分離します。
    - 起動時に `data/stop_requested.flag` が存在する場合は起動をせず終了します。
    - 実行中は PID ファイル（`data/execution.pid` デフォルト）を作成します。
    - 停止させるには監視側からの kill.flag（data/kill.flag）や stop_requested.flag の作成等で制御できます。

- Monitoring（監視プロセス）起動
  - 実行:
    - python -m kabusys.run_monitoring
  - 挙動:
    - SQLite（monitoring 用）へ接続し、SystemMonitor のポーリングを行います。
    - 環境に関わらず monitoring は本番 sqlite_path（Settings.sqlite_path）を参照します。
    - ポーリング間隔:
      - デフォルト 60 秒
      - 環境変数 MONITOR_POLL_INTERVAL で上書き可（例: export MONITOR_POLL_INTERVAL=30）
    - 停止:
      - リポジトリルートの `data/stop_requested.flag` を作成するとループを終了します。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1) になります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能（デフォルト: data/paper_trading.db）
  - 成功率・稼働率・レイテンシ等を集計し PASS/FAIL を出力します。

- AI 関連（プログラムから呼び出す API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡してニュースセンチメントを ai_scores テーブルへ書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ書き込みます。
  - どちらも OPENAI_API_KEY を環境変数または引数で指定する必要があります。

---

## 停止・Kill Switch の動作

- run_execution / ExecutionEngine
  - 実行中に `data/kill.flag` が書き込まれると KillSwitch によって ExecutionEngine 側で検出・停止される設計です（KillSwitch は `Settings.kill_flag_path` を参照）。
  - run_execution 自体は `data/stop_requested.flag` を監視しており、存在すればエンジンを起動せず終了します（また run_execution 実行中は同フラグを検知して engine.stop() を呼びます）。

- run_monitoring
  - `data/stop_requested.flag` が存在すると監視ループを終了します（スムーズな停止）。

---

## 主要環境変数（まとめ）

- 必須（アプリで必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb（DuckDB ファイル）
  - SQLITE_PATH: data/monitoring.db（監視用 SQLite）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - PID_FILE_PATH: data/execution.pid（PID ファイル）
  - KILL_FLAG_PATH: data/kill.flag（Kill Switch 参照）
- AI
  - OPENAI_API_KEY: OpenAI を利用する機能で必須
- その他
  - LOG_LEVEL: DEBUG|INFO|...
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効）
  - PAPER_FILL_MODE: ペーパートレード時の注文約定挙動（instant|partial|never|reject）

---

## トラブルシューティング / 注意事項

- ログディレクトリ作成失敗時は標準出力のみでログを出力するフォールバックがあります（警告を出力）。
- psutil によるプロセス優先度設定は OS に依存し、権限不足で失敗する場合は警告が出ます（操作はスキップされます）。
- OpenAI 呼び出しは API エラー / レート制限に対して指数バックオフでリトライします。大量 API コール時はキーのレート制限に注意してください。
- DuckDB / SQLite スキーマは init_monitoring_db() 等で冪等に作成・マイグレーションされますが、既存データのバックアップを推奨します。
- .env は絶対にリポジトリにコミットしないでください（config_setup の出力にも警告があります）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル / モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - config_setup.py                  — .env 対話式ウィザード
  - validate_config.py               — 設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                    — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py             — 市場レジーム判定（OpenAI + MA200）
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数決定 / 集計上限 / 単元丸め
    - risk_adjustment.py             — セクター上限 / レジーム乗数
  - research/
    - factor_research.py             — Momentum/Value/Volatility 等
    - feature_exploration.py         — 将来リターン / IC / 統計
  - monitoring/
    - monitoring_db.py               — SQLite スキーマ・DB 操作ラッパ
    - system_monitor.py              — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py               — (trade 関連チェック)  ※実装ファイルあり
    - risk_monitor.py                — ドローダウン & ポジション監視
    - kill_switch.py                 — kill.flag の書き込み/評価
    - monitoring_engine.py           — 監視コンポーネント統合
    - alert_manager.py               — (アラート送信ラッパ) ※実装ファイルあり
  - execution/
    - execution_engine.py            — ExecutionEngine（主実行ループ）
    - order_manager.py               — 注文管理
    - order_repository.py            — 注文ログの永続化
    - risk_manager.py                — リスク管理ロジック
    - reconciler.py                  — 注文再調整
    - broker_factory.py              — ブローカークライアント生成（Mock含む）
  - monitoring/monitoring_db.py      — 監視 DB 初期化・操作
  - utils/
    - logging_setup.py               — 統一ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity
  - data/                            — 実行時に用いる SQLite/DuckDB/log 等（デフォルト）
  - logs/                            — ログ出力先（デフォルト）

（上のリストは主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 開発者メモ・拡張案

- 将来的に単元株数（lot_size）を銘柄マスタへ持たせるなどの拡張を想定した設計です。
- AI 部分は OpenAI SDK の変更に備え、呼び出し部分を簡単に差し替えられるよう分離しています（テスト時は内部呼び出しをモック可能）。
- DuckDB を用いたリサーチ機能はデータサイズ増大時に性能劣化し得るため、クエリ最適化やパーティショニングを検討してください。

---

README で不足している点や、特定のモジュール（ExecutionEngine の起動オプション、Broker の設定、アラート送信先の構成など）について詳細が必要であれば、その点を教えてください。必要に応じて起動例や .env テンプレート、運用手順書を追加で作成します。
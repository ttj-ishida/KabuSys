# KabuSys

日本株向け自動売買システムのコードベース（README）。  
このドキュメントはプロジェクト全体の概要、主要機能、セットアップ方法、実行方法、ディレクトリ構成を日本語でまとめたものです。

> 注意: 実運用時は .env に秘密情報（API トークン、パスワード等）を絶対にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買および関連処理（データ処理、ファクター計算、ポートフォリオ構築、監視、ペーパートレード検証、AI ベースのニュース分析など）を行うモジュール群です。  
主要な実行コンポーネントは以下です。

- ExecutionEngine: 発注ロジック・リスク管理・注文管理を行うエンジン
- Monitoring: システム状態、注文ログ、リスク指標を定期監視しアラート／Kill Switch を制御
- Research: DuckDB 上の市場データからファクター・統計分析を行う研究用モジュール
- Portfolio: 候補選定、配分・ポジションサイズ計算、セクター制限など
- AI モジュール: ニュースの NLP スコアリング（OpenAI を利用）、市場レジーム判定
- Tools: ペーパートレードの検証レポート作成スクリプト 等

設計上のポイント:
- 環境変数 / .env で動作設定を行う
- paper_trading モードは本番 DB と分離（paper DB を使用）
- 監視は本番 monitoring DB（sqlite）に記録
- OpenAI、DuckDB、psutil 等の外部ライブラリを利用

---

## 機能一覧（主なもの）

- 実行（Execution）
  - Broker クライアント抽象化（本番 / モック）
  - リスク管理（最大ポジション、資金利用率、サーキットブレーカー等）
  - 注文管理・約定ログ記録
  - PID / stop フラグ管理（data/execution.pid, data/stop_requested.flag）

- 監視（Monitoring）
  - CPU / メモリ / ディスク使用率監視
  - プロセス生存チェック（Execution が生きているか）
  - データ鮮度チェック（prices_daily 等の最新日付）
  - トレードログ分析（滞留注文検出、約定価格異常など）
  - リスク監視（ドローダウン・ポジション上限）と Kill Switch 書き込み
  - 監視結果は SQLite（data/monitoring.db デフォルト）へ永続化

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 上）
  - 将来リターン計算・IC（情報係数）計算・統計サマリ

- ポートフォリオ（Portfolio）
  - シグナルから候補選定、等重/スコア重み、リスクベースの株数決定
  - セクター上限適用、レジーム乗数（bull/neutral/bear）

- AI（OpenAI）
  - ニュースの銘柄別センチメントスコア付与（ai_scores テーブルへ書き込み）
  - マクロニュース＋ETF MA 乖離を組み合わせた市場レジーム判定（market_regime テーブルへ書き込み）
  - 両機能とも OpenAI（gpt-4o-mini など）を利用、API キー必須

- ツール
  - Paper Trading 検証レポート生成（期間指定で成功率・レイテンシ等を集計）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール  
   主要依存（例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   - その他: sqlite3 は標準ライブラリ

   例:
   - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt がある場合はそれを利用してください:
   - pip install -r requirements.txt

4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードが .env を生成・更新します（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など必須項目あり）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます

6. データディレクトリ等
   - デフォルトの DB やログは以下パス（プロジェクトルート基準）:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/ （LOG_DIR で上書き可）
   - 必要に応じてディレクトリを作成（logging 設定は自動で作成を試みますが、権限等で失敗することがあります）

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- LOG_LEVEL / LOG_DIR: ログ出力レベル / ログディレクトリ
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

その他は .env.example を参照してください。

---

## 使い方（主要スクリプト・コマンド）

- 環境設定ウィザード（.env の作成/編集）
  - python -m kabusys.config_setup

- 設定検証（起動前のチェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（手動／デーモン等で実行）
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid に PID を書き、停止は data/stop_requested.flag を作成することで実行ループを停止できます。
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い paper_trading DB（data/paper_trading.db）へ記録します（本番 DB と分離）。

- Monitoring を起動（ポーリングループ）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視ループはプロジェクトルートの data/stop_requested.flag により停止できます（存在チェック）。
  - 監視は monitoring DB（sqlite_path）に書き込みます。Monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を使用します。

- Paper Trading 検証レポート生成（コマンドラインツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで db ファイル指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング / レジーム判定（ライブラリ呼び出し）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数引数）。
  - 例（Python REPL やスクリプト内で）:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
    - score_regime(conn, target_date, api_key="...")

- ライブラリ関数（研究・ポートフォリオ等）
  - kabusys.research.calc_momentum/coef などを DuckDB 接続と target_date を渡して利用可能
  - kabusys.portfolio の関数群は純粋関数で DB 参照せずテストしやすい

---

## 停止 / Kill Switch / フラグファイル

- 停止フラグ（run_execution / run_monitoring のループ停止）
  - data/stop_requested.flag を作成すると実行ループは検知して安全に終了します。
  - 実行中の ExecutionEngine は PID ファイル（data/execution.pid）を持ちます。

- Kill Switch（自動的な停止要求）
  - 監視モジュール（KillSwitch）が重大事象（ドローダウン超過、ポジション上限超過など）で data/kill.flag を書き込みます。
  - ExecutionEngine は起動時や監視で kill.flag の存在を見てプロセス停止や起動中止を行います。
  - Settings.kill_flag_clear_on_start が `1` の場合は起動時に kill.flag を自動でクリアします（本番では `0` 推奨）。

---

## ロギング

- setup_logging() によって、コンソール（stdout）と日次ローテートされたファイル出力が設定されます。
- デフォルトログディレクトリ: logs/
- ログファイル名はアプリ名プレフィックス（例: execution → logs/execution.log）
- LOG_LEVEL / LOG_DIR で上書き可能

---

## 主要ディレクトリ構成

（プロジェクトルート / src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（自動 .env ロード等）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - execution/               — ExecutionEngine 関連（BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (非コード、ランタイム / DB 保存先の既定)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid
    - stop_requested.flag
    - kill.flag
  - config/ (YAML 設定テンプレート等)
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml

---

## 開発・運用時の注意点

- 本番環境 (KABUSYS_ENV=live) では .env 内の設定を特に慎重に確認してください（validate_config の警告を確認）。
- paper_trading モードは発注を模擬し、本番 DB を汚さないよう専用 DB に記録します。必ず separation が効いていることを確認してください。
- OpenAI を利用するスクリプトは API 使用量・レスポンス時間に注意してください。リトライやバックオフが実装されていますが、API レート制限により部分失敗が発生する可能性があります。
- ログディレクトリの作成に失敗するとファイル出力は無効化されコンソールのみになります。権限・ディスク容量に注意してください。
- DuckDB / SQLite のパスは Settings で指定可能です。複数環境で運用する場合は .env で適切に分離してください。

---

## よく使うコマンドまとめ

- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要であれば、README に含めるサンプル .env テンプレートや systemd/cron 用の起動例、Dockerfile・docker-compose 構成例、CI 設定のテンプレートなども作成できます。どの情報を追加したいか教えてください。
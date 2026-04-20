# KabuSys

日本株向け自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、注文実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、AIを使ったニュースセンチメント評価などを含むモジュール群で構成されています。コードは主に純粋関数／DBアクセス層／起動スクリプトに分かれており、本番（live）／ペーパートレード（paper_trading）／開発（development）での挙動差分を環境変数で切り替えられます。

> 注: .env（認証情報等）を含む設定ファイルは絶対にリポジトリへコミットしないでください。

---

## 主な機能

- Execution（ExecutionEngine）
  - 実注文／ペーパートレード切替
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理（OrderManager / OrderRepository）
  - リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- Monitoring（監視）
  - システム稼働監視（CPU/MEM/DISK、プロセス生存）
  - 注文ログ・約定監視（trade_logs）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（フラグファイルでExecutionEngineを停止）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算（等金額・スコア加重）
  - セクター制限、レジーム乗数適用
  - 株数決定・単元丸め・投下資金制限
- Research（リサーチ）
  - Momentum / Volatility / Value ファクター計算（DuckDB参照）
  - 将来リターン・IC計算・統計サマリ
- AI（ニュースNLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント評価（ai_scores 登録）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定
- ユーティリティ
  - ロギング設定（日次ローテート）
  - プロセス優先度／CPU affinity 設定
  - .env 対話式ウィザード / 設定検証 CLI
  - Paper Trading 検証レポート生成ツール

---

## 前提（推奨環境）

- Python 3.10+
  - 型アノテーションの記法（`X | None`）があるため 3.10 以上を推奨します
- 必要な主なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML を検証する場合に任意で必要）
- SQLite（標準ライブラリで使用）
- ネットワークアクセス（kabuステーション API / OpenAI API を使う場合）

---

## セットアップ手順

1. リポジトリをクローン:
   git clone <repository-url>
2. 仮想環境を作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）:
   pip install duckdb psutil openai PyYAML
   （プロジェクトに requirements.txt があればそれを使用してください）
4. .env を作成:
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - または手動で環境変数を設定（下記参照）
5. 設定検証（任意）:
   python -m kabusys.validate_config
   - --strict を付けると WARNING も失敗扱いになります
6. データディレクトリの初期化（必要に応じて）
   - デフォルトでは data/ 以下を使用します（ログ: logs/）
   - 起動時に自動作成されますが、適切な権限を確認してください

---

## 必要な環境変数（主要なもの）

（`config_setup` を使うと対話式で設定できます）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 主要オプション
  - KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
  - PAPER_FILL_MODE — ペーパー注文の約定挙動（instant|partial|never|reject、デフォルト: instant）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
  - LOG_DIR — ログの保存先（デフォルト: logs/）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用、デフォルト: 60）

注意: .env は秘密情報を含むため Git にコミットしないでください。

---

## 実行方法（主要な CLI / モジュール）

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、デフォルトで data/paper_trading.db を使用して本番 DB と分離します
    - 起動時に data/stop_requested.flag があれば起動しません
    - 実行中は data/execution.pid を管理します
- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を参照）
    - data/stop_requested.flag によりループ終了
- 設定ウィザード（.env の生成）
  - python -m kabusys.config_setup
- 設定検証 CLI
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数でも DB を指定できます
- AI / リサーチ等の個別機能はライブラリとして import して使用できます
  - 例: from kabusys.ai import score_news
  - DuckDB 接続（duckdb.connect(...)）を渡して関数を呼ぶ形

---

## 運用上の注意

- 本番環境では KABUSYS_ENV=live を設定して慎重に運用してください。validate_config は本番向けの追加チェックをします。
- Kill Switch（data/kill.flag）を使うことで ExecutionEngine を強制停止できます。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です。
- OpenAI を利用する処理は API のレート制限や失敗を考慮した実装になっていますが、APIキーやコストの管理は運用側で行ってください。
- ログは logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。
- DB マイグレーション等は起動スクリプト内で必要なカラム追加（冪等）処理を行っています。

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理（自動 .env ロード）
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py    — Paper Trading 検証レポート
  - utils/
    - logging_setup.py                — ロギング設定ユーティリティ
    - process_priority.py             — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py                — 監視用 SQLite の永続化層
    - system_monitor.py               — システム状態・データ鮮度監視
    - trade_monitor.py                — 注文 / 約定の監視（ログ解析）
    - risk_monitor.py                 — ドローダウン / ポジション上限監視
    - monitoring_engine.py            — 各 Monitor を束ねるエンジン
    - kill_switch.py                  — フラグファイル方式の停止シグナル
    - alert_manager.py                — （別ファイルで実装される想定の）アラート送信管理
  - execution/
    - execution_engine.py             — 実行エンジン本体
    - order_manager.py                — 注文管理
    - order_repository.py             — DBアクセス（注文履歴）
    - broker_factory.py               — ブローカークライアント生成
    - reconciler.py                   — リコンシリエーション
    - risk_manager.py                 — 注文時のリスク制御
  - portfolio/
    - portfolio_builder.py            — 候補選定・重み計算
    - position_sizing.py              — 株数決定ロジック
    - risk_adjustment.py              — セクター制限・レジーム乗数
  - research/
    - factor_research.py              — ファクター計算（momentum/value/volatility）
    - feature_exploration.py          — 特徴量解析 / IC 計算
  - ai/
    - news_nlp.py                     — ニュースセンチメント評価（OpenAI）
    - regime_detector.py              — マクロ + ETF MA200 によるレジーム判定

data/ および logs/ はランタイムで作成・利用されます（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid）。

---

## 開発・拡張メモ

- DuckDB を使って大規模な市場データ（prices_daily / raw_financials / raw_news 等）を高速に集計する設計です。研究・テスト目的で SQLite を使うこともできますが、リサーチ機能は DuckDB を前提として最適化されています。
- AI 呼び出し箇所（news_nlp, regime_detector）は API 呼び出し（_call_openai_api）を内部関数に分離しており、ユニットテスト時はモックに差し替え可能です。
- 監視データは monitoring_db.py によって冪等に初期化・マイグレーションが行われます。schema 変更時はここに追記してください。

---

必要であれば、README に含める「サンプル .env（テンプレート）」「実行例ログ」「運用チェックリスト」などの追加セクションも作成できます。どの情報をさらに詳しくしたいか教えてください。
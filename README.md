# KabuSys

KabuSys は日本株向けの自動売買・リサーチ基盤です。  
ポートフォリオ構築、ポジションサイジング、監視（Monitoring）、実行エンジン（Execution）、AI を用いたニュース／レジーム評価、研究用ファクター計算などのコンポーネントを含みます。

Version: 0.1.0

---

## 概要

このリポジトリは以下の主要機能を持つモジュール群で構成されています。

- 実行エンジン (ExecutionEngine)：ブローカークライアント経由で注文を管理・発行するコンポーネント
- 監視（Monitoring）：システム状態、注文ログ、リスク指標をポーリングして永続化・アラート判定する
- ポートフォリオ構築：候補選定、重み付け、ポジションサイズ計算、セクター制限・レジーム乗数など
- 研究（Research）：ファクター計算、将来リターン、IC（Information Coefficient）など
- AI モジュール：ニュース記事のセンチメント評価（OpenAI）や市場レジーム判定
- ツール：ペーパートレード検証レポート等

設計方針の一例：
- DB（DuckDB/SQLite）やファイルベースのフラグを使った明示的な永続化・停止制御
- LLM 呼び出しはフェイルセーフにして、本番での致命的停止を避ける実装
- 各ユーティリティは OS 差分を吸収（例：プロセス優先度設定）

---

## 機能一覧

- 環境セットアップウィザード（.env の生成）: `kabusys.config_setup`
- 設定検証 CLI（環境変数・config/*.yaml のチェック）: `kabusys.validate_config`
- 監視ループ起動スクリプト: `kabusys.run_monitoring`
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用
- 実行エンジン起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録
- Monitoring 永続化層（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
- RiskMonitor: ドローダウン・ポジション上限監視と risk_logs 出力
- KillSwitch: `data/kill.flag` を書き込んで ExecutionEngine を停止させる仕組み
- AI:
  - ニュース NLP（OpenAI）で銘柄ごとにスコアを算出して ai_scores テーブルへ書き込み
  - レジーム判定（ETF + マクロニュース + LLM 合成）
- 研究用モジュール:
  - ファクター計算（momentum, volatility, value）
  - 将来リターン / IC / 統計サマリー
- ツール:
  - Paper Trading 検証レポート生成 (`kabusys.tools.paper_verification_report`)

---

## 前提条件（概略）

- Python 3.9+（ソースでの型注釈や pathlib 等を想定）
- 必要な外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml の検証を行う場合）
- OS に依存する操作（プロセス優先度設定等）について管理者権限が必要な場合あり

依存パッケージはプロジェクトに requirements.txt があればそちらを使ってください（本コードスニペットでは省略）。

例（仮）:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（プロジェクトの requirements.txt がある場合はそれを使用）。
   - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   ウィザードは .env（デフォルト：プロジェクトルート/.env）を作成します。
   必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   オプション:
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）
     - KABUSYS_ENV（development / paper_trading / live）

4. 設定検証
   - python -m kabusys.validate_config
   - 本番運用前に --strict オプションで警告を FAIL 扱いにできます:
     - python -m kabusys.validate_config --strict

5. データディレクトリの準備
   - デフォルト DB / フラグファイルはプロジェクトルートの `data/` 配下に置かれます。
   - logs ディレクトリも自動作成されます（`LOG_DIR` 環境変数で上書き可能）。

---

## 使い方（起動・停止・ツール）

基本的にパッケージモジュールとして直接起動します。

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  備考:
  - run_monitoring は常に Settings.sqlite_path を使用して monitoring DB を初期化します。
  - 停止させたい場合はプロジェクトルートの `data/stop_requested.flag` を作成すると監視ループが検知して終了します。

- 実行エンジンの起動
  - python -m kabusys.run_execution
  - Paper trading を使う例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト `data/paper_trading.db`）を使用します。

  停止:
  - `data/stop_requested.flag` を作成すると、エンジンは停止処理を実行します。
  - Kill Switch（監視側が条件を満たすと `data/kill.flag` を書き込む）により ExecutionEngine 停止シグナルを送る仕組みがあります。

- .env 作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を指定すると警告も失敗として exit(1)

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: `data/paper_trading.db`。`--db PATH` で指定可。

- AI 機能
  - ニューススコアリング / レジーム判定はそれぞれ `kabusys.ai.news_nlp.score_news` / `kabusys.ai.regime_detector.score_regime` を呼び出します（スクリプト化されている場合はモジュール経由で呼び出し）。
  - OpenAI API キーは `OPENAI_API_KEY` 環境変数または関数引数で渡します。

---

## 主な環境変数（抜粋）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DB / ファイル:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（実行エンジン PID 保存先, デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（Kill Switch フラグ, デフォルト: data/kill.flag）
- ログ:
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR（ログディレクトリ、デフォルト: logs/）
- 監視:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）
- AI:
  - OPENAI_API_KEY（OpenAI 呼び出しに必要）

---

## ファイル／ディレクトリ構成（簡易）

プロジェクトルート（src 配下のパッケージ）を要約します:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — Monitoring ポーリングループ起動
  - run_execution.py        — ExecutionEngine 起動
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI）
    - regime_detector.py    — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ & DB ラッパー
    - system_monitor.py
    - trade_monitor.py      — （注文監視）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      — （アラート処理）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                   — 実行時に利用する data ディレクトリ（DB/フラグ等）
  - logs/                   — ログ出力先（デフォルト）

（注）上記は主要ファイルの抜粋です。その他ユーティリティや追加モジュールがあります。

---

## ログ / 永続化

- ログ: デフォルト `logs/<app_name>.log`（日次ローテーション・30日保持）。`LOG_DIR` で変更可能。
- 監視ログ: SQLite（`SQLITE_PATH`）に system_status / trade_logs / positions / risk_logs / dashboard を保存。
- 分析データ: DuckDB（`DUCKDB_PATH`）を用いるモジュールあり（research, ai の一部など）。

---

## 運用上の注意

- 本番運用時は KABUSYS_ENV=live を意識して `.env` の値（特に API キー/通知設定）を確認してください。validate_config による「live ガード」チェックが有効です。
- kill.flag / stop_requested.flag / execution.pid の管理は運用ルールを明確にしてください。`KILL_FLAG_CLEAR_ON_START` を本番で 1 にするのは危険です。
- OpenAI 等外部 API 呼び出しはレートリミットや一時的障害を考慮したリトライ設計ですが、API キー管理・課金には注意してください。
- データのバックアップ（DuckDB/SQLite）・ログローテーション容量を監視してください。

---

## 開発／拡張のヒント

- research モジュールや portfolio モジュールは DuckDB 接続や純粋関数群で分離されており、テストが書きやすい設計です。
- AI モジュールは API 呼び出し部分が分離されており、テスト時に _call_openai_api をモックできます。
- 設定ロードはプロジェクトルート（.git / pyproject.toml を探索）を基準に行います。パッケージ配布後も CWD に依存しない設計です。

---

README はここまでです。必要に応じて以下を提供できます：
- 具体的な .env.example（テンプレート）
- requirements.txt（推奨パッケージの一覧）
- 起動 / デバッグ用の systemd / docker-compose 例

どれを追加しますか？
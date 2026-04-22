# KabuSys

日本株向けの自動売買 / 研究用ツール群（ライブラリ＋起動スクリプト群）。

このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量探索）、AI ベースのニュース NLP / レジーム判定、ペーパートレード検証ツールなどを含むモジュール群で構成されています。

---

## 主要な概要

- 設計方針
  - DB はローカルの DuckDB（分析用）と SQLite（監視／発注ログ）を使用。
  - 環境変数 / `.env` で設定を管理。`kabusys.config` が読み込み/検証を提供。
  - Paper trading（ペーパートレード）と Live（本番）を分離する設計。
  - ロギングは共通ユーティリティで設定（日次ローテーション + コンソール出力）。
  - AI（OpenAI）を使ったニュースセンチメント・レジーム判定機能あり（APIキー必須）。
  - フェイルセーフ：API失敗やデータ欠損時は安全側のフォールバックがある設計。

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine（注文実行エンジン）の起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、`data/paper_trading.db` に記録して本番 DB と分離
    - 停止フラグ（`data/stop_requested.flag`）検知で安全に停止
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）
    - 監視は環境に関わらず本番の sqlite_path を使用（設計上の注意）
- 設定管理
  - config_setup.py: 対話式ウィザードで `.env` を作成/更新
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
- 監視（monitoring）
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db（SQLite 永続化層）
  - KillSwitch が条件に応じて `data/kill.flag` を書き込み、ExecutionEngine を停止する
- 発注・実行（execution）
  - ブローカーファクトリ、注文管理、リスク管理、再整合（reconciler）等（詳細は execution パッケージ）
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数等（純粋関数群）
- 研究（research）
  - factor_research（Momentum / Value / Volatility 等）、feature_exploration（forward returns / IC / summary）
  - DuckDB を用いたオフライン計算（prices_daily / raw_financials 等）
- AI（ai）
  - news_nlp.score_news: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector.score_regime: ETF の MA200 乖離 + マクロニュースセンチメントから日次レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率、成功率、レイテンシ等）

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係をインストール
   - 依存パッケージの例（リポジトリの pyproject.toml / requirements.txt を参照してください）:
     - duckdb
     - psutil
     - openai
     - PyYAML (設定 YAML の検証時)
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートで `.env` を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは `.env` を手動作成（下にサンプルを示します）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは `data/`、`logs/` を使用します。自動で作成されることもありますが、権限やファイル配置を確認してください。

注意:
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI 機能を利用する場合:
  - 環境変数 OPENAI_API_KEY を設定する必要があります（または関数呼び出し時に明示的に渡す）

サンプル .env（参考）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 使い方（起動例・コマンド）

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - 動作モード: KABUSYS_ENV 環境変数に依存（development / paper_trading / live）
    - paper_trading: 発注は MockBroker に保存され `data/paper_trading.db` を使う
    - live: 実際のブローカーに発注（kabuステーション等）
  - エンジンは `data/stop_requested.flag` を検知すると安全に停止します。
  - 実行中は PID ファイル（デフォルト: data/execution.pid）が作成されます。

- Monitoring の起動（システム監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔の変更:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - 監視ループも `data/stop_requested.flag` を検知して終了します。
  - 監視は環境にかかわらず（KABUSYS_ENV に関わらず）本番の sqlite_path を使用します（設計上の注意）。

- .env の作成/更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 結果に応じてエラー/警告/情報が表示されます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（ニューススコアリング・レジーム判定）
  - Python API 経由で使用:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - OpenAI API キー（OPENAI_API_KEY）を設定しておくこと
  - 大量リクエスト時はレート制御・リトライロジックが含まれますが、API 使用料には注意してください。

停止・Kill Switch
- ExecutionEngine / Monitoring の停止
  - 監視・実行ループは `data/stop_requested.flag` の存在をポーリングして終了します。ファイルを作成すると安全に停止します。
  - KillSwitch（監視コンポーネント）は条件に応じて `data/kill.flag` を作成し、これを ExecutionEngine 側で検知して安全停止させます（`KILL_FLAG_CLEAR_ON_START` 設定に注意）。

ログ
- ログはデフォルトで `logs/` に日次ローテーションで保存されます（ファイル名: execution.log / monitoring.log 等）。コンソール出力は stdout に出力されます。

---

## 設定項目（主な環境変数）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）例: 60
  - PAPER_FILL_MODE: paper_trading 時の MockBroker の fill 動作（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（開発用。0 推奨）

詳細は `kabusys.config.Settings` を参照してください（型チェックやバリデーションあり）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py      — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py       — システム状態・データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - trade_monitor.py        — （トレード監視 — 詳細は該当ファイル）
    - monitoring_engine.py    — 各 Monitor を束ねてポーリング
    - kill_switch.py          — Kill Switch ロジック（flag ファイル書き込み）
    - alert_manager.py        — （アラート送信/管理）
  - execution/                — Execution 系の実装（BrokerFactory, Engine, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                     — （実行時に使用するローカルファイル: data/*.db, pid/flag 等）
  - utils/
    - logging_setup.py        — 共通ロギング設定
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - その他：`data/`, `logs/`（実行時生成）

（上記は主要モジュールの抜粋です。細かい実装は各モジュール内の docstring を参照してください。）

---

## 注意事項 / 運用上のポイント

- 監視コンポーネントは production の sqlite_path を使用する場面があります（run_monitoring は環境に関係なく本番 sqlite_path を使用する設計）。環境分離の取り扱いに注意してください。
- kill.flag / stop_requested.flag の管理には注意してください。特に本番では誤って kill.flag をクリアしないように設定（KILL_FLAG_CLEAR_ON_START は 0 推奨）。
- OpenAI 使用時は API コストに留意してください。また API エラー・レート制限に対してリトライロジックは組み込まれていますが、過度なリクエストは避けてください。
- ロギングディレクトリや DB ファイルのパーミッション、容量管理（DuckDB / SQLite / ログローテーション）に注意してください。
- CSV / YAML の設定ファイル生成・編集は `scripts/` や `config/`（存在する場合）を利用してください。validate_config は config/*.yaml の存在・パースも確認します（PyYAML が必要）。

---

## 開発・拡張のヒント

- DuckDB 接続を直接渡して関数単位でロジックをテストできます（research / ai モジュールはその設計）。
- 各モジュールはドキュメント文字列と型注釈を備えています。ユニットテストを追加してフェイルケース（API失敗/DB欠損）をカバーすると堅牢になります。
- ポートフォリオ・ポジション計算やリスク制御ロジックは純粋関数群として実装されており、モックデータで簡単に検証可能です。

---

必要であれば、README にさらに以下の内容を追記します：
- インストール用の pyproject.toml / requirements のサンプル
- よくあるトラブルシュート（DB が開けない、OpenAI キーが無い等）
- 各 CLI の詳細な引数説明（help は各スクリプトの argparse を参照）

要望があれば、追記・整備します。
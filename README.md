# KabuSys

日本株自動売買システムのコアライブラリ / 起動スクリプト群の README（日本語）。

このリポジトリはアルゴリズムトレーディングの主要コンポーネント（設定管理、監視、実行エンジン、ポートフォリオ構築、調査ツール、AI ベースのニュース解析など）を含みます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコア部分を構成する Python モジュール群です。主な目的は以下です。

- 戦略に基づく銘柄選定・配分・株数決定（Portfolio）
- ExecutionEngine を通した発注ロジック（実環境 / ペーパートレード対応）
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ）
- DuckDB / SQLite による分析・ログ永続化
- ニュースの NLP によるセンチメント評価（OpenAI 経由）
- 研究用途向けファクター計算・特徴量評価ツール
- 環境設定ウィザード・設定検証ツール・検証レポート生成ツール

設計方針として、実口座 API とは明確に分離され、ペーパートレード時は専用 DB に記録する等の安全ガードが組み込まれています。

---

## 主な機能一覧

- 設定管理
  - .env 自動/対話的読み書き（`kabusys.config_setup`）
  - 起動前の設定チェック（`kabusys.validate_config`）
- 実行エンジン
  - 本番 / ペーパートレード切替（`KABUSYS_ENV`）
  - 発注 / 注文管理 / リスク制御（ExecutionEngine 関連）
- 監視
  - システム稼働・データ鮮度・滞留注文・ドローダウン監視
  - Kill Switch（フラグファイルで強制停止）
  - 監視ループ起動スクリプト（`run_monitoring.py`）
- ポートフォリオ構築
  - 候補選定、等金額・スコア重み配分、リスク制御、サイズ計算
- 研究（Research）
  - Momentum / Volatility / Value 等ファクター計算
  - 将来リターン計算、IC（Information Coefficient）等
- AI（OpenAI）
  - ニュースを使った銘柄別センチメント評価（`ai.news_nlp.score_news`）
  - マクロセンチメント + ETF MA を用いた市場レジーム判定（`ai.regime_detector.score_regime`）
- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）
- ユーティリティ
  - 統一ログ設定（ローテーション付きファイル + stdout）
  - プロセス優先度 / CPU affinity 設定

---

## 動作要件（想定）

（リポジトリに requirements.txt がない場合は下記を想定してインストールしてください）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- （必要に応じて）その他のライブラリ

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実際のプロジェクトでは requirements.txt / poetry / pipfile を用意して管理してください。

---

## 主要な環境変数

必須（少なくとも設定が必要）:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う設定（デフォルトあり）:

- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- PAPER_FILL_MODE: paper_trading のモック約定挙動（instant|partial|never|reject）
- LOG_DIR: ログの出力ディレクトリ（デフォルト: logs/）

自動ロード:

- プロジェクトルート（.git または pyproject.toml を起点）にある `.env` / `.env.local` が自動ロードされます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。

---

## セットアップ手順

1. リポジトリをクローン

```bash
git clone <repo-url>
cd <repo-root>
```

2. 仮想環境を作成して依存をインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# その他、実行に必要なパッケージを追加
```

3. .env の作成（対話ウィザード推奨）

```bash
python -m kabusys.config_setup
```

ウィザードは `.env` を作成 / 更新します。必要な項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を入力してください。

4. 設定検証

```bash
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

5. データディレクトリやログディレクトリの確認

- デフォルト DB / ファイルパスは `data/` 配下、ログは `logs/` 配下に生成されます。適切な権限で作成されることを確認してください。

---

## 使い方

### 実行エンジン（ExecutionEngine）起動

- ペーパートレード: `KABUSYS_ENV=paper_trading` を設定すると MockBrokerClient が使われ、データは `data/paper_trading.db` に記録されます。
- 本番/通常: `KABUSYS_ENV=live` / `development` 等に応じて挙動が変わります。

起動:

```bash
python -m kabusys.run_execution
```

挙動:

- 起動時にプロセス優先度を「high」に設定しようとします（権限がない環境ではスキップされます）。
- 停止は `data/stop_requested.flag`（プロジェクトルート配下）を作成すると検知して終了します。
- PID は `data/execution.pid` に格納されます。

### 監視ループ起動

監視プロセスは System / Trade / Risk モニタを定期的に実行し、必要に応じて Kill Switch を発動します。

起動:

```bash
# デフォルトは 60 秒間隔
python -m kabusys.run_monitoring
# 環境変数でポーリング間隔を変更
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

挙動:

- 監視は常に（KABUSYS_ENV に関わらず）本番用の `sqlite_path` を使用して監視テーブルを初期化します。
- 停止は `data/stop_requested.flag` を検知してループ終了します。

### Kill Switch / 停止フラグ

- Kill Switch を発動すると `data/kill.flag` に理由が書き込まれます（ExecutionEngine はこれを検知して停止します）。
- 起動設定で `KILL_FLAG_CLEAR_ON_START=1` を設定するとエンジン起動時に `kill.flag` を自動でクリアします（本番では推奨されません）。

### 設定ウィザード / 検証

- .env 作成: `python -m kabusys.config_setup`
- 設定検証: `python -m kabusys.validate_config`

### Paper Trading 検証レポート

Paper Trading のログから検証レポートを生成します。

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示的に指定する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

レポートは稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL を判定します。

---

## 主要 API / ライブラリの使い方（簡易）

- ポートフォリオ関連（純粋関数、DB 参照なし）
  - select_candidates(buy_signals, max_positions)
  - calc_equal_weights(candidates)
  - calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)

- 研究（Research）
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons)
  - calc_ic(factor_records, forward_records, factor_col, return_col)

- AI
  - score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を集約し OpenAI に送信して ai_scores を更新します。
  - score_regime(conn, target_date, api_key=None)
    - ETF(1321) MA とマクロニュースの LLM センチメントを合成して market_regime を更新します。

- 監視 DB（MonitoringDB クラス）
  - init_monitoring_db(sqlite_conn) — テーブル作成 / マイグレーション
  - MonitoringDB(conn).log_system_status(...)
  - MonitoringDB(conn).log_trade_event(...)
  - MonitoringDB(conn).upsert_dashboard(...)

---

## よく使うファイル / フラグ類

- data/stop_requested.flag — run_monitoring / run_execution が監視する「停止要求」フラグ
- data/kill.flag — Kill Switch が書き込む ExecutionEngine 停止フラグ
- data/execution.pid — ExecutionEngine の PID ファイル（起動時に使用）
- logs/<app>.log — 日次ローテーションされるログファイル（デフォルト logs/）

---

## ディレクトリ構成

以下は主要なファイル・ディレクトリ（src/kabusys 配下）の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス、自動 .env 読込
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - research/
    - factor_research.py     — ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       (参照コード内に存在)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       (参照コード内に存在)
  - execution/
    - execution_engine.py    (参照コード内に存在)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はソース内の実装 / コメントから抽出した主要ファイル群です。実際のファイル全体はリポジトリを参照してください。）

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）のときは `LINE_CHANNEL_ACCESS_TOKEN` / `LINE_USER_ID` を設定しておくと監視アラートが届きます。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険です。Kill Switch を誤って自動クリアすると停止ガードが無効になります。
- OpenAI API を利用する機能は API キーとコストに注意してください（リクエストあたりのコスト、レート制限）。
- DuckDB / SQLite のパスはデフォルト `data/` 下になります。運用時には永続領域（ディスク）を確保してください。
- ログディレクトリ作成に失敗した場合、ファイルロギングはスキップされコンソールのみになります（ログ出力は utils.logging_setup が担います）。

---

## ライセンス / バージョン

パッケージバージョンは `kabusys.__version__ = "0.1.0"`。ライセンス情報が別途あればそちらを参照してください。

---

必要であれば、README に「起動例」「systemd / supervisord のユニット例」「詳細な環境変数一覧（説明付き）」などを追加できます。どの情報を優先して追加しますか？
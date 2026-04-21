# KabuSys

日本株向け自動売買システムのコアライブラリ。本リポジトリは発注（Execution）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）といった主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群です。主な設計方針は以下です。

- 発注ロジック（Execution）と監視（Monitoring）を明確に分離
- Paper Trading（ペーパートレード）と Live（本番）を環境変数で切替可能
- DuckDB を分析用 DB、SQLite を監視・履歴用 DB として利用
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / レジーム判定をサポート（オプション）
- ロギング・プロセス優先度設定・停止フラグ等の運用ユーティリティを提供

---

## 機能一覧

- Execution
  - ExecutionEngine による発注処理（paper_trading 環境時は MockBroker を使用）
  - OrderManager / OrderRepository / RiskManager / Reconciler 等の発注関連コンポーネント
  - Paper trading 用の専用 SQLite（デフォルト: `data/paper_trading.db`）で本番 DB と完全分離
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度の監視
  - TradeMonitor: 注文の滞留・約定異常などの検出（該当コードあり）
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch: しきい値超過時に `data/kill.flag` を作成して ExecutionEngine を停止する仕組み
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ
- ポートフォリオ構築（pure function）
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイジング、セクター制約、レジーム乗数など
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（オプション）
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースを組合せて市場レジームを判定
- ツール
  - .env 対話式ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report`
- ユーティリティ
  - ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - Monitoring 用 SQLite 初期化 / 永続化レイヤ（MonitoringDB）

---

## 必要条件（推奨）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証の拡張に必要、オプション）
- SQLite（標準ライブラリで利用可能）
- ネットワーク接続（本番で kabuステーション / OpenAI を使う場合）

インストール例（仮の requirements）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ 実際の運用では requirements.txt を用意して `pip install -r requirements.txt` を推奨します。

---

## セットアップ手順

1. リポジトリをクローンし、ワークディレクトリに移動
2. 仮想環境を作成して依存パッケージをインストール
3. .env ファイルを作成（対話ウィザード推奨）

対話式ウィザードで .env を作成:
```bash
python -m kabusys.config_setup
```

ウィザードで作成後、設定を検証:
```bash
python -m kabusys.validate_config
# 警告も許容せず厳密にチェックする場合:
python -m kabusys.validate_config --strict
```

.env の自動ロード:
- 起動時に .env と .env.local が自動的に読み込まれます（環境変数より後に読み込まれるため、OS 環境変数が優先されます）。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時）
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- LOG_LEVEL, LOG_DIR など

ログディレクトリのデフォルト: `logs/`。日次ローテートで最大 30 日保持。

---

## 使い方

基本的な起動スクリプト:

- ExecutionEngine の起動
  - 本番・ペーパー両方で動作。KABUSYS_ENV によって挙動が変わる（paper_trading は MockBroker）。
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - `data/stop_requested.flag` が存在する場合は起動せず終了する。
    - 実行中に `data/kill.flag` を書き込むことで ExecutionEngine を停止させることができます（KillSwitch 経由）。
    - 実行時に `data/execution.pid`（PID ファイル）を作成します。

- Monitoring の起動
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングするループを開始します。
  - 起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 環境変数でポーリング間隔を上書き可能:
    ```bash
    export MONITOR_POLL_INTERVAL=30  # 秒
    ```
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視情報を記録します（監視データは本番 DB を参照）。
  - 停止は `data/stop_requested.flag` を作成すると検出してループを終了します。

- .env 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB パスは `data/paper_trading.db`。`--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可。

- AI 機能
  - OpenAI キー（`OPENAI_API_KEY`）を設定しない場合、AI 機能はエラーになります。AI 関連は外部 API を使用するため使用時は API キーの管理を厳格に行ってください。
  - ニュース NLP（例）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 1), api_key="sk-...")
    ```

---

## 運用上の注意

- Kill Switch:
  - RiskMonitor 等が条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine を停止させる仕組みがあります。`KILL_FLAG_CLEAR_ON_START` は起動時に kill.flag を自動クリアする挙動を制御します（本番では `0` を推奨）。
- PID / Stop フラグ:
  - `data/execution.pid`, `data/stop_requested.flag` などのフラグファイルを利用してプロセスの起動・停止を管理します。
- ログ:
  - デフォルトでコンソール出力（stdout）と `logs/<app_name>.log` に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。
- データ鮮度:
  - SystemMonitor は DuckDB の価格データ鮮度をチェックします。古いデータ（閾値デフォルト 3 日）で警告を上げます。

---

## ディレクトリ構成

主要ファイル・ディレクトリの構成（src/kabusys 以下を抜粋）:

- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- config.py
  - 環境変数 / 設定管理（自動 .env ロード、Settings クラス）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI
- __init__.py
  - パッケージメタ情報（__version__ 等）

- ai/
  - news_nlp.py: ニュースセンチメントスコアリング
  - regime_detector.py: 市場レジーム判定
  - __init__.py

- monitoring/
  - monitoring_db.py: SQLite 監視 DB 初期化 + MonitoringDB クラス
  - system_monitor.py: システム / データ鮮度監視
  - trade_monitor.py: 注文監視（滞留・約定異常など）
  - risk_monitor.py: ドローダウン / ポジション制限監視
  - kill_switch.py: kill.flag 書き込みユーティリティ
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: 通知管理（LINE 等に通知する想定）
  - (その他モジュール)

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py など
  - Engine のコアロジック・ブローカー抽象化・リスク管理

- portfolio/
  - portfolio_builder.py: 候補選定・スコア並び替え
  - position_sizing.py: 株数算出・集約キャップ処理
  - risk_adjustment.py: セクター上限・レジーム乗数
  - __init__.py

- research/
  - factor_research.py: Momentum / Volatility / Value の計算
  - feature_exploration.py: 将来リターン / IC / 統計
  - __init__.py

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート
  - __init__.py

- utils/
  - logging_setup.py: 統一ロギング設定
  - process_priority.py: プロセス優先度・CPU affinity 設定
  - __init__.py

- data/
  - データファイルやフラグファイル（実行時に生成）
    - monitoring.db（デフォルト: data/monitoring.db）
    - kabusys.duckdb（デフォルト: data/kabusys.duckdb）
    - paper_trading.db（ペーパートレード用）
    - kill.flag / stop_requested.flag / execution.pid など

---

## 開発者向け補足

- 型ヒントや modern union 型（`|`）を使用しているため Python 3.10 以上を前提としています。
- DuckDB 接続は分析処理（research, ai）で多用されます。大規模データの読み書きには性能上の考慮が必要です。
- OpenAI API 呼び出し箇所はリトライ・バックオフ・レスポンス検証など頑健化されていますが、実運用では API 利用制限やコストに留意してください。
- テスト・CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って外部環境に依存しないようにできます。

---

必要であれば次の追補を作成します:
- example .env.example の完全テンプレート
- requirements.txt の推奨一覧
- 運用手順（デプロイ / systemd / cron / supervisor 用の unit ファイル例）
- よくあるトラブルシューティング集

どれを優先して追加しますか？
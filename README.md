# KabuSys

日本株自動売買システムのライブラリ／実行スクリプト群。  
ポートフォリオ構築、ファクター計算、ペーパートレード検証、監視（モニタリング）、および AI を使ったニュース／レジーム判定などの機能を備えています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 動作要件 / 依存パッケージ
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主なもの）
- 重要ファイル / パス・挙動の注意点
- ディレクトリ構成（概観）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究・監視を支援する Python モジュール群です。  
主な要素は次のとおりです。

- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リスク調整（セクターキャップ、レジーム乗数）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI 連携（ニュースのセンチメントスコアリング、マクロレジーム判定。OpenAI を使用）
- ペーパートレード検証ツール（集計・合否判定レポート）
- 実行エンジンと監視モジュール（ExecutionEngine / MonitoringEngine 相当の起動スクリプト）
- 監視ログの永続化（SQLite）と分析用 DuckDB

設計方針には「フェイルセーフ」「ルックアヘッドバイアス回避」「冪等性」を重視しています。

---

## 主な機能一覧

- portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（リスクベース／等配分／スコア加重）
  - apply_sector_cap, calc_regime_multiplier
- research:
  - calc_momentum, calc_volatility, calc_value（DuckDB ベースのファクター計算）
  - calc_forward_returns, calc_ic, factor_summary
- ai:
  - score_news（ニュースを OpenAI でスコアリングして ai_scores テーブルへ書込）
  - score_regime（ETF + マクロニュースを統合して市場レジーム判定）
- monitoring:
  - SystemMonitor, TradeMonitor, RiskMonitor（監視ロジック）
  - MonitoringDB（SQLite ベースの永続化レイヤ）
  - KillSwitch（リスクトリガで ExecutionEngine 停止）
  - monitoring_engine（ポーリング実行器）
- utils:
  - logging_setup（標準化されたロギング設定）
  - process_priority（プロセス優先度 / CPU affinity 設定）
- tools:
  - paper_verification_report（ペーパートレード検証レポート生成）

---

## 動作要件 / 依存パッケージ

推奨 Python バージョン: 3.10+ （Union 型表記 `X | Y` を使用）

主な依存パッケージ（必要に応じてインストールしてください）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config ファイル検証をしたい場合）

例:
```
pip install duckdb psutil openai PyYAML
```

（requirements.txt はプロジェクトに含まれていない想定のため、実行に必要なパッケージを上記のように個別に入れてください）

---

## セットアップ手順

1. リポジトリをクローン / コードを配置する
2. Python 環境を用意（venv など）
3. 必要パッケージをインストール（上記参照）
4. .env を作成（環境変数を設定）
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは `.env`（デフォルト: プロジェクトルート/.env）を生成・更新します。
5. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告を失敗として扱う場合:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリ準備（通常は自動作成されますが、必要に応じて手動で作成可能）:
   - デフォルト DB/ログ/フラグパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / kill flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（monitoring）:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 監視は常に「本番用 sqlite_path」を使用（KABUSYS_ENV に依らず）。
  - 停止: プロジェクトルート/data/stop_requested.flag が存在するとループを抜けます。

- 実行エンジン起動（ExecutionEngine）:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db）へ記録します（本番 DB と分離）。
  - 実行中にプロセスを停止したい場合は `data/stop_requested.flag` を作成します（起動時に flag が存在すると起動しません）。

- ペーパートレード検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定例
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 系（スクリプト呼び出し例、ライブラリ経由の呼び出しも可）
  - OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または引数）。
  - モジュール関数を直接呼ぶ例（アプリ内部で使用）:
    - `kabusys.ai.score_news(conn, target_date, api_key=...)`
    - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)`

---

## 環境変数（主なもの）

必須（起動前に .env で設定すること）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要オプション:
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログファイル保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI 利用時に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject, デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（デフォルト 0。本番では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH — ファイルパスを上書き可能

注意: `.env.example` を参考に `.env` を作成することを推奨します（プロジェクトに .env.example がある場合）。

---

## 重要ファイル / パス・挙動の注意点

- data/kill.flag
  - KillSwitch によって書き込まれるフラグファイル。存在すると ExecutionEngine に停止シグナルを送る仕組みです。
  - 本番で `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされます（危険な設定のため本番では 0 推奨）。

- data/stop_requested.flag
  - run_monitoring/run_execution の外部停止フラグ。ファイルが存在するとループを抜けます（起動時のチェックもあり）。
  - 管理者が停止を指示する際に使用します。

- data/execution.pid
  - 実行エンジンの PID 書き出し先（既定）。プロセス管理で利用。

- ログ
  - デフォルトで `logs/<app_name>.log` 日次ローテーション（30日保持）とコンソールへ出力します。
  - `kabusys.utils.logging_setup.setup_logging(app_name="...")` で一貫したロギングが行われます。

- DB の分離
  - `paper_trading` モードでは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番監視 DB と分離されます。
  - Monitoring の実行は常に `SQLITE_PATH`（本番 sqlite_path）を参照する設計の箇所があるため注意してください（run_monitoring は環境にかかわらず本番 sqlite を使用します）。

---

## トラブルシューティング / 運用メモ

- .env の自動読み込み
  - 起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動読み込みします。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視ポーリング値不正
  - `MONITOR_POLL_INTERVAL` が 0 や負の値の場合、デフォルトにフォールバックします（ログに警告）。
- OpenAI エラー処理
  - AI 呼び出しは 429 / タイムアウト / 5xx を指数バックオフでリトライします。失敗時は安全側で処理を続行する設計です（多くはスコアを 0 にフォールバック）。
- ログディレクトリ作成失敗
  - ログディレクトリの作成に失敗した場合はファイル出力を無効化してコンソール出力のみで継続します（起動ログに警告あり）。
- kill.flag の手動解除
  - ファイルを手動で削除:
    ```
    rm data/kill.flag
    ```
  - またはスクリプトから `KillSwitch(flag_path).clear()` を呼ぶことで削除できます。

---

## ディレクトリ構成（src/kabusys: 概観）

（主要なファイル・モジュールのみ抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / affinity 設定
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
    - news_nlp.py            — ニューススコア付与（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF MA）
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py (想定)
    - alert_manager.py (想定)
  - execution/
    - execution_engine.py (想定)
    - order_manager.py (想定)
    - order_repository.py (想定)
    - broker_factory.py (想定)
    - reconciler.py, risk_manager.py (想定)
  - data/ (実行時に生成される / デフォルト)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/
    - execution.log, monitoring.log, ...（日次ローテーション）

注: README に記載の一部モジュール（execution 側の詳細クラスや trade_monitor, alert_manager 等）はこのコードベースの別ファイル（あるいは将来追加のサブパッケージ）に依存します。実行時はこれらのコンポーネントが揃っていることを確認してください。

---

必要に応じて README を拡張して、セットアップ手順（venv 作成、systemd / Supervisor / Docker での常駐化、詳細な .env.example）や API キーの管理方法、CI でのテスト実行手順などを追加できます。追加したい内容があれば教えてください。
# KabuSys

日本株向け自動売買システムのコアライブラリ / 起動スクリプト群です。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築・リスク調整、研究用ファクター計算、ニュース NLU をつなぐコンポーネント群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します：

- ExecutionEngine：ブローカークライアントを使った発注実行（本番 / ペーパートレード対応）
- Monitoring：システム稼働 / データ鮮度 / 注文状態 / リスク監視と Kill Switch
- Portfolio：銘柄選定、重み算出、ポジションサイズ計算、セクター制約などの純粋関数群
- Research：DuckDB 上で動くファクター計算・特徴量探索ユーティリティ
- AI：ニュースのセンチメント評価（OpenAI を使用）とレジーム判定
- Tools：ペーパートレード検証レポート等のスクリプト
- ユーティリティ：ログ設定、プロセス優先度設定、設定読み書きウィザード等

設計方針の一例：
- DB（DuckDB / SQLite）や外部 API 呼び出しを明示的に分離
- 本番とペーパートレードは DB を分離（設定で切替）
- 自動停止（Kill Switch）はファイルフラグで実装（data/kill.flag）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine 起動スクリプト
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い paper_trading DB を使用
  - プロセス優先度設定、PID 管理、停止フラグ検査

- run_monitoring.py
  - SystemMonitor のポーリングループ起動
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番の sqlite_path を使用（監視ログ共通化）

- config_setup.py / validate_config.py
  - .env を対話式に作成 / 更新するウィザード
  - 起動前に必須環境変数や config/*.yaml を検証する CLI

- monitoring パッケージ
  - MonitoringDB（SQLite）永続化層
  - SystemMonitor / TradeMonitor / RiskMonitor 等の監視ロジック
  - KillSwitch（data/kill.flag により ExecutionEngine を停止）

- portfolio パッケージ
  - 銘柄選定、等配分／スコア加重、ポジションサイズ計算、セクター上限など

- research パッケージ
  - DuckDB を使ったファクター計算（Momentum / Value / Volatility）
  - 将来リターン計算、IC などの解析ユーティリティ

- ai パッケージ
  - news_nlp: OpenAI を用いたニュースセンチメントの集約・書込み
  - regime_detector: ma200 とマクロニュースを組み合わせた市場レジーム判定

- tools
  - paper_verification_report: ペーパートレード DB から合格/不合格判定付きレポート生成

- utils
  - logging_setup: stdout と日次ローテーションファイルの設定
  - process_priority: プラットフォームに依存しない優先度 / CPU affinity 設定

---

## セットアップ手順

1. Python 環境を準備（推奨: 仮想環境）
   - Python 3.9+ を想定（duckdb / openai 等の互換性に依存）

   例：
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要パッケージをインストール
   - 最小の例（実際の要件により調整してください）:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - testing / 開発で追加パッケージが必要な場合は適宜インストールしてください。

3. .env の作成
   - 対話ウィザードで .env を生成・更新できます：
   ```
   python -m kabusys.config_setup
   ```
   - 必須環境変数（実行前に必ず設定）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を環境変数に設定（または .env に追加）

4. 設定の検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   - 警告をエラー扱いにする場合:
   ```
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリ / ファイル権限確認
   - ログディレクトリ（デフォルト `logs/`）や DB 保存先（`data/`）の書き込み権限を確認してください。
   - ログディレクトリ作成に失敗した場合はコンソール出力のみで動作します。

---

## 使い方

- ExecutionEngine を起動（通常）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` を付与するとペーパートレードモードになります（専用の paper_trading DB を使用）。
  - 実行中に停止したい場合は `data/stop_requested.flag` を作成するとエンジンは検出して終了します（run_execution/run_monitoring ともに参照）。
  - Kill Switch（リスク検出 → 停止）用フラグは `Settings.kill_flag_path`（デフォルト: `data/kill.flag`）に書き込まれます。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには環境変数 `MONITOR_POLL_INTERVAL` を設定（秒、例: 30）。
  - Monitoring は監視ログ用 SQLite を使います（デフォルト: `data/monitoring.db`）。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定できます。

- ライブラリとしての利用（簡単な例）
  - ポートフォリオ候補選定:
    ```py
    from kabusys.portfolio import select_candidates, calc_equal_weights
    candidates = select_candidates(buy_signals, max_positions=10)
    weights = calc_equal_weights(candidates)
    ```
  - ファクター計算:
    ```py
    import duckdb
    from datetime import date
    from kabusys.research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    results = calc_momentum(conn, date(2026, 4, 10))
    ```
  - ニューススコア（AI）:
    ```py
    from kabusys.ai import score_news
    # duckdb_conn は DuckDBPyConnection
    written = score_news(duckdb_conn, target_date, api_key="sk-...")
    ```

- ログ設定
  - 全起動スクリプトは `kabusys.utils.logging_setup.setup_logging(app_name=...)` を呼び出します。
  - デフォルトログディレクトリ: `logs/`、ファイル名は `<app_name>.log`（日次ローテーション、30日保持）

---

## 重要な設定 / 環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境 / 動作切替
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）

- DB パス
  - DUCKDB_PATH（例: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、例: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、例: data/paper_trading.db）

- AI
  - OPENAI_API_KEY（news_nlp / regime_detector を使用する場合必須）

- Monitoring
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数; デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH（Settings で指定可）

---

## ディレクトリ構成（抜粋）

（リポジトリのルートに `src/kabusys` を想定）

- src/
  - kabusys/
    - __init__.py
    - run_execution.py
    - run_monitoring.py
    - config.py
    - config_setup.py
    - validate_config.py
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (参照)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (参照)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - execution/ (ExecutionEngine 関連: broker_factory, execution_engine, order_manager 等)
    - data/ (データ格納ディレクトリ: DB / フラグファイル等)

※ 上記は主要ファイルの抜粋です。実際のリポジトリには他に補助モジュールが含まれます。

---

## .env 例（最小）

以下は .env の一例（実運用では機密値を適切に管理してください）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

作成は `python -m kabusys.config_setup` を推奨します。

---

## トラブルシューティング / 注意点

- 環境変数未設定エラー:
  - `Settings` における必須キーが未設定だと起動時に例外が出ます。`validate_config` で事前チェックしてください。

- 権限関連:
  - ログディレクトリ（logs/）や data/ 下の DB/フラグファイルに書き込み権限が必要です。

- psutil の優先度設定:
  - set_process_priority は環境によって AccessDenied を起こす場合があります（権限不足）。その場合は警告が出てスキップされます。

- DuckDB / SQLite のバージョン互換:
  - 一部の実装は DuckDB の古いバージョンで executemany の空リストに弱い等の留意点があります（実装中に互換性配慮あり）。

- AI (OpenAI) 呼び出し:
  - API キーの管理、レート制限、エラーハンドリングを考慮してください。news_nlp と regime_detector はリトライ・フォールバックロジックを備えていますが、課金や呼び出し制限に注意してください。

---

## ライセンス / 貢献

本リポジトリのライセンスやコントリビューションの方針はリポジトリルートの LICENSE / CONTRIBUTING ファイルを参照してください。

---

必要なら、起動例の systemd ユニットや Docker 化手順、追加の開発者向けドキュメント（テスト、CI 設定、モックブローカーの詳細）を別途作成します。どの情報が必要か教えてください。
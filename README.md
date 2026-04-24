# KabuSys

日本株向け自動売買システムのコアライブラリ。ポートフォリオ構築、ポジションサイズ計算、発注エンジン、モニタリング、研究用ファクター計算、ニュース NLP / レジーム判定などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。設計方針として

- 明確な責務分離（Execution / Monitoring / Research / Portfolio / AI）
- 本番・ペーパートレードの分離（環境変数で切替）
- DuckDB / SQLite を用いたデータ永続化と分析
- LLM（OpenAI）を用いたニュースセンチメントやマクロ判定の統合
- フェイルセーフ（APIエラーや部分失敗に対する安全策）

を特徴とします。

---

## 主な機能一覧

- ExecutionEngine（発注実行）
  - ブローカークライアントの抽象化（本番/モック）
  - 注文管理、リスク管理、照合（Reconciler）
  - ExecutionSession のデーモン実行サポート（pid / stop フラグ）
- Monitoring
  - SystemMonitor：CPU/メモリ/Disk/プロセス稼働・データ鮮度監視
  - TradeMonitor：注文滞留や約定異常検出（ログ参照）
  - RiskMonitor：ドローダウン・ポジション上限監視、Kill Switch 連携
  - MonitoringEngine：これらをまとめてポーリング
- Portfolio（銘柄選定 / 重み付け / ポジション投入量計算）
  - select_candidates, calc_equal_weights, calc_score_weights
  - セクターキャップ適用、レジーム乗数、position sizing（lot単位丸め、aggregate cap）
- Research（ファクター計算 / 特徴量探索）
  - momentum / volatility / value のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント算出（ai_scores テーブルへ保存）
  - ETF（1321）MA200 乖離とマクロセンチメントの混合で市場レジーム推定
- ユーティリティ
  - .env 設定ウィザード（config_setup）
  - 設定検証ツール（validate_config）
  - Paper Trading 用検証レポート生成ツール（tools.paper_verification_report）
  - ロギングセットアップ、プロセス優先度設定など

---

## 前提条件 / 依存パッケージ

（実際の requirements ファイルは含まれていないため、代表的な依存を記載します）

- Python 3.9+
- duckdb
- openai
- psutil
- （任意）PyYAML（config/*.yaml のパース検証に使用）

インストール例（仮）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai psutil
# PyYAML が欲しい場合
pip install pyyaml
```

SQLite は標準ライブラリで利用します。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 仮想環境を作成・有効化し、必要なパッケージをインストール（上参照）。

3. 初回設定（.env の作成）
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成します（デフォルトはプロジェクトルートの .env）。

4. 設定検証
   - 自動検証スクリプトで必須環境変数や config/*.yaml の存在・整合性をチェックします:
     ```bash
     python -m kabusys.validate_config
     # 警告も失敗扱いにする場合
     python -m kabusys.validate_config --strict
     ```

5. データディレクトリの準備（必要なら）
   - デフォルト SQLite / DuckDB のパスは .env と同じく `data/` 下を想定しています。監視やログ出力のために `data/` と `logs/` ディレクトリを作成しておくと良いです。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます

- データベース / ファイル
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（Execution の pid ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（Kill Switch flag、デフォルト: data/kill.flag）

- ログ / 実行
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト: 60）

- OpenAI
  - OPENAI_API_KEY（AI 機能で必要）

- Paper トレード動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

（.env の雛形は config_setup により生成されます）

---

## 使い方（起動・コマンド例）

- 実行エンジン（ExecutionEngine）起動
  - 本番 / ペーパートレードの振る舞いは KABUSYS_ENV に依存します。
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - 起動時にプロセス優先度を "high" に設定します（設定に失敗しても継続）。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録します。
    - 起動前に `data/stop_requested.flag` が存在すると起動しません（停止フラグ）。

- 監視プロセス起動
  - システム・注文・リスクをポーリングで監視します。
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 環境変数でポーリング間隔を上書き可能:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は Settings の sqlite_path（デフォルト: data/monitoring.db）にログを記録します。
  - 監視プロセスもプロセス優先度を "high" に設定します。

- 設定ウィザード（.env の作成）
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
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## 停止 / Kill Switch の仕組み

- 実行エンジン停止:
  - モニタリング側の判定（RiskMonitor → KillSwitch）により `data/kill.flag` を書き込むことで ExecutionEngine に停止指示を出します。
  - ExecutionEngine は `data/stop_requested.flag`（run scripts 内で使う停止フラグ）や `data/kill.flag` の存在を監視して安全に停止します。
- フラグ操作:
  - `KillSwitch.clear()` により `data/kill.flag` を削除できます。`KILL_FLAG_CLEAR_ON_START` を `1` にすると起動時に自動クリアされますが、本番では `0` を推奨します。

---

## ログ設定

- 共通ロギングユーティリティ: `kabusys.utils.logging_setup.setup_logging`
  - コンソール出力（stdout）と日次でローテーションするファイル出力（logs/<app_name>.log）を設定します。
  - デフォルトで 30 日分を保持します。
  - LOG_DIR 環境変数でログ保存先を変更できます。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート: src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるセンチメント
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化（監視用テーブル）
    - system_monitor.py       — システムデータ・プロセス監視
    - trade_monitor.py        — 注文ログ監視（存在）
    - risk_monitor.py         — ドローダウン・ポジション制限監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各 Monitor を束ねる
    - alert_manager.py        — （存在を仮定するアラート管理）
  - execution/
    - execution_engine.py     — ExecutionEngine コア（存在）
    - broker_factory.py       — ブローカークライアント生成
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                      — デフォルトで利用される SQLite / DuckDB / flag ファイルはここに置く想定
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/monitoring_db.py — DB 初期化・永続化ロジック（テーブル定義）

> 注: 上記はリポジトリ内の主要モジュールを抜粋したものです。実際のファイル一覧はプロジェクト内を参照してください。

---

## 開発時の注意事項 / ヒント

- DuckDB は分析用途に使われ、research や AI モジュールは DuckDB 接続を受け取って SQL を実行します。大規模データを投げる際はメモリに注意してください。
- AI（OpenAI）を使う機能は API キーとネットワークを要します。API エラーやレート制限に対してリトライやフェイルセーフが実装されていますが、コスト管理に注意してください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を設定しておくとアラートが受け取れます。
- プロセス優先度や CPU affinity の設定は OS 権限に依存します。権限がない場合は警告が出てスキップされます。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（起動）
  ```bash
  python -m kabusys.run_execution
  ```

- 監視（起動）
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、この README をベースに「運用手順書（起動/停止/障害対応）」「デプロイ手順」「監視運用まとめ」「設定変数の詳細ドキュメント」を別途作成できます。どのドキュメントを優先しますか？
# KabuSys

日本株自動売買システム（軽量リファレンス実装）

このリポジトリは、売買ロジック・ポートフォリオ構築・監視・研究用ユーティリティ・AI 補助モジュールを含む小型の自動売買フレームワークです。実行スクリプトは ExecutionEngine（発注・約定連携）と Monitoring（システム・注文・リスク監視）を提供します。

---

## プロジェクト概要

- 株式自動売買のコア処理（発注エンジン）は `kabusys.execution`（エンジン／注文管理／ブローカー抽象）に実装されています（本リポジトリには一部のみ示されています）。
- モニタリング機能は `kabusys.monitoring` にまとまっており、システム稼働監視、注文ログ監視、リスク監視、Kill Switch（停止フラグ）などを提供します。
- ポートフォリオ構築は `kabusys.portfolio` に純粋関数として実装（候補選定、重み付け、ポジションサイズ計算、セクター制約など）。
- 研究・分析機能は `kabusys.research`（ファクター計算、特徴量探索）で提供され、DuckDB を使った価格データの処理を想定しています。
- AI モジュール（`kabusys.ai`）は OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントや市場レジーム判定を行います（API キーが必要）。
- 開発のための CLI ツール: `.env` 対話式ウィザード（`config_setup`）、設定検証（`validate_config`）、ペーパートレード検証レポート（`tools.paper_verification_report`）などを提供。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み／対話式作成（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
- 実行エンジン
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - Paper Trading と Live の分離（ペーパートレード用 DB）
  - Broker クライアントファクトリ（環境に応じて Mock を使用）
- 監視
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセスの存在確認
  - TradeMonitor: 注文の滞留チェックや約定異常検出（監視サブモジュール）
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: リスク条件で停止フラグ（`data/kill.flag`）を作成
  - MonitoringEngine: 上記モニタをまとめてポーリング
- ポートフォリオ構築
  - 候補選定（スコア順）/ 等金額・スコア加重配分
  - 単元株丸め、リスクベースの株数計算、aggregate cap スケーリング
  - セクター集中上限適用、レジーム乗数
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計要約
- AI（OpenAI）
  - ニュース記事のセンチメント集約と ai_scores への書き出し
  - 市場レジーム判定（MA200 + マクロニュースセンチメントの合成）
- ツール
  - Paper Trading 用検証レポート生成（成功率・稼働率・レイテンシ等）

---

## 必要な外部依存（主なもの）

（実行時に必要な主なパッケージ例。環境に合わせて適宜インストールしてください。）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（`validate_config` の YAML 検証に任意で使用）
※ sqlite3 は標準ライブラリに含まれます。

推奨インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. 初期設定 (.env) を作成
   - 対話式ウィザードを使う:
     ```
     PYTHONPATH=src python -m kabusys.config_setup
     ```
     （`PYTHONPATH=src` はリポジトリルートから実行する場合に必要です）

   - もしくは `.env` を手動作成。主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH, SQLITE_PATH (データベースファイルパス)
     - LOG_LEVEL
     - OPENAI_API_KEY （AI 機能を利用する場合）
     - PAPER_FILL_MODE (paper_trading 用: instant | partial | never | reject)

5. 設定検証
   ```
   PYTHONPATH=src python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告もエラーとして扱います。

6. データ・ログ用ディレクトリ作成（通常は自動作成されますが事前に作ることも可能）
   ```
   mkdir -p data logs
   ```

---

## 使い方（起動・操作）

※ モジュールはパッケージモードで実行することを想定しています。プロジェクトルートから `PYTHONPATH=src` を指定するか、インストールしてから `python -m` で実行してください。

- Monitoring を起動
  ```
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で変更:
    ```
    MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
    ```
  - 停止: `data/stop_requested.flag` を作成すると監視ループが終了します（同リポジトリ内スクリプトがチェックします）。

- ExecutionEngine を起動（発注エンジン）
  ```
  PYTHONPATH=src python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録されます。
  - 起動時、`data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中は同フラグの検出で停止処理を行います。

- 設定ウィザード
  ```
  PYTHONPATH=src python -m kabusys.config_setup
  ```

- 設定検証
  ```
  PYTHONPATH=src python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート（ローカル SQLite を使って集計）
  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルトの DB: `data/paper_trading.db`
  - 環境変数 `PAPER_TRADING_SQLITE_PATH` で DB を指定できます。

- AI 機能（例）
  - ニューススコアリング / レジーム判定は OpenAI API キーを必要とします。環境変数 `OPENAI_API_KEY` を設定してください。
  - 実際の呼び出しは `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime` を経由します（スクリプト化されている場合は対応の CLI を用意してください）。

- Kill Switch／停止フラグ
  - KillSwitch は `data/kill.flag` を書き込み、ExecutionEngine 停止のための外部シグナルとして機能します。`KILL_FLAG_CLEAR_ON_START` 環境変数（`0`/`1`）で起動時に自動クリアするか指定できます（本番では `0` 推奨）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（システム挙動を切替）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（`paper_trading` 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant, partial, never, reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## ディレクトリ構成（主要ファイル）

（ソースは `src/kabusys` 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（.env / 環境変数の解決、検証）
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py (ログの統一設定)
    - process_priority.py (プロセス優先度・CPU affinity 設定)
  - monitoring/
    - monitoring_db.py (SQLite の DB スキーマ & ラッパー)
    - monitoring_engine.py (複数モニタを束ねる)
    - system_monitor.py (CPU/メモリ/ディスク・データ鮮度監視)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (停止フラグ操作)
    - alert_manager.py (アラート送信管理) — ※参照あり（実装に依存）
    - trade_monitor.py (注文監視) — ※参照あり（実装に依存）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py など（発注ロジック）
  - portfolio/
    - portfolio_builder.py (候補選定・重み)
    - position_sizing.py (株数計算・cap)
    - risk_adjustment.py (セクター制約・レジーム乗数)
  - research/
    - factor_research.py (Momentum, Volatility, Value)
    - feature_exploration.py (forward return, IC, summary)
  - ai/
    - news_nlp.py (ニュースセンチメント -> ai_scores)
    - regime_detector.py (市場レジーム判定)
  - tools/
    - paper_verification_report.py (ペーパートレード検証用レポート)
  - data/ (実行時に生成される想定)
    - monitoring.db (SQLite, デフォルト)
    - paper_trading.db (ペーパートレード DB)
    - kill.flag / stop_requested.flag / execution.pid などのフラグ・PID ファイル
  - logs/ (ログ出力先、`logging_setup` が使用)

---

## 開発上の注意点 / 運用メモ

- 本実装は複数の DB（SQLite と DuckDB）を併用します。監視ログやトレードログは SQLite、時間系列分析やリサーチは DuckDB を想定しています。
- KABUSYS_ENV によって挙動が変わります。`paper_trading` では実口座に触れない設計になっています（MockBroker を使用し `data/paper_trading.db` に記録）。
- AI モジュールは外部 API（OpenAI）を呼び出します。API の失敗時はフォールバックや部分スキップして継続するよう設計されていますが、API キーおよび利用量に注意してください。
- ログはコンソール（stdout）と日次ローテーションされたファイルに出力されます（デフォルト `logs/<app_name>.log`、30日分保持）。
- kill.flag / stop_requested.flag / execution.pid といったファイルはプロセス間シグナリングに使われます。運用時は誤ってフラグを残さないよう注意してください（`KILL_FLAG_CLEAR_ON_START` は慎重に扱う）。

---

## よく使うコマンドまとめ

- .env ウィザード
  ```
  PYTHONPATH=src python -m kabusys.config_setup
  ```

- 設定検証
  ```
  PYTHONPATH=src python -m kabusys.validate_config
  ```

- 監視起動
  ```
  MONITOR_POLL_INTERVAL=60 PYTHONPATH=src python -m kabusys.run_monitoring
  ```

- 実行エンジン起動
  ```
  PYTHONPATH=src python -m kabusys.run_execution
  ```

- ペーパートレード検証レポート
  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベース（主に src/kabusys 配下）からの抜粋と注釈に基づき作成しています。実環境で稼働させる前に、必須環境変数の設定、DB パスの確認、`kabusys.validate_config` による検証を必ず行ってください。もし追加で README に含めたい起動オプションや運用手順があれば教えてください。
# KabuSys

日本株自動売買システムのサンプル実装。  
バックテスト／リサーチ、発注エンジン、監視・アラート、AI（ニュースセンチメント／レジーム判定）などの主要機能をモジュール化して実装しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されるシンプルな自動売買プラットフォームです。

- ExecutionEngine — 発注・注文管理・リスク管理を担う実行エンジン（実口座 / ペーパートレード切替）
- Monitoring — システム稼働状態、注文ログ、リスク指標を監視し Kill Switch を管理
- Portfolio モジュール — 候補選定・配分・ポジションサイズ計算、セクター制限・レジーム乗数
- Research モジュール — ファクター計算・将来リターン計算・IC 等の解析機能（DuckDB を利用）
- AI モジュール — ニュースの NLP（OpenAI）による銘柄スコアリング、マクロニュースと ma200 を使ったレジーム判定
- CLI ユーティリティ — .env の対話式作成（config_setup）、設定検証（validate_config）、ペーパートレード検証レポート生成

設計方針の一部:
- 環境依存設定は .env / 環境変数で管理
- ペーパートレードは本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用 DB として採用（prices_daily / raw_financials 等）
- 外部 API（OpenAI など）はキーをオプション・環境変数で指定

---

## 主な機能一覧

- Execution
  - ブローカークライアント抽象化（実口座 / Mock）
  - 注文管理・リスク管理（position limits, drawdown など）
  - 発注イベントのログ（trade_logs）
- Monitoring
  - CPU / メモリ / ディスク / プロセス稼働チェック
  - データ鮮度チェック（prices_daily）
  - リスク監視（ドローダウン・ポジション数上限）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - アラート送信インタフェース（LINE 等の通知設定あり）
- Portfolio
  - 候補選別、等分配 / スコア重み付け、リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数計算
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）等の解析ユーティリティ
- AI
  - ニュース記事を LLM（OpenAI）でセンチメント評価して ai_scores に書込
  - マクロニュース + ETF ma200 で日次レジーム判定と market_regime への書込
- ツール
  - ペーパートレード検証レポート生成（paper_verification_report）
  - 対話式 .env 作成（config_setup）
  - 起動前設定検証（validate_config）

---

## 必要条件 / 依存関係

主に以下のパッケージを使用しています（抜粋）:

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定ファイル検証を完全に行う場合に推奨）

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt に duckdb, psutil, openai, pyyaml などを記載しておいてください
```

（リポジトリに requirements.txt がない場合は上記パッケージを個別にインストールしてください）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 仮想環境を作成・有効化し、依存パッケージをインストール。

3. .env の作成（対話式ウィザード）:

```bash
python -m kabusys.config_setup
```

ウィザードは J-Quants トークンや kabu API パスワードなどの必須項目を対話的に促します。.env は絶対に Git にコミットしないでください。

4. 設定検証:

```bash
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

5. 必要なディレクトリを作成（通常は起動スクリプトが自動で作成しますが、手動で準備することも可能）:

- data/ （SQLite や PID / flag を置く）
- logs/ （ログファイル）

6. DuckDB / SQLite ファイル:
- デフォルトで DuckDB は data/kabusys.duckdb、監視用 SQLite は data/monitoring.db、ペーパートレード DB は data/paper_trading.db を使用します。必要に応じて .env で `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` を上書きしてください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API を利用する際に必要
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、ExecutionEngine は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）
- PAPER_FILL_MODE — paper_trading 時の約定モード（instant | partial | never | reject）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 kill.flag クリア（0 推奨）

監視ループのポーリング間隔:
- MONITOR_POLL_INTERVAL — 監視プロセスのポーリング間隔（秒、デフォルト 60）。不正値は無視してデフォルトにフォールバックします。

停止・Kill 操作:
- data/stop_requested.flag — run_monitoring.py / run_execution.py の停止フラグ（手動停止やデプロイ操作に利用）
- data/kill.flag — Kill Switch（監視が条件を満たした場合に書き込まれる）: ExecutionEngine はこのファイル存在を見て停止します

---

## 使い方（実行例）

- 監視プロセス起動（システム監視ループ）:

```bash
python -m kabusys.run_monitoring
# ポーリング間隔を環境変数で変更:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 実行エンジン起動（ExecutionEngine）:

```bash
python -m kabusys.run_execution
```

- ペーパートレード検証レポート生成:

```bash
# デフォルト DB (data/paper_trading.db) を使用
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# 別 DB を指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- .env 対話式作成 / 更新:

```bash
python -m kabusys.config_setup
```

- 設定検証:

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

停止手順（手動）:
- 監視・実行プロセスを止めるには `data/stop_requested.flag` を作成してください。スクリプトはこのフラグを検知して安全に終了します。
- Kill Switch による自動停止は `data/kill.flag` を書き込みます（監視プロセスが検出）。

ログ:
- ログは標準出力（コンソール）と日次ローテートされるファイル（デフォルト: logs/<app_name>.log）に出力されます。
- ログ出力設定は `kabusys.utils.logging_setup.setup_logging` で統一管理されます。

---

## 注意点 / 運用上のメモ

- Monitoring は KABUSYS_ENV に関わらず常に本番の sqlite_path（SQLITE_PATH）を使用して監視データを書き込みます。
- ExecutionEngine は `KABUSYS_ENV=paper_trading` の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全に分離します。
- OpenAI を使う機能（news_nlp, regime_detector）は API レート制限や一時エラーをリトライで扱いますが、API キー未設定時は呼び出し元でエラーとなります。運用時は API キーのセキュアな管理を行ってください。
- 本番（live）では `KILL_FLAG_CLEAR_ON_START` を 0 にすることを強く推奨します。1 にすると起動時に既存の kill.flag を自動で消去してしまい危険です。
- `.env` は絶対にリポジトリにコミットしないでください（秘密情報を含むため）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュールを抜粋した構成例:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (アラート送信の抽象化)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

- data/                         — 実行時に生成される DB / PID / flag 等
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/                         — ログ出力先（設定による）

（上記は実際のファイル群の抜粋です。詳細はソースツリーを参照してください）

---

## 参考コマンドまとめ

- 仮想環境・依存インストール

  ```
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml
  ```

- .env 作成

  ```
  python -m kabusys.config_setup
  ```

- 設定検証

  ```
  python -m kabusys.validate_config
  ```

- 監視起動

  ```
  python -m kabusys.run_monitoring
  ```

- 実行エンジン起動

  ```
  python -m kabusys.run_execution
  ```

- ペーパートレード検証レポート

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はここまでです。追加で「.env のサンプル」や「運用チェックリスト（デプロイ手順）」、あるいは特定モジュール（AI モジュールの詳細や DuckDB のスキーマ）についての詳細が必要であれば教えてください。
# KabuSys — 日本株自動売買システム

この README は、リポジトリ内のコードベースに基づく簡易ドキュメントです。起動スクリプト、監視、ポートフォリオ構築、リサーチ、AI ニューススコアリング等の主要コンポーネントを含む自動売買システムのローカル運用・開発を想定しています。

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数（主なもの）
- 使い方（起動・運用）
- ツール
- 停止・Kill Switch の説明
- ログ・DB の場所
- ディレクトリ構成（主要ファイル説明）
- 開発メモ / 注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコアライブラリ群です。  
主なコンポーネントは以下の通りです。

- ExecutionEngine（発注エンジン、ブローカ抽象化を介して実際の発注/ペーパートレードを実行）
- Monitoring（システム状態・発注状態・リスク監視）
- Portfolio construction（銘柄選定・重み付け・株数算出）
- Research（ファクター計算・特徴量探索）
- AI モジュール（ニュースの NLP によるセンチメントスコア、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード等）

設計方針として、実取引（live）とペーパートレード（paper_trading）を環境変数で明確に分離し、監視用 DB は環境に依らず一貫して本番の sqlite_path を使用するようになっています。

---

## 主な機能

- 環境設定ウィザード（config_setup）と事前検証 CLI（validate_config）
- ExecutionEngine：実発注 / モックブローカーでのペーパートレード対応
- Monitoring：CPU / メモリ / ディスク / プロセス稼働・データ鮮度監視
- Kill Switch：ドローダウンやポジション上限で自動停止フラグを発行
- Portfolio construction：候補選定、等金額／スコア重み、リスクベースのポジションサイズ算出
- Research：モメンタム・バリュー・ボラティリティ等のファクター計算、IC 計算
- AI：OpenAI を使ったニュースセンチメント（news_nlp）、市場レジーム判定（regime_detector）
- ツール：Paper Trading 検証レポート生成スクリプト

---

## 前提条件

- Python 3.9+（typing の構文等に対応）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証時に必要）
- ネットワーク接続（kabuステーション API / OpenAI を利用する場合）
- ローカルファイル書き込み権限（data/logs ディレクトリなど）

※ requirements.txt はこのリポジトリ内に明示されていない場合があります。プロジェクトで想定される依存パッケージを pip でインストールしてください。

例:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・アクティベート（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/Mac
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージのインストール（上記参照）
4. 環境変数設定（.env を作成）
   - 対話式ウィザードで .env を生成：
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成後は必ず設定検証を実行：
     ```bash
     python -m kabusys.validate_config
     ```
     `--strict` を付けると警告を FAIL 扱いにできます。

5. data / logs ディレクトリが自動で作成されますが、必要に応じて手動で作成してください。
   - デフォルトの DB/ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / Kill flag: data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 推奨 / 運用関連
  - KABUSYS_ENV — 実行環境: "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading 時は MockBrokerClient が使われ、データは data/paper_trading.db に記録され本番 DB と分離されます
  - OPENAI_API_KEY — OpenAI を利用する場合に必要
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - MONITOR_POLL_INTERVAL — 監視スクリプトのポーリング間隔（秒）※run_monitoring 用

- Kill Switch 関連
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" または "0"）

- Paper Trading 挙動
  - PAPER_FILL_MODE — MockBroker のフィルモード（instant, partial, never, reject）

詳しくは kabusys.config.Settings クラスのプロパティを参照してください。

---

## 使い方（起動・運用）

### 1) 設定検証（必ず行うことを推奨）
```bash
python -m kabusys.validate_config
# --strict を付けると警告でも exit(1)
python -m kabusys.validate_config --strict
```

### 2) ExecutionEngine（発注エンジン）起動
実稼働・ペーパートレードは KABUSYS_ENV によって切り替わります。

```bash
# デフォルトは .env の KABUSYS_ENV に従う
python -m kabusys.run_execution
```

挙動ポイント:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し data/paper_trading.db に記録される（本番 DB と分離）
- 起動時に data/stop_requested.flag が存在すると起動をスキップ
- 実行中は PID ファイル (data/execution.pid) を作成
- 停止は stop flag（stop_requested.flag）や kill.flag によって行われる

### 3) Monitoring（監視ループ）起動
監視は定期的に System / Trade / Risk チェックを実行し、必要に応じて kill.flag を書き込む等のアクションを行います。

```bash
# ポーリング間隔を環境変数で上書き可能（秒）
export MONITOR_POLL_INTERVAL=60
python -m kabusys.run_monitoring
```

特徴:
- MONITOR_POLL_INTERVAL（秒）でポーリング
- Monitoring は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録
- SystemMonitor はプロセス生存確認、データ鮮度確認、CPU/メモリ/ディスク使用率を記録
- KillSwitch（ドローダウン等の条件）で data/kill.flag を書き込むと ExecutionEngine に停止指示を与える

---

## ツール

- Paper Trading 検証レポート
  - 期間を指定して paper_trading DB から稼働率や約定率、レイテンシなどを集計してレポートを出力します。

  使用例:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db で DB を明示的に指定可能
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## 停止フラグ / Kill Switch

- data/stop_requested.flag — 実行プロセス（run_execution/run_monitoring）がループを終了するために参照する「運用停止フラグ」。外部でこのファイルを作成するとプロセスは安全に停止処理を開始します。
- data/kill.flag — Monitoring → KillSwitch が書き込むファイル。ExecutionEngine に緊急停止を指示する（ExecutionEngine は起動時やループでこのファイルの存在を確認する実装になっています）。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に既存の kill.flag を自動クリアします（本番では危険なのでデフォルトは 0 推奨）。

---

## ログ・DB の場所

- ログ: logs/<app_name>.log（app_name は "execution" / "monitoring" 等）
  - ログはコンソール（stdout）と日次ローテーションされたファイルへ出力されます（logs ディレクトリ）。
- DuckDB: data/kabusys.duckdb（分析用）
- SQLite (monitoring): data/monitoring.db
- SQLite (paper trading): data/paper_trading.db（paper_trading 環境で使用）

ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

---

## ディレクトリ構成（主要ファイル・概要）

- src/kabusys/
  - __init__.py — パッケージメタ情報（version）
  - config.py — 環境変数 / Settings 管理（.env 自動読み込み機能を含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFileHandler）
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文関連の監視。コードベースに詳細あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py —（アラート送信処理。LINE 等に通知する実装がある想定）
  - execution/ — ExecutionEngine、注文管理、ブローカーファクトリ等（発注ロジック）
  - portfolio/
    - portfolio_builder.py — 銘柄選定（スコア降順、等）
    - position_sizing.py — 株数算出・集約上限のスケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム/バリュー/ボラティリティ計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - data/ — (想定) データ/DB/フラグ/PID 等を格納するディレクトリ（data/monitoring.db 等）

---

## 開発メモ / 注意点

- Monitoring は監視 DB として Settings.sqlite_path を参照します。監視データは環境にかかわらず同じ sqlite_path を使用する設計になっています（運用上の扱いに注意）。
- run_execution は KABUSYS_ENV=paper_trading の場合に専用の paper_sqlite_path を使用して本番 DB と分離します。
- AI モジュール（news_nlp, regime_detector）は OpenAI API を利用します。API 呼び出しに対してはリトライ・バックオフやレスポンスバリデーションを組み込んであり、失敗時はフォールバック値（例: 0.0）で継続する実装になっています。
- Logging はアプリケーション起動直後に setup_logging を呼び出してから行うことが想定されています。ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみの出力にフォールバックします。
- process_priority.set_process_priority はプラットフォーム差異を吸収しますが、権限不足などで設定に失敗する可能性があるため警告ログを出して続行します。
- DB スキーマのマイグレーション（列追加等）は init_monitoring_db() 内に簡易処理があり、既存 DB にカラムがなければ追加する実装が含まれています。

---

この README はコードベースの一部に基づく要約です。詳細な挙動は各モジュール（特に execution、monitoring、ai、portfolio、research の各実装）を参照してください。README の追記・改善やセットアップ手順の自動化（requirements.txt / Dockerfile 等の追加）を行うことを推奨します。
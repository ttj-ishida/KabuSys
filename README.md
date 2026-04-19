# KabuSys

日本株向け自動売買・リサーチ基盤（軽量モジュール群）のリポジトリ。本 README はこのコードベースの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下のような責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行うランタイム（run_execution）
- 監視モジュール（Monitoring）: システム状態・注文状況・リスク監視・Kill Switch 制御（run_monitoring）
- ポートフォリオ構築ロジック: 候補選定、重み計算、ポジションサイズ算出、セクター制限など（portfolio）
- リサーチ / ファクター計算: DuckDB 上の株価データからファクターや将来リターン、IC 等を計算（research）
- AI 補助: ニュース NLP によるセンチメント集約、市場レジーム判定（ai）
- ユーティリティ: ログ設定、プロセス優先度設定、設定読み込み/ウィザード、設定検証など（utils, config*）
- 各種ツール: ペーパートレード検証レポート生成スクリプト等（tools）

設計のポイント:
- 設定は .env（もしくは環境変数）から読み込まれる。設定ウィザード（config_setup.py）と検証ツール（validate_config.py）を提供。
- Paper Trading（仮想発注）は本番 DB と分離（デフォルト：`data/paper_trading.db`）。
- ログは統一的にセットアップ（stdout + 日次ローテートファイル）。
- OpenAI を使う AI モジュールは API キーを環境変数 `OPENAI_API_KEY` で受け取る。

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution: ExecutionEngine を起動（Paper と Live を切り替え）
- 監視
  - run_monitoring: SystemMonitor をポーリングして system_status 等を記録
  - MonitoringEngine: system / trade / risk の各 Monitor を束ね、Kill Switch と Alert を管理
  - リスク監視（ドローダウン、ポジション上限）と kill.flag の自動生成
- 設定関連
  - config_setup: 対話式 .env 生成・更新ウィザード
  - validate_config: .env / config/*.yaml の事前チェック CLI
  - Settings クラス: 環境変数の取得・検証（型変換・デフォルト）
- ポートフォリオ構築（純関数）
  - 候補選定、等配分／スコア配分、リスクベースの株数計算、セクター制限、レジーム乗数
- リサーチ
  - momentum / volatility / value 等のファクター計算（DuckDB）
  - forward returns、IC（Spearman）、統計サマリ
- AI（OpenAI）
  - ニュース集合から銘柄ごとのセンチメントを算出して ai_scores に書き込み
  - マクロニュースと ETF MA 乖離を合成して日別の market_regime を判定
- ツール
  - paper_verification_report: ペーパートレードのパフォーマンス / 稼働率・レイテンシ等の検証レポートを生成

---

## 必要要件（概略）

最低限の Python ランタイムと外部パッケージが必要です。バージョンはプロジェクトポリシーに合わせてください。例:

- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config ファイル検証を行う場合、任意）

インストール例（最低限）:
```
pip install duckdb psutil openai
# 任意: pip install PyYAML
```

（プロジェクトに requirements.txt があればそれを使用してください）

---

## 環境変数（主要項目）

validate_config に記載されている主要な環境変数（必須 / 任意）:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — AI 機能利用時に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — PaperTrading の fill 動作（instant / partial / never / reject）

Kill Switch / 制御:
- KILL_FLAG_PATH — kill.flag の場所（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか (0/1)

注: `.env` の自動読込はデフォルトで有効。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai
   # 任意: pip install PyYAML
   ```
4. 環境変数を用意
   - 対話式ウィザードで .env を作る:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは `.env` を手動で作成（`config_setup` が推奨）。最低でも JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD を設定してください。
5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリの準備（必要に応じて）
   - デフォルトの DB/ログのパスは `data/` や `logs/` なので、権限等を確認してください。多くの処理は自動でディレクトリを作成します。

---

## 主要スクリプトの使い方

CLI は Python の -m 形式で実行できます。

- 実行エンジン（ExecutionEngine）起動
  ```
  python -m kabusys.run_execution
  ```
  補足:
  - KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録します。本番（live）では本番 SQLite を使用します。
  - プロセス優先度を high に設定してから起動します。
  - 起動時に `data/stop_requested.flag` が存在する場合は起動せず終了します。
  - 実行中は `data/execution.pid` に PID を書きます。停止は `data/stop_requested.flag` または `data/kill.flag` による信号で行えます。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  補足:
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書きできます（デフォルト 60 秒）。
  - 監視用 SQLite（monitoring）は環境にかかわらず `Settings.sqlite_path`（デフォルト: data/monitoring.db）を使います。
  - 停止は `data/stop_requested.flag` の作成で行います（スクリプトはその存在を検出して終了します）。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラム内 API）
  - ニューススコアリング:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーを `api_key` 引数または環境変数 `OPENAI_API_KEY` で指定
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらは DuckDB の接続オブジェクト（kabusys が期待するスキーマ）を受け取り、結果をテーブルに書き込みます。

---

## 監視 / Kill Switch の挙動（運用上のポイント）

- Kill Switch:
  - リスク監視（ドローダウンやポジション数）で閾値を超えると `data/kill.flag` を書き込み、ExecutionEngine に停止要求が送られます（Execution 起動中は kill.flag を検知すると停止処理を行います）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると Execution 起動時に kill.flag を自動でクリアしますが、本番では危険な設定なのでデフォルトは 0（クリアしない）推奨です。
- 停止フラグ:
  - `data/stop_requested.flag`: run_execution / run_monitoring に対して即時停止要求を行うためのフラグ（運用者が作成してプロセスを優雅に停止させるために使用）。
  - `data/execution.pid`: ExecutionEngine の PID を記録。

---

## ディレクトリ構成（概要）

以下は src/kabusys 配下の主要モジュールとファイルの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                      — Settings クラス、.env 読み込みロジック
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py          — プロセス優先度 / CPU affinity 設定
  - execution/                      — 実行エンジン関連（Engine, Broker, OrderManager, RiskManager 等）
    - (複数モジュール)
  - monitoring/
    - monitoring_db.py             — SQLite の永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/                          — （期待される）データディレクトリ（DB ファイルを置く）
  - tools/
    - paper_verification_report.py
    - __init__.py

詳しいソースは各ファイルの docstring / 関数コメントに設計意図や利用方法が書かれています。実装を読みながら運用方針を決めることを推奨します。

---

## 追加ノート / 運用上の注意

- Paper Trading と Live は DB を分離する設計です。誤って Live DB にペーパートレードを書き込まないよう `KABUSYS_ENV` を正しく設定してください。
- OpenAI を使うモジュールは API コストとレート制限に注意してください（リトライ・バッチ処理の実装あり）。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソール出力のみになります。
- `.env` は機密情報（API トークン等）を含むため Git にコミットしないでください（config_setup のヘッダでも注意喚起あり）。
- 本 README は概略です。詳細は各モジュールの docstring / 関数コメントを参照してください。

---

もし README に追加したい項目（セットアップスクリプトの例、Dockerfile、CI 指示、より詳細な運用手順など）があれば教えてください。必要に応じて追記します。
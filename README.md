# KabuSys — README

以下はこのリポジトリ（KabuSys）の簡易 README です。日本株向けの自動売買 / 研究補助用モジュール群を含み、実行エンジン、監視、ポートフォリオ構築、ファクター計算、AI を用いたニュース評価などの機能を備えています。

注意: 本 README はソースコードから読み取れる設計・設定情報をまとめたものです。実行前に必ず .env を作成し、設定検証を行ってください。

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコア部分を切り出した Python モジュール群です。主な目的は以下：

- 注文の実行（ExecutionEngine）
- システム稼働・注文状況・リスク監視（Monitoring）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- ファクター・リサーチ（DuckDB を使ったファクター計算、IC 計算等）
- ニュースの NLP によるセンチメントスコアリング（OpenAI）
- ペーパートレード用の検証レポート生成

設計上の特徴：
- 設定は .env（環境変数）で管理。`config_setup` ウィザードで対話的に作成可能
- `validate_config` で起動前の自動チェックが可能（YAML 設定ファイルの存在/パースは PyYAML が必要）
- 本番（live）／ペーパートレード（paper_trading）／開発（development）を切替可能
- DuckDB / SQLite をデータストアとして利用
- OpenAI を使った NLP 部分は外部 API キーで制御。失敗時はフェイルセーフ挙動あり

---

## 主な機能一覧

- run_execution: ExecutionEngine 起動スクリプト（本番 / ペーパーで DB 分離）
- run_monitoring: SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
- monitoring: system / trade / risk の各モニタ、Kill Switch、Alert 管理
- portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- research: ファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量解析（IC 等）
- ai:
  - news_nlp: ニュース記事を OpenAI へ送り銘柄ごとのセンチメントを計算・書き込み
  - regime_detector: マクロ + ETF MA を合成して市場レジーム判定
- tools:
  - paper_verification_report: ペーパートレードの検証レポート生成
- utils:
  - logging_setup: 統一的なログ設定（console + 日次ローテートログ）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- config_setup: .env を対話式で作成するウィザード
- validate_config: 起動前の環境チェック CLI

---

## 必須 / 主要な環境変数

必須（validate_config でもチェックされる）：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション:
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

その他、設定ウィザードで作成できるキーが .env に含まれます。

---

## セットアップ手順

推奨 Python バージョン: 3.10+

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール（最小／推奨）
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を有効にする場合: pip install pyyaml

   例（まとめて）:
   - pip install duckdb psutil openai pyyaml

   注: 本リポジトリに requirements.txt がない場合は上記を手動でインストールしてください。

3. .env の作成
   - 対話式で作る（推奨）:
     - python -m kabusys.config_setup
   - またはテンプレートをコピーして編集 (.env.example がある場合を想定)

4. 設定検証（本番前に必須）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ（logs, data など）の作成（自動作成されることも多いですが手動確認推奨）
   - mkdir -p data logs

---

## 使い方（起動コマンド例）

- ExecutionEngine（実行エンジン）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します。

- Monitoring（監視）起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード（.env の作成/更新）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコアリング / レジーム判定（プログラムから呼ぶ）
  - news_nlp.score_news(duckdb_conn, target_date, api_key=...)
  - regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

---

## 実行時の挙動・運用メモ

- ログ:
  - kabusys.utils.logging_setup.setup_logging を使いコンソール（stdout）とファイル（logs/<app>.log）へ出力。
  - ログローテーション: 日次、30世代保持。

- プロセス優先度:
  - run_execution / run_monitoring は起動時に set_process_priority("high") を呼びます（プラットフォーム依存で失敗時は警告で継続）。

- 停止フラグ:
  - run_monitoring はリポジトリルートの data/stop_requested.flag を監視してループを終了します。
  - run_execution は起動中に同フラグを検知すると engine.stop() を呼び停止します。
  - Kill Switch（kill.flag）は監視モジュールから ExecutionEngine 停止のために書き込まれます（Settings.kill_flag_path）。

- DB:
  - monitoring 用の SQLite（デフォルト: data/monitoring.db）
  - DuckDB（デフォルト: data/kabusys.duckdb）
  - paper_trading モードでは paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離

- フェイルセーフ:
  - AI 呼び出し（OpenAI）部分は 429 等の一時エラーに対して指数バックオフでリトライし、それでも失敗した場合にはスコアを取得できなかった項目をスキップする（システム全体が停止しない設計）。

---

## ディレクトリ構成（主要ファイルの説明）

※ この README は src/kabusys 以下のファイル構成に基づきます。

- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、Settings クラス（環境変数アクセス）
  - config_setup.py
    - .env の対話式ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite の永続化層（テーブル作成・読み書きラッパ）
    - system_monitor.py — システム状態 & データ鮮度チェック
    - trade_monitor.py — （注文ログ監視）※詳細実装ファイルあり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
    - alert_manager.py — 通知管理（LINE 等、別実装想定）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, etc.
    - broker_factory.py — 本番/Mock ブローカー切替
    - reconciler.py, risk_manager.py など
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マクロ + MA によるレジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
    - __init__.py

---

## 開発者向けメモ

- 型ヒントや modern な構文（| を用いた union 型）を利用しているため Python 3.10+ を推奨します。
- DuckDB へ接続する関数群は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。テスト時は in-memory DB を使うと便利です。
- validate_config は PyYAML がない場合、config/*.yaml の内容検証をスキップします（警告）。
- ローカル実行時に .env の自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- log ディレクトリ作成に失敗した場合はコンソール出力のみで継続します（エラーになりません）。

---

## よくある操作例

- .env を作って検証して実行（ペーパートレードで起動）:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視を起動（30秒間隔）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート（過去 10 日分）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要があれば README に追記します（例: 各設定項目の詳細説明、実行時のログ例、Docker / systemd の起動サンプルなど）。どの情報を追加したいか教えてください。
# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・リサーチ・モニタリングのためのライブラリと起動スクリプト群を含みます。各モジュールは実運用を念頭に設計されており、ローカル開発 / ペーパートレード / 本番 (live) を切り替えて使えます。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動例 / CLI）
- 環境変数一覧（主要）
- ディレクトリ構成（ファイル説明）

---

## プロジェクト概要

KabuSys は以下の目的で設計されたコンポーネント群を提供します。

- 戦略（ファクター算出、特徴量解析）用のリサーチモジュール（DuckDB を使用）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- ExecutionEngine（発注ロジック）およびペーパートレード用モックブローカー
- 監視（System / Trade / Risk）と Kill Switch による停止制御
- AI を使ったニュース NLP（OpenAI）によるセンチメント評価とレジーム判定
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、外部 API を呼ぶ部分（OpenAI, kabu API 等）は分離され、DB（DuckDB / SQLite）ベースでの再現性の高い計算を行います。

---

## 主な機能一覧

- config 管理（.env 自動読み込み, Settings クラス）
- 環境設定ウィザード（config_setup）
- 設定検証 CLI（validate_config）
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading DB に分離して記録
- 監視エンジン起動スクリプト（run_monitoring）
  - システム稼働・データ鮮度・トレード状況・リスク監視、Kill Switch 判定
- モニタリング DB 層（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard
- ポートフォリオ構築: 候補選定、等分・スコア加重、リスク調整（セクターキャップ）、ポジションサイズ計算
- リサーチ: ファクター計算（momentum / value / volatility）、将来リターン、IC 計算、統計サマリ
- AI モジュール: ニュースセンチメント（news_nlp）、市場レジーム判定（regime_detector）
- ツール: ペーパートレード結果検証レポート（paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.10+ 推奨
- DuckDB, SQLite はライブラリレベルで使用（duckdb Python package）
- OS により psutil が必要（プロセス優先度 / CPU affinity）

1. リポジトリをクローン／配置
   - プロジェクトルートには `pyproject.toml` または `.git` がある想定です。

2. 仮想環境を作成して依存をインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate
     pip install -U pip
     pip install duckdb psutil openai

   - 任意で PyYAML（config 検証で YAML の中身チェックをする場合）:
     pip install pyyaml

3. 環境変数設定（.env）
   - 初回はウィザードで作成すると簡単です:
     python -m kabusys.config_setup
   - もしくは手動で `.env` をプロジェクトルートに作成してください。
   - 重要な変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LOG_LEVEL, LOG_DIR など

4. 設定検証
   - python -m kabusys.validate_config
   - --strict フラグで警告も失敗扱いにできます。

5. データディレクトリ作成（必要なら）
   - 多くのデフォルトファイルは `data/` 配下に作成されます。起動時に自動作成されることもありますが、事前に作ると権限関連の問題を避けられます。
   - ログはデフォルト `logs/` に出力されます。

---

## 使い方

以下は主要スクリプトの実行例です。いずれもプロジェクトルートで実行してください。

1. 環境設定ウィザード（.env 生成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード:
     python -m kabusys.validate_config --strict

3. ExecutionEngine 起動（発注エンジン）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して `data/paper_trading.db` に記録（本番 DB と分離）
     - 起動時に `data/stop_requested.flag` が存在すると起動しません
     - 実行中は PID ファイル（デフォルト `data/execution.pid`）を扱います

4. Monitoring 起動（ポーリング監視）
   - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を変更:
     - MONITOR_POLL_INTERVAL=<秒>（デフォルト 60）
   - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使用します
   - 停止方法:
     - `data/stop_requested.flag` を作成すると監視ループは優雅に終了します
     - Kill Switch が評価されると `data/kill.flag` が書き込まれ、ExecutionEngine 側が検知して停止します

5. Paper Trading 検証レポート（ツール）
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

6. AI 機能（プログラムから呼び出す）
   - OpenAI API キーを設定（OPENAI_API_KEY）
   - ニュースセンチメント:
     - from datetime import date
       import duckdb
       conn = duckdb.connect("data/kabusys.duckdb")
       from kabusys.ai.news_nlp import score_news
       score_news(conn, date(2026,4,1), api_key=None)  # api_key None → 環境変数参照
   - レジーム判定:
       from kabusys.ai.regime_detector import score_regime
       score_regime(conn, date(2026,4,1))

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading 時）
- OPENAI_API_KEY — OpenAI を利用する場合に必須
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）

詳細は `src/kabusys/config.py` の Settings クラスにドキュメントがあります。

---

## ファイル / ディレクトリ構成（要約）

リポジトリの主要な構成:

- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込みロジック、Settings クラス（各種パス・閾値）
  - config_setup.py
    - `.env` を対話的に生成・更新するウィザード
  - validate_config.py
    - 起動前に環境変数や config/*.yaml を検証する CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — logging の初期化（stdout + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 層（スキーマ初期化・アクセス）
    - system_monitor.py — システム状態 & データ鮮度チェック
    - trade_monitor.py — （trade 監視ロジック）
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — kill.flag の管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py —（通知管理: LINE 等の実装想定）
  - execution/
    - execution_engine.py — 実際の発注 / セッション管理（EngineConfig）
    - broker_factory.py — ブローカークライアント生成（実ブローカー / Mock）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - data/
    - pipeline, stats 等（DuckDB を扱うユーティリティ）
  - research/
    - factor_research.py — momentum/volatility/value 等
    - feature_exploration.py — forward returns / IC / 統計
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・スケールダウンロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - ai/
    - news_nlp.py — OpenAI を用いたニュースセンチメント
    - regime_detector.py — MA200 + マクロセンチメント合成のレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

その他:
- data/ — デフォルト DB やフラグファイル（起動時に作成される）
  - stop_requested.flag — run_* スクリプトの外部停止フラグ
  - kill.flag — Kill Switch 発動フラグ（実行エンジン停止用）
  - execution.pid — 実行エンジンの PID ファイル
- logs/ — ログファイル出力先（デフォルト）

---

## 運用メモ / 注意事項

- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を `0` にすることを推奨します（誤って Kill Switch をクリアしないようにするため）。
- Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を参照します。ペーパートレード中でもモニタリングは本番用 DB を監視する点に注意してください。
- run_execution は起動時に `data/stop_requested.flag` の存在をチェックし、存在する場合は起動を中断します。停止はフラグファイルの作成で行います。
- OpenAI を利用する場合は必ず `OPENAI_API_KEY` を設定し、API のレート制限やコストに注意してください。AI モジュールはリトライやフォールバックの実装を含みますが、失敗時はフェイルセーフ的に影響を限定します。
- SQLite / DuckDB のファイルパスは環境変数で上書き可能です。運用時は適切なバックアップ・マウントポリシーを検討してください。

---

## サポート / 開発時のヒント

- ロギングは `kabusys.utils.logging_setup.setup_logging` を各起動スクリプトで呼び出します。ログ保存先・レベルは環境変数 `LOG_DIR` / `LOG_LEVEL` で調整できます。
- ユニットテストを書く際は Settings の自動 .env ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。
- DuckDB を使ったリサーチ関数は外部副作用を持たない純粋関数的実装を意図しています。ローカル解析や CI での高速検証に向きます。

---

この README はコードベースの概要ドキュメントです。各モジュールの詳細な仕様や API 利用法はソース内のドキュメンテーション文字列（docstring）を参照してください。追加の説明やテンプレート（例: config/*.yaml の生成スクリプト）についてはプロジェクトの scripts やドキュメントを参照してください。
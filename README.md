# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動／運用スクリプト群を収めたリポジトリの README です。  
本ドキュメントはコードベース（`src/kabusys`）の主要コンポーネント、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのフレームワークです。主な機能は以下の通りです。

- 戦略（ファクター計算、特徴量解析）とポートフォリオ構築ロジック（候補選定、重み付け、株数計算）を提供
- ExecutionEngine による発注管理（実売買とペーパートレードの分離）
- 監視（System / Trade / Risk）と Kill Switch（フラグファイルによる停止）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（ニュースセンチメント、レジーム判定）
- DuckDB / SQLite を用いたデータ保存・分析
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針として、データ処理ロジックは可能な限り副作用を持たない純粋関数で実装され、実売買周りは環境（`KABUSYS_ENV`）により本番とペーパートレードで分離されます。

---

## 主な機能一覧

- 環境設定管理
  - `.env` 自動読み込み（プロジェクトルートに `.env` / `.env.local` があれば読み込む）
  - 対話式ウィザードで `.env` を生成する `kabusys.config_setup`
  - 起動前に設定を検証する `kabusys.validate_config`

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 発注ログの整合性・滞留注文・約定異常チェック（trade_logs テーブル参照）
  - RiskMonitor: ドローダウンやポジション上限監視とアラート発行
  - MonitoringEngine: 上記モニタを束ねてポーリング
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine に停止シグナルを送る

- 実行（Execution）
  - ExecutionEngine: 発注フロー、OrderManager、RiskManager、Reconciler 等の起動
  - BrokerClientFactory により本番 / ペーパートレードクライアントを切替
  - ペーパートレードでは専用 DB（`data/paper_trading.db` がデフォルト）に記録

- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算、セクター制約、レジームに応じた乗数、株数計算（単元丸め・集約キャップ等）

- リサーチ（DuckDB を使ったファクター計算・解析）
  - momentum / volatility / value などのファクター計算
  - 将来リターン計算、IC（情報係数）計算、統計サマリ

- AI（OpenAI を利用）
  - ニュースを LLM でセンチメント化して `ai_scores` テーブルに保存（`kabusys.ai.news_nlp`）
  - マクロニュース + ETF MA を使った市場レジーム判定（`kabusys.ai.regime_detector`）
  - API 呼び出しは安全なリトライとバリデーションを行う

- 運用ツール
  - `kabusys.tools.paper_verification_report`: ペーパートレード DB（SQLite）から検証レポート生成

---

## 依存関係（主な Python パッケージ）

- Python 3.8+
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（設定ファイル YAML の、任意の構文チェック用）
- （標準ライブラリ以外は requirements.txt または pyproject.toml にまとめてください）

※ PyYAML が無い場合、`validate_config` の YAML 検証はスキップされます。  
※ OpenAI を使う機能（news_nlp, regime_detector）は `OPENAI_API_KEY` が必要です。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（例）:
   - pip install -r requirements.txt
   - または pip install duckdb psutil openai pyyaml

3. 環境変数の初期設定（`.env`）を作成します（推奨: 対話式ウィザードを使用）
   - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - 必須変数（例）: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`

4. データディレクトリ / ログディレクトリの作成（通常は自動作成されますが手動でも可）
   - data/（例: monitoring.db, paper_trading.db, kill.flag 等）
   - logs/

5. （任意）OpenAI 機能を使う場合は `OPENAI_API_KEY` を .env に設定

---

## 主要な環境変数

（重要なもののみ抜粋）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用関連
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- LOG_DIR — ログ保存先（デフォルト: logs/）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

Monitoring / Execution
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PID_FILE_PATH / KILL_FLAG_PATH — pid / kill flag のパス（デフォルト: data/execution.pid, data/kill.flag）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant / partial / never / reject）

OpenAI
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 用）

---

## 使い方（起動 & CLI）

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります:
    - python -m kabusys.validate_config --strict

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明:
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
    - 監視は常に `settings.sqlite_path`（デフォルト `data/monitoring.db`）を使用します（環境に依存せず本番 DB を参照）。
    - 停止フラグ: `data/stop_requested.flag` が存在するとループを終了します。

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 説明:
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使用され、ペーパートレード用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録され、本番 DB と完全分離されます。
    - 起動時に `data/stop_requested.flag` が存在する場合は起動をスキップします。
    - 実行中に `data/stop_requested.flag` を作成するとエンジン停止をリクエストします。
    - Execution は起動時に優先度を "high" に設定し、PID ファイル（デフォルト `data/execution.pid`）を書きます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD
    - --db PATH : SQLite ファイル（環境変数 `PAPER_TRADING_SQLITE_PATH` より優先）

- AI モジュールの呼び出し（コードから）
  - ニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # returns number of written codes
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

  ※ これらは CLI を提供していません。Python から関数を呼び出して利用してください（`OPENAI_API_KEY` が必要）。

---

## 停止・Kill Switch の仕組み

- Kill Switch は `kabusys.monitoring.kill_switch` に実装されています。条件を満たすと `data/kill.flag` を書き込みます。
- ExecutionEngine は起動時に `kill.flag` の有無を確認し、存在する場合は起動をしないか停止します（設定に応じて）。
- 強制停止やメンテナンス用に `data/stop_requested.flag` を用いる起動スクリプト（run_monitoring / run_execution）もあります。これらはプロセスを優雅に停止するためのフラグです。

---

## ログ

- ログは標準出力（stdout）と日次ローテーションされるファイルハンドラへ出力されます。
- デフォルトログディレクトリ: `logs/`。環境変数 `LOG_DIR` で変更可能。
- ログレベルは `LOG_LEVEL`（または setup_logging の引数）で制御します（デフォルト `INFO`）。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内で重要なファイル・ディレクトリのみ抜粋しています（`src/kabusys` を想定）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — 対話式 .env 生成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングプロセス起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で ai_scores を更新
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロ NLP）

  - monitoring/
    - monitoring_db.py       — SQLite のスキーマ + DB アクセスラッパ
    - system_monitor.py      — システム / データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（file omitted in listing but exists in package）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - alert_manager.py       — （アラート送信のラッパ／インタフェース）

  - execution/
    - execution_engine.py    — ExecutionEngine（発注ループ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 株数（ロット）計算 / 投下資金スケーリング
    - risk_adjustment.py     — セクターキャップ / レジーム乗数

  - research/
    - factor_research.py     — モメンタム / ボラ / バリュー等のファクター計算
    - feature_exploration.py — IC / 将来リターン / 統計サマリ

  - data/                    — 実行時に生成されるデータファイル（DB / flags / pid 等）
  - logs/                    — デフォルトのログ出力先

---

## よくある運用ポイント・注意点

- .env は絶対にリポジトリにコミットしないでください（秘密情報を含む）。
- `KABUSYS_ENV=paper_trading` のときは発注は仮想で行われ、`PAPER_TRADING_SQLITE_PATH` に記録されます。本番 DB とは完全に分離されます。
- `MONITOR_POLL_INTERVAL` は監視ループの sleep 秒数です。0 や負の値を設定すると無視されデフォルトに戻ります。
- OpenAI 関連は API コストとリトライ挙動に注意してください。API の失敗時はフェイルセーフとしてスコア 0 やスキップで継続する設計です（例外をそのまま上げない箇所が多い）。
- DuckDB / SQLite のパスは Settings で変更可能。運用環境では書き込み権限（ディレクトリの作成含む）を確認してください。
- `KILL_FLAG_CLEAR_ON_START=1` を本番で使うと危険です（kill.flag が自動で消去され、思わぬ発注継続が発生する可能性があります）。本番は 0 推奨。

---

## トラブルシューティング

- validate_config がエラーを出す場合は missing env を確認:
  - echo $JQUANTS_REFRESH_TOKEN
  - echo $KABU_API_PASSWORD
- ログに警告が出る場合は `LOG_LEVEL=DEBUG` で詳細ログを出してください。
- OpenAI 呼び出しでレート制限が出る場合は API キーと使用頻度を確認。コード側では指数バックオフを実装しています。

---

この README はコードベースから抽出された情報に基づいています。実際の運用では `config/*.yaml`（存在する場合）や `pyproject.toml` / requirements に記載された依存関係も合わせて確認してください。必要であれば README に追記しますので、項目の追加・修正を指示してください。
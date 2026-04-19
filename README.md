# KabuSys

日本株向け自動売買システムのコードベース README です。  
本ドキュメントはプロジェクトの概要、主な機能、セットアップ手順、利用方法、ディレクトリ構成を日本語でまとめています。

※ このリポジトリはパッケージとして `kabusys` を提供します。実行スクリプトはモジュールとして起動することを想定しています（例: `python -m kabusys.run_monitoring`）。

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究パイプライン／監視を行うためのモジュール群です。  
主な目的は以下：

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- 注文管理・Execution Engine（本番 / ペーパートレードの分離）
- システム監視・リスク監視・Kill Switch（停止信号）
- ニュース NLP / レジーム判定（OpenAI 等を利用）
- ペーパートレード検証レポート生成ツール

設計方針として、ルックアヘッドバイアスを避ける、フェイルセーフ（API失敗時は安全側で継続）などが盛り込まれています。

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（必要に応じて無効化可能）
  - 対話式ウィザードで `.env` を作成・更新する CLI（config_setup）
  - 設定検証 CLI（validate_config）

- 実行系
  - ExecutionEngine 起動スクリプト（run_execution）
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い DB を分離（paper_trading DB）
    - PID ファイル、停止フラグ / stop flag に対応

- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 単体起動スクリプト（run_monitoring）
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60秒）
    - 監視結果は SQLite（`data/monitoring.db` 既定）へ永続化

- ポートフォリオ構築（純粋関数）
  - 候補選定、等金額・スコア加重配分、ポジションサイズ決定（単元株丸め等）
  - セクター制限・レジーム乗数調整

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）等の統計処理（外部ライブラリ非依存）

- AI（OpenAI）連携
  - ニュース記事を LLM でスコアリング（news_nlp）
  - マクロニュース + MA200 を使ったレジーム判定（regime_detector）
  - OpenAI API のキーが必要（環境変数 `OPENAI_API_KEY`）

- ツール
  - ペーパートレーディング結果を集計・判定するレポート生成ツール（tools/paper_verification_report）

---

## 前提／推奨環境

- Python 3.10 以上（型注釈・モダン構文を使用）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定検証で YAML 内容を検査する場合）
- ログは既定で `logs/` ディレクトリへ日次ローテートで出力されます

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は duckdb, psutil, openai 等を個別にインストール）

4. 環境変数の初期化（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - `.env` を対話的に作成します。作成後は `python -m kabusys.validate_config` で検証してください。

5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OpenAI を使う場合: OPENAI_API_KEY
   - その他（任意）: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等

6. データディレクトリ作成（自動で作られる場合が多いですが事前作成しておくと安全）
   - mkdir -p data logs

---

## 使い方（主要コマンド）

- 設定ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup
  - オプション: --env-file を指定して別パスに保存可能

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると warning も失敗扱いで exit(1)

- 監視ループ起動（SystemMonitor 単体）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き（デフォルト 60）
    - 例: export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
  - 停止: Ctrl+C またはプロジェクトルートの data/stop_requested.flag を作成するとループが終了します

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading 用 DB に書き込みます
    - 例: export KABUSYS_ENV=paper_trading
  - 停止: data/stop_requested.flag を作成するか、ExecutionEngine の PID ファイル (data/execution.pid) を確認してプロセスを停止

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - モジュール関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時のフィルモード: instant/partial/never/reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 Kill Flag クリア（危険な設定）

.env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ファイル／ディレクトリ構成（主要ファイル）

以下はパッケージルート `src/kabusys` の主要モジュール一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理（.env 読み込み・Settings クラス）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py          — レジーム判定（MA + マクロ NLP）

  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py            — システム・データ鮮度監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - trade_monitor.py             — 注文滞留 / 約定異常検出（存在）
    - kill_switch.py               — data/kill.flag 書き込みロジック
    - monitoring_engine.py         — 各 monitor を束ねるエンジン
    - alert_manager.py             — 通知（LINE など）管理（存在）

  - execution/
    - execution_engine.py          — ExecutionEngine（起動・セッション管理）
    - broker_factory.py            — ブローカークライアント生成（Mock / 実環境）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定・資金配分ロジック
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py          — ファクター計算（momentum/value/volatility）
    - feature_exploration.py      — 将来リターン / IC / 統計サマリー
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート（コマンドライン実行可）

  - utils/
    - logging_setup.py            — ログ設定ユーティリティ（コンソール + 日次ローテーション）
    - process_priority.py         — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

- data/                             — データファイル（logs, sqlite, duckdb など）（実行時に生成）
  - stop_requested.flag             — 起動スクリプトが監視する停止フラグ
  - kill.flag                       — Kill Switch により書き込まれる停止フラグ
  - execution.pid                    — ExecutionEngine PID 管理など

- logs/                             — ログファイル（logs/<app_name>.log）

---

## 運用上の注意／ベストプラクティス

- 本番（KABUSYS_ENV=live）では kill flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は推奨されません。
- `.env` は機密情報を含むため、絶対にリポジトリにコミットしないでください。
- OpenAI など外部APIを使用する機能は API失敗時にフォールバックを行う設計ですが、APIキーは安全に管理してください。
- run_execution はペーパートレードと本番 DB を分離します。紙上での試験は KABUSYS_ENV=paper_trading を使用してください。
- 監視ループや実行エンジンは data/stop_requested.flag の存在を監視します。運用時は外部からこのフラグを操作して安全に停止できます。

---

## よく使うコマンドまとめ（例）

- .env の作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動（デフォルト 60s）:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- 実行エンジン起動:
  - python -m kabusys.run_execution

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースから抽出した主要情報をまとめたものです。実運用に際しては config/*.yaml（もし存在すれば）や各モジュールのドキュメント、及び .env.example を参照のうえ、慎重に設定を確認してください。質問や追記が必要であれば教えてください。
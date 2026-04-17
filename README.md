# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行コンポーネント群）

このリポジトリは、発注エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・調査（Research）・AI を使ったニュース判定など、自動売買に必要な基盤機能をモジュール化したものです。実運用（live）とペーパートレード（paper_trading）を分離して扱える設計になっています。

---

## プロジェクト概要

- 発注ロジック（ExecutionEngine）を中心に、リスク管理、注文管理、約定ログ保存などを行う。
- 監視サブシステムがシステム状態・注文滞留・リスク指標を定期的にチェックし、必要に応じて Kill Switch を発動して ExecutionEngine に停止通知を送る。
- DuckDB を分析用に、SQLite を監視・発注ログ用に利用（デフォルトファイルは `data/kabusys.duckdb`, `data/monitoring.db`）。
- Paper trading モードでは MockBroker を使い、本番 DB とは分離して `data/paper_trading.db` を利用。
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント評価・市場レジーム判定機能を提供（API キー必須）。
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）、リスク調整の純粋関数群を提供（DB に依存しない設計）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（本番 / ペーパー切替）
  - OrderManager / OrderRepository / Reconciler / RiskManager
  - PID 管理、停止フラグ対応（`data/stop_requested.flag`, `data/execution.pid`）

- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク / データ鮮度 / プロセス生存）
  - TradeMonitor（滞留注文、約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件を満たした場合に `data/kill.flag` を書き込み、Execution を停止）
  - MonitoringEngine（複数モニタを束ねるポーリングループ）

- AI
  - news_nlp: ニュース記事を LLM でセンチメント評価し `ai_scores` テーブルへ書込み
  - regime_detector: マクロニュース + ETF MA 乖離から市場レジーム判定

- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）評価
  - 候補選定、等金額/スコア加重、ポジション数算出、セクター制約・レジーム乗数

- Tools
  - ペーパートレード検証レポート生成スクリプト（期間指定可）
  - .env 対話式ウィザード、設定検証 CLI

---

## セットアップ手順（概略）

1. 必要環境
   - Python 3.10 以上（typing の | アノテーション等を使用）
   - 推奨: 仮想環境（venv / pyenv / conda 等）

2. 依存パッケージ（代表例）
   - duckdb
   - psutil
   - openai
   - PyYAML（設定ファイル検証に任意で必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

3. プロジェクトルートに移動して .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは `.env` を手動で作成（下記の必須・主要環境変数参照）

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は `--strict` オプションを付与

5. データディレクトリの準備
   - デフォルトは `data/` に DB ファイルやフラグファイルを置きます。必要に応じて権限/パスを確認してください。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading の場合は MockBroker を使用し DB は `PAPER_TRADING_SQLITE_PATH` を使う
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動: "instant" | "partial" | "never" | "reject"（デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"0"/"1"。本番は 0 推奨）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒。run_monitoring で使用。デフォルト 60）

※ .env には機密情報を含むため絶対に Git にコミットしないでください。

---

## 使い方（実行例）

- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 起動時、プロセス優先度を "high" に設定し、PID を `data/execution.pid`（デフォルト）に書きます。
  - 停止: `data/stop_requested.flag` を作成すると起動スレッドが検知して停止します。
  - Kill Switch（監視側が発動）により `data/kill.flag` が作成されると ExecutionEngine は停止します。

- 監視ループ起動
  - MONITOR_POLL_INTERVAL を設定してポーリング間隔を変更可（秒）。
  - python -m kabusys.run_monitoring
  - 監視は常に本番の sqlite_path を使用（環境にかかわらず監視 DB は共通の監視用 DB を参照/更新します）。

- ペーパートレード検証レポート（例）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラム的に）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用
  - OpenAI API キーが必要。内部でリトライやバリデーション処理を行います。

---

## 停止・フラグの取り扱い

- 実行系停止
  - run_execution/run_monitoring は `data/stop_requested.flag` の存在を監視して自己シャットダウンします（手動停止の手段）。
  - KillSwitch は `KILL_FLAG_PATH`（デフォルト `data/kill.flag`）に理由を書き込み、ExecutionEngine を停止させます。

- PID / フラグの初期化
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると Execution 起動時に kill.flag を自動で削除します（本番では推奨されません）。

---

## テスト・デバッグのヒント

- 設定検証（validate_config）で不足や警告が出るので起動前に必ず実行してください。
- Paper trading では MockBroker を使い、本番 DB と分離されます。実動作をテストしたい場合は KABUSYS_ENV=paper_trading に設定。
- OpenAI API 呼び出し部は外部依存が強いため unittest.mock で _call_openai_api をモックすると単体テストが容易です。
- psutil の優先度設定や CPU affinity は権限によって失敗することがあります（警告ログのみ）。

---

## ディレクトリ構成（主要ファイル）

（抜粋: 実際のリポジトリは下記以外のファイルも存在する可能性があります）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数読み込み・Settings
    - config_setup.py                 — .env 対話式ウィザード
    - validate_config.py              — 設定検証 CLI
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py  — ペーパートレード検証レポート
    - ai/
      - news_nlp.py                   — ニュース NLP（OpenAI 呼び出し）
      - regime_detector.py            — 市場レジーム判定（LLM + MA）
      - __init__.py
    - monitoring/
      - monitoring_db.py              — SQLite 監視 DB 層（スキーマ初期化）
      - system_monitor.py             — システム状態・データ鮮度監視
      - trade_monitor.py              — 注文滞留・約定異常監視
      - risk_monitor.py               — ドローダウン・ポジション上限監視
      - kill_switch.py                — Kill Switch（flag 書き込み）
      - monitoring_engine.py          — 監視ループ統括
      - alert_manager.py              — （アラート送信ロジック、実装場所）
    - execution/                       — 発注関連（OrderManager 等。実装ファイル群）
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
      - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py

---

## 追加情報 / 注意点

- デフォルト DB ファイルは `data/` 配下です（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` で上書き可）。data ディレクトリや DB ファイルは運用環境で適切に保護してください。
- .env は決してリポジトリにコミットしないこと（README ヘッダに注記や config_setup の出力にも同様の注意書きをしています）。
- AI 系機能を実行する場合、API 利用料やレートリミットに注意してください。本実装はエラー時にリトライ・フォールバック処理を含みますが、コストはユーザ負担です。
- run_monitoring は MONITOR_POLL_INTERVAL（秒）でポーリング。環境変数で上書き可。無効値が設定された場合はデフォルト 60 秒にフォールバックします。

---

この README はリポジトリ内の主要な機能と利用方法をまとめた概要です。各モジュール（特に execution/*、monitoring/*、ai/*）の詳細な仕様や拡張ポイントは該当ソースコードの docstring とコメントを参照してください。質問や追加ドキュメント化希望があればお知らせください。
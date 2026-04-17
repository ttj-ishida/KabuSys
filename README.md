# KabuSys

日本株向け自動売買システムの一部を切り出したコードベース。  
この README はリポジトリ内の主要モジュール（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニュース処理など）を使い始めるための手引きを日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存関係
- セットアップ手順
- 環境変数と設定 (.env)
- 使い方（主要な CLI / モジュール）
- ディレクトリ構成
- 運用 / 開発メモ

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するシステムです。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine（発注エンジン）: 実際の発注処理（本番 / ペーパートレード）
- Monitoring（監視）: システム状態・注文状態・リスク監視、Kill Switch
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、ポジションサイズ算出
- Research（リサーチ）: ファクター計算、将来リターン、統計解析
- AI（ニュース NLP / レジーム判定）: OpenAI を用いたニュースのセンチメント評価・市場レジーム判定
- Tools: ペーパートレード検証レポート等のユーティリティ

設計上の方針として、ルックアヘッドバイアス回避（現在時刻の参照を限定する）、ペーパートレードと本番 DB の分離、フォールバック／フェイルセーフを重視しています。

---

## 機能一覧

- Execution
  - 本番 / ペーパートレードの切り替え（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント生成（Mock も利用可能）
  - リスク管理 (RiskManager)、注文管理（OrderManager / Reconciler）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態/データ鮮度の監視
  - TradeMonitor: 注文滞留、約定価格の異常検出
  - RiskMonitor: ドローダウン、ポジション上限の監視とアラート記録
  - KillSwitch: 条件に応じた停止フラグの作成（data/kill.flag）
  - MonitoringEngine: 各モニタを定期的に呼ぶポーリングループ
- Portfolio
  - 候補選定 (select_candidates)
  - 等比率 / スコア加重の重み計算
  - セクター制限適用、レジーム乗数の計算
  - ポジションサイズ計算（リスクベース、等配分等）、単元株丸め、aggregate cap
- Research
  - Momentum / Volatility / Value のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースセンチメント: raw_news を集約して OpenAI へバッチ送信、ai_scores へ結果書き込み
  - レジーム判定: ETF 1321 の MA とマクロニュースで市場レジーム（bull/neutral/bear）を算出
- Tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを生成

---

## 前提条件 / 依存関係

主な Python パッケージ（プロジェクトに requirements.txt がない場合は下記をインストールしてください）:

- python >= 3.9（型アノテーションで | を使用）
- duckdb
- psutil
- openai (OpenAI Python SDK) — AI 機能を使う場合
- PyYAML（config 検証で YAML 検査を行う場合）
- （SQLite は標準ライブラリで使用）

インストール例:
pip install duckdb psutil openai pyyaml

※ 実際にはプロジェクトの requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・アクティブ化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （存在する場合）
   - あるいは最低限: pip install duckdb psutil openai pyyaml

4. .env の準備（対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話で J-Quants トークンや KABU_API_PASSWORD、DB パス等を設定できます。
   - もしくはプロジェクトルートに .env ファイルを手動で作成

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 問題があれば修正。--strict オプションで警告もエラー扱いにできます。

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution モード。値: development | paper_trading | live（デフォルト: development）
  - paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録される
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（ペーパートレードの約定モード、instant|partial|never|reject）
- OPENAI_API_KEY（AI 機能利用時に必要）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START（"1" にすると Execution 起動時に kill.flag を自動クリア）
- MONITOR_POLL_INTERVAL（Monitoring のポーリング間隔秒、デフォルト 60）
- PID_FILE_PATH（ExecutionEngine の PID ファイル、デフォルト: data/execution.pid）
- KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）に .env/.env.local がある場合、自動で読み込まれます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（主要コマンド例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して data/paper_trading.db に記録（本番 DB とは分離）
    - 起動後は data/execution.pid に PID が書かれます
    - 停止: data/stop_requested.flag を作成すると graceful に停止（監視スクリプト・手動でも可能）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
  - 監視は常に「本番 sqlite_path」（Settings.sqlite_path）を参照します（監視用 DB は本番 DB を想定）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH が優先されます（デフォルト: data/paper_trading.db）

- AI 関連（ライブラリ関数）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡してニューススコアを ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ書き込む
  - これらはライブラリ関数として呼び出す想定です。OpenAI キーは api_key 引数か環境変数 OPENAI_API_KEY で与えます。

---

## 重要なフラグ / ファイル

- data/execution.pid
  - Execution 起動時に書き込まれる PID ファイル。SystemMonitor はこのファイルを参照してプロセス存否をチェックします。

- data/kill.flag
  - KillSwitch が危険条件（ドローダウン等）を検知した際に作成される停止フラグ。ExecutionEngine はこれを参照して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリア（本番では通常 0 を推奨）。

- data/stop_requested.flag
  - run_execution / run_monitoring の外部停止（手動停止）用フラグ。存在を検知するとループを抜けます。

---

## ディレクトリ構成

リポジトリの主要なディレクトリ / ファイル（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - utils/
      - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
    - execution/                — 発注関連（OrderManager, Engine, BrokerFactory 等）
    - monitoring/
      - monitoring_db.py       — SQLite ベースの監視 DB レイヤ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py       — （アラート送信ロジック）
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
    - tools/
      - paper_verification_report.py

データ / 設定ファイル（プロジェクトルート想定）
- .env, .env.local
- data/
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (ペーパートレード用 DB)
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## 運用 / 開発メモ

- ペーパートレードと本番データは明確に分離されています。KABUSYS_ENV=paper_trading にすると paper_trading 用 SQLite にデータが記録され、本番 SQLite は使用されません（監視は別途本番 sqlite_path を参照する点に注意）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）を起点に行われます。テスト時など自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL（秒）で監視の間隔を調整できます。不正な値（0 や負数）を与えるとデフォルト（60秒）にフォールバックします。
- OpenAI を使う AI 機能は API のレート制限や一時エラーに対してエクスポネンシャルバックオフでリトライする実装になっています。API キーは OPENAI_API_KEY 環境変数か関数引数で渡してください。
- DuckDB 側のテーブル（prices_daily, raw_financials, raw_news 等）が想定どおり用意されていない場合、Research / AI の処理は正常に動作しません。validate_config で config/*.yaml の存在チェックや DB パスの親ディレクトリ存在チェックを行えます。
- 開発時は LOG_LEVEL=DEBUG にすると詳細ログを得られます。標準では INFO。

---

もし README に追加したい情報（API ドキュメント、データベーススキーマ、実行時のログ例、CI セットアップ手順など）があれば教えてください。必要に応じて追記・整形して提供します。
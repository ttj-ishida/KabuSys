# KabuSys

日本株自動売買システムの軽量コアライブラリ群（監視 / 実行 / ポートフォリオ構築 / 研究 / AI 補助等）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づいて作成されています。

- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコア部分を提供する Python パッケージです。主要な機能は次のとおりです。

- 実行エンジン（ExecutionEngine）を起動してブローカーに注文を送信（本番 / ペーパートレード対応）
- 監視サブシステム（MonitoringEngine）によるプロセス・システム状態・注文・リスクのポーリング監視とアラート／Kill Switch の制御
- ポートフォリオ構築（シグナル選定、重み計算、株数決定、セクター制限、レジーム補正）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー等） — DuckDB による高速集計
- AI 支援（ニュース NLP によるセンチメント計算／市場レジーム判定。OpenAI API を利用）
- 開発支援ツール: 環境設定ウィザード（.env 作成）、設定検証 CLI、Paper Trading 検証レポート生成

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — 実行エンジン起動（KABUSYS_ENV により本番 / ペーパー切替）
  - run_monitoring.py — 監視ループ起動（ポーリングで System/Trade/Risk をチェック）
- 設定関連
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 環境変数 / config/*.yaml の検証ツール
  - config.Settings — 環境変数のラッパー（デフォルト値・バリデーション含む）
- 監視
  - monitoring/monitoring_db.py — SQLite による監視ログ永続化（schema 初期化・マイグレーション）
  - monitoring/system_monitor.py / trade_monitor.py / risk_monitor.py — 各種監視ロジック
  - monitoring/monitoring_engine.py — 各 Monitor をまとめてポーリング、Kill Switch 評価、Alert 発火
  - monitoring/kill_switch.py — フラグファイルによる ExecutionEngine 停止トリガ
- 実行（概要）
  - execution/* — ブローカーファクトリ、ExecutionEngine、OrderManager、Reconciler、RiskManager 等（起動点は run_execution.py）
- ポートフォリオ構築
  - portfolio/portfolio_builder.py — 候補選定・重み計算（等重・スコア重み）
  - portfolio/position_sizing.py — 株数計算、ロット丸め、投下金額スケーリング
  - portfolio/risk_adjustment.py — セクターキャップ適用、レジーム乗数
- 研究（Research）
  - research/factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB ベース）
  - research/feature_exploration.py — 将来リターン、IC（Spearman）計算、ファクターサマリー
- AI
  - ai/news_nlp.py — raw_news を LLM（OpenAI）で評価して ai_scores を作成
  - ai/regime_detector.py — ETF の MA 指標 + マクロセンチメントから市場レジーム判定
- ユーティリティ
  - utils/logging_setup.py — 一貫したログ設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py — プラットフォーム差分を吸収したプロセス優先度 / CPU アフィニティ設定

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション（デフォルトを示す）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログファイル格納ディレクトリ（デフォルト: logs）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0|1）

run_monitoring.py 固有:
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒, デフォルト: 60）。1 未満・無効値はデフォルトにフォールバック。

制御用フラグファイル:
- data/stop_requested.flag — 存在すると run_execution/run_monitoring のループが終了する（手動停止用）
- data/kill.flag — Kill Switch が書き込む停止フラグ（ExecutionEngine 停止トリガ）
- data/execution.pid — ExecutionEngine の PID（実行中に作成される想定）

---

## セットアップ手順（開発／ローカル向け）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - 例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 依存パッケージをインストール（必要なライブラリ: duckdb, psutil, openai, PyYAML など）
   - requirements.txt が存在する場合:
     ```bash
     pip install -r requirements.txt
     ```
   - 最低限の手動インストール例:
     ```bash
     pip install duckdb psutil openai PyYAML
     ```

3. 対話式で .env を作成（推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードは .env の作成 / 更新を支援します。作成後は必ず `.env` を Git にコミットしないでください。

4. 設定の検証
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合
   python -m kabusys.validate_config --strict
   ```

5. DB 用ディレクトリ作成（必要なら）
   ```bash
   mkdir -p data logs
   ```

注: 実際の本番運用では kabuステーション の設定や J-Quants のトークン等、外部サービスの正しい値を設定してください。KABUSYS_ENV=live のときは特に注意深く設定を確認してください（validate_config が補助します）。

---

## 使い方（主要コマンド）

- 実行エンジンを起動（本番 or paper_trading は KABUSYS_ENV で切替）
  ```bash
  python -m kabusys.run_execution
  ```
  - ペーパートレードでは mock ブローカーを使用し、データは `data/paper_trading.db` に分離して記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします（安全措置）。
  - 実行中に停止するには `data/stop_requested.flag` を作成するか、ExecutionEngine の停止機構で終了します。

- 監視ループを起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - デフォルトポーリング間隔は 60 秒。環境変数で変更可:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番用の SQLite（Settings.sqlite_path）を使用します（監視ログは環境に依存せず本番 DB へ書きます）。

- .env の作成・更新ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（ニューススコア / レジーム判定）はライブラリ API 経由で呼び出します（OpenAI API キー必須）。
  - 例（ライブラリ関数呼び出し）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

---

## 停止・Kill Switch 制御

- run_execution / run_monitoring はそれぞれプロジェクトの data ディレクトリ内にある stop_requested.flag を監視しています。これを作成するとループは優雅に終了します。
  ```bash
  # 停止要求を出す
  touch data/stop_requested.flag

  # 停止要求を取り消す（削除）
  rm -f data/stop_requested.flag
  ```

- Kill Switch（自動停止）は監視サブシステムが異常（例: ドローダウン超過、ポジション上限超過）を検出したときに `data/kill.flag` を作成します。ExecutionEngine 側は kill.flag の存在を起点に挙動を設計することで緊急停止を実現します。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主なファイル・フォルダ（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - execution/               — ExecutionEngine 関連（broker, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py       — SQLite schema & DB 操作ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信管理: LINE 等、実装参照）
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
  - utils/
    - logging_setup.py
    - process_priority.py

プロジェクトルートには:
- .env.example / .env (プロジェクト設定)
- data/ — デフォルト DB / フラグ / pid ファイル等が置かれる想定
- logs/ — ログファイル（設定に応じて出力）

---

## 開発メモ / 注意点

- Settings は自動的にプロジェクトルートの .env を読み込みますが、自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
- run_monitoring は監視用 DB として常に Settings.sqlite_path を使います（環境に依らず本番 DB を用いる設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、専用の paper_sqlite_path を使って本番 DB と完全分離します。
- AI 機能を利用するには OpenAI API キーが必要です（環境変数 OPENAI_API_KEY）。
- DuckDB / SQLite のスキーマは起動時に必要に応じて作成・マイグレーションされます（monitoring_db.init_monitoring_db など）。
- 実運用では KABUSYS_ENV を `live` にした際の安全ガード（LINE 通知、kill_flag の取り扱い等）を十分に確認してください。

---

以上が主要な README 内容です。必要であれば、起動フロー図・API リファレンス（各関数の詳細シグネチャ）・運用 Runbook（デプロイ手順、バックアップ、監視 KPI）などの追加ドキュメントを作成します。どの情報を優先して追加しますか？
# KabuSys

日本株向け自動売買システム（プロトタイプ）

このリポジトリは、注文実行エンジン・監視・リスク管理・シグナル生成・リサーチ・ニュースNLP などを備えた日本株自動売買システムのコードベースです。開発用・ペーパートレード・本番（live）を想定した設定分離と、監視→Kill Switch による安全停止機構を持ちます。

---

## 主な概要（Project overview）

- ExecutionEngine: 発注ロジック、Order 管理、リスク管理を統合してセッション実行を行うメインエンジン。
- Monitoring: システムヘルス（CPU/メモリ/ディスク）、注文ログ、ドローダウン・ポジション制限を定期的にチェックし、必要時に Kill Switch を作動させる。
- Paper trading モード: `KABUSYS_ENV=paper_trading` で MockBroker を使用し、実 DB と完全分離してペーパートレードが可能。
- Research モジュール: DuckDB を使ったファクター計算（モメンタム・バリュー・ボラティリティ 等）や特徴量解析。
- AI モジュール: OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。
- ツール類: .env ウィザード、設定検証、ペーパートレード用検証レポート等。

---

## 機能一覧（Features）

- Execution
  - 実注文（live） / ペーパートレード（paper_trading）を環境で切替
  - RiskManager による発注制限（ポジション上限、利用率、ドローダウン等）
  - OrderRepository / OrderManager による永続化・管理
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常などの検出
  - RiskMonitor: ドローダウンやポジション数の監視とリスクログ記録
  - KillSwitch: 条件を満たすと `data/kill.flag` を書き込み ExecutionEngine を停止
  - AlertManager（拡張想定）による通知連携（LINE など）
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（情報係数）計測、統計サマリ
- AI
  - ニュースを LLM（OpenAI）でスコアリングして ai_scores に保存
  - マクロ記事 + ETF MA200 を合成して市場レジーム判定を行い DB に永続化
- Utilities
  - 簡易ログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - .env ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
- Tools
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

---

## セットアップ手順（Setup）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... ; cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存ライブラリをインストール
   - 最低限の推奨パッケージ（明示的な requirements.txt が無い場合の例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (config の内容チェックを行う場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実運用では requirements.txt / poetry / pipenv を使用してバージョン管理してください。

4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - このウィザードで `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` 等を設定します。
   - 生成した `.env` は絶対にリポジトリへコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合は `--strict` を付けて実行します。

6. データディレクトリ
   - デフォルトで sqlite/duckdb/log ファイルは `data/` / `logs/` に作られます。必要なら環境変数でパスを変更してください。

---

## 主要な環境変数（一部）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード
- 実行環境
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- データベース
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 用、デフォルト: data/paper_trading.db）
- ロギング
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト: INFO
  - LOG_DIR — ログファイル格納ディレクトリ（デフォルト: logs/）
- ペーパートレード挙動
  - PAPER_FILL_MODE — instant/partial/never/reject（ペーパーブローカーの約定ルール）
- 監視
  - MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト: 60）
- OpenAI
  - OPENAI_API_KEY — OpenAI を使う場合に必要

詳しい項目は `kabusys.config.Settings` を参照してください。

---

## 使い方（Usage）

起動スクリプト（パッケージモジュールとして実行）:

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ記録されます。
    - 起動時に `data/stop_requested.flag` が存在するとエンジンは起動を中止します。
    - エンジンは `data/execution.pid` に PID を書きます。

- Monitoring を起動（常駐監視ループ）
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60）。
    - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使います（環境値に関わらず監視 DB は共通）。
    - `data/stop_requested.flag` を置くと監視ループが終了します。

- .env 初期化（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db` で DB パスを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可。

- AI 機能（プログラムから呼び出す場合）
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも DuckDB 接続オブジェクト（duckdb.connect(...)）を渡して使います。
  - OPENAI_API_KEY を環境変数で設定するか、api_key 引数で明示してください。

停止・Kill Switch 関連:

- Kill Switch (監視側) が発動すると `data/kill.flag` を作成します。ExecutionEngine は起動中にこのフラグを検出して安全停止します。
- 手動での停止やテスト用に `data/stop_requested.flag` を用い、スクリプトがループを抜けるようにしています（run_monitoring / run_execution で使用）。

ログ:

- ログはデフォルトで stdout と `logs/<app_name>.log`（日次ローテーション、30日保持）に出力されます。
- LOG_DIR 環境変数でログディレクトリを変更できます。

---

## ディレクトリ構成（Directory structure）

主要ファイル／パッケージの抜粋:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 注文実行関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — 監視 DB（SQLite）アクセス層
    - system_monitor.py      — システム状態チェック
    - trade_monitor.py       — 注文ログ監視（ファイル内にあり）
    - risk_monitor.py        — ドローダウン／ポジション監視
    - kill_switch.py         — kill.flag の評価・書き込み
    - monitoring_engine.py   — 各モニタ統合ループ
    - alert_manager.py       — 通知管理（抽象）
  - portfolio/
    - portfolio_builder.py   — 候補選定・ウェイト算出
    - position_sizing.py     — 株数算出・スケーリング・単元処理
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるセンチメントスコアリング
    - regime_detector.py     — マクロセンチメント + MA によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/ (ランタイムに作られる)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレード)
    - kill.flag / stop_requested.flag / execution.pid

---

## 注意事項・運用上のポイント

- .env（機密情報）を絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では Kill Switch 周り・LINE 通知等を充分に設定し、安全に運用してください。
- OpenAI API の呼び出しは料金が発生します。AI 機能はオプションです。API キーやレート制限に注意してください。
- monitoring は監視用 DB（sqlite）に書き込みを行います。monitoring は常に `Settings.sqlite_path`（本番 DB）を参照する設計なので、テスト時の混同に注意してください（ペーパートレードの発注 DB は分離されています）。
- ログディレクトリ作成に失敗した場合、ファイル出力が無効化されコンソールのみで動作します（ログの取りこぼしに注意）。

---

必要であれば、README に起動例の具体的コマンドや systemd / Supervisor のサンプル unit、CI 用の簡易テスト手順などを追加します。どの情報が必要か教えてください。
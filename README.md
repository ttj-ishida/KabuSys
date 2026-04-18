# KabuSys

日本株向けの自動売買 / 研究用ライブラリ群および起動スクリプト群です。  
本リポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を用いたニュースセンチメント解析等のコンポーネントで構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような責務を持ちます。

- データベース（DuckDB / SQLite）を用いたデータ管理と集計
- 戦略用ファクター計算・特徴量解析（research）
- ポートフォリオ構築、ポジションサイズ計算（portfolio）
- ExecutionEngine による注文管理（本番 / ペーパートレード対応）
- 監視（System / Trade / Risk）と Kill Switch による自動停止
- OpenAI を用いたニュース NLP によるセンチメント評価（ai）
- 運用補助ツール（設定ウィザード、検証、検証レポート生成 等）

設計方針として、本番実行時の安全性（ペーパートレード分離、Kill Switch、冪等性など）を重視しています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 / mock broker を切り替え）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: 対話式で .env を生成・更新
  - validate_config.py: 環境変数 / config/*.yaml の妥当性チェック
- モニタリング
  - system_monitor / trade_monitor / risk_monitor：監視ロジック
  - monitoring_engine：各 Monitor の統合とアラート発行ポイント
  - monitoring_db：監視ログ用 SQLite スキーマとアクセス API
  - kill_switch：条件に応じた停止フラグ発行（data/kill.flag）
- ポートフォリオ構築
  - 候補選定、重み計算、セクターキャップ、ポジションサイズ計算（単元丸め・aggregate cap 対応）
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント算出（ai_scores へ書き込み）
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

---

## システム要件 / 依存関係（代表例）

- Python 3.10+
- 必須パッケージの例:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config YAML の検証を行う場合）
- SQLite（標準ライブラリで利用）

（実際の requirements はプロジェクトの packaging / requirements ファイルに合わせてください）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は少なくとも duckdb, psutil をインストール）

4. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabuAPI / DB パス / LOG_LEVEL 等を設定します。
   - 生成される .env は絶対に git にコミットしないでください。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. 必要に応じて data ディレクトリ作成（logs は logging_setup が自動作成します）
   - mkdir -p data logs

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 運用 / 実行
  - KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
    - paper_trading: MockBrokerClient を使用し、ペーパートレード DB (PAPER_TRADING_SQLITE_PATH) に記録
    - live: 実際に発注が行われるため取り扱い注意
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…） デフォルト: INFO
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で消すか（0/1、デフォルト: 0）

- 監視関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: アラート閾値（%）

- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector で使用）

---

## 使い方（よく使うコマンド）

- 設定ウィザード（.env を対話式で作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 本番 / ペーパートレードは KABUSYS_ENV によって切り替わる
  - python -m kabusys.run_execution
  - 注意: 起動前に data/kill.flag や data/stop_requested.flag があると起動/継続をしない設計の箇所があります

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成（SQLite を直接指定可能）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI: ニューススコア / レジーム判定（API キー必須）
  - OPENAI_API_KEY を設定してスクリプトやモジュールを呼び出す
  - 例（プログラム内呼び出し）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")

---

## 運用／停止

- Kill Switch
  - RiskMonitor 等の条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine に停止シグナルを送る設計です。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

- 強制停止
  - プロジェクトルートの data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して停止します。
  - run_execution は data/execution.pid を PID ファイルとして使います。

---

## ログ

- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- デフォルトは stdout 出力 + 日次ローテートされるファイル出力（logs/<app_name>.log）を使用します。
- ログディレクトリは自動作成されますが、作成に失敗した場合はファイル出力が無効化され stdout のみになります。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ / 永続化 API
    - system_monitor.py       — システム状態監視
    - trade_monitor.py        — 発注 / 約定監視（実装ファイルあり）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - monitoring_engine.py    — 各 Monitor の統合ループ
    - kill_switch.py          — Kill Switch 制御
    - alert_manager.py        — アラート送信（LINE などの実装に依存）
  - execution/                — Execution 系コンポーネント（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 発注株数計算
    - risk_adjustment.py      — セクター制限 / レジーム乗数
  - research/
    - factor_research.py      — ファクター計算
    - feature_exploration.py  — IC, forward returns, 統計
  - utils/
    - logging_setup.py        — ログユーティリティ
    - process_priority.py     — プロセス優先度設定ユーティリティ

（注）上記は主要ファイルの抜粋です。詳細は各モジュールの docstring / ソースを参照してください。

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV=live のときは本番発注が行われます。環境変数や kill flag の設定を十分確認してください。
- ペーパートレード時は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録され、本番 DB と完全に分離されます。
- モジュールの多くは外部 API（kabuステーション、OpenAI 等）に依存します。API キーやネットワークの取り扱いには注意してください。
- ローカルで初めて使う場合は、まず config_setup → validate_config → run_monitoring（監視）→ run_execution（実行）の順で動作確認するのがおすすめです。
- .env は安全に管理し、Git 等へコミットしないでください。

---

README に書かれている以外の詳細（各モジュールのパラメータ、内部アルゴリズムや API レスポンス仕様）は各モジュールの docstring / ソースに注釈があります。必要があれば特定モジュールのドキュメントを生成したり、利用例を追加できます。
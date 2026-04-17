# KabuSys

日本株向け自動売買システムのリファレンス実装（モジュール群）。
このリポジトリは発注エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI ベースのニュース評価などを含むコンポーネント群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような機能を持つ自動売買フレームワークの骨組みです。

- ExecutionEngine（発注エンジン）: ブローカークライアント経由で注文を送信・管理するエンジン。
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、本番 DB と分離された paper_trading 用 SQLite に記録します。
- Monitoring（監視）: システム状態、注文滞留、ドローダウン等を定期的にチェックしてログ・アラートや Kill Switch を管理。
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、ポジション決定（単元丸め・リスク制限）。
- Research（リサーチ）: DuckDB 上の時系列データを使ったファクター計算・特徴量解析。
- AI（ニュース NLP / レジーム検出）: OpenAI API を使ったニュースセンチメント集計や市場レジーム判定。
- ユーティリティ: 環境変数管理、プロセス優先度設定、各種ツールスクリプト。

設計方針として「本番 DB と開発/ペーパートレード DB の分離」「ルックアヘッドバイアス回避」「外部 API 呼び出しの失敗時は安全側（フォールバック）」などが組み込まれています。

---

## 主な機能一覧

- 実行関連
  - ExecutionEngine 起動スクリプト: src/kabusys/run_execution.py
  - Paper Trading モード（完全分離 DB、MockBrokerClient）
  - Kill Switch（data/kill.flag）によるエンジン停止
- 監視関連
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度を監視
  - TradeMonitor: 注文滞留・約定異常チェック
  - RiskMonitor: ドローダウン・ポジション上限チェック
  - MonitoringEngine: 上記を束ねるポーリング実行（run_monitoring.py）
- ポートフォリオ構築
  - 候補選定、等重配分・スコア加重、セクター制限、ポジションサイズ計算
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）計算
- AI
  - news_nlp: raw_news をまとめて OpenAI へ送り銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ETF（1321）MA とマクロニュースを合成して市場レジーム判定
- 各種ツール
  - 設定ウィザード: config_setup.py（.env の初期作成/更新）
  - 設定検証 CLI: validate_config.py
  - Paper Trading 検証レポート: tools/paper_verification_report.py

---

## セットアップ手順（ローカル）

1. Python 環境を作成（推奨: 3.10+）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 実装ファイルに依存するパッケージの例:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証時に使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt は本リポジトリに含まれていないため、プロジェクト用途に合わせて必要パッケージを揃えてください。

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 手動作成: プロジェクトルート（pyproject.toml か .git のあるディレクトリ）に `.env` を置く。
   - 自動ロード: デフォルトで .env を自動読み込みします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — AI 機能を利用する場合に必要
   - KABUSYS_ENV — 実行環境（development | paper_trading | live）
   - 他: DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_LEVEL など（デフォルトが設定可）

5. DB 初期化
   - Monitoring 用 SQLite は Monitoring モジュール起動時にテーブルを作成します（init_monitoring_db）。
   - DuckDB ファイル（データ・時系列テーブル）は研究・ファクター処理で使用します。適切なスキーマ/データが必要です。

---

## 主要な環境変数（抜粋とデフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — default: development
- DUCKDB_PATH: DuckDB ファイルパス — default: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite パス — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite — default: data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） — default: INFO
- PAPER_FILL_MODE: paper_trading の注文約定挙動（instant / partial / never / reject） — default: instant
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） — default: 60
- PID_FILE_PATH / KILL_FLAG_PATH: 実行時に使われるフラグ/ファイルパス（defaults: data/execution.pid, data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1） — default: 0

.env の雛形は config_setup で生成できます。自動ロードの詳細は src/kabusys/config.py を参照してください。

---

## 使い方（コマンド例）

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗扱い（CI等）: python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数で間隔変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  監視プロセスは data/stop_requested.flag を検知するとループを終了します（プロジェクトルート内の data/ にある stop_requested.flag）。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します。
  - エンジンは data/stop_requested.flag を検知すると停止処理を始めます。実行時 PID は data/execution.pid に書き込まれます。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 簡易に PAPER_TRADING_SQLITE_PATH 環境変数を使うこともできます。

- AI 機能（ニューススコア・レジーム判定）
  - news_nlp.score_news / ai.regime_detector.score_regime を呼ぶ API があります（OpenAI API Key が必要）。スクリプト経由での実行例は実装ファイル内の docstring を参照してください。

---

## 停止・Kill Switch の仕組み

- 停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring などのループはこのファイルを検知して優雅に終了します。
- Kill Switch:
  - data/kill.flag — KillSwitch クラスが作成。RiskMonitor 等の評価で発動するとこのファイルを書き込み、ExecutionEngine に停止指示を出します。
  - Kill Switch の自動クリアは KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にクリアされます（本番では 0 推奨）。

---

## 開発者向けメモ

- 設定の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を読み込みます。テスト時に自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings クラス（src/kabusys/config.py）を経由して設定へアクセスできます。
  - 例: from kabusys.config import settings; settings.sqlite_path
- プロセス優先度や CPU affinity の設定は src/kabusys/utils/process_priority.py に実装されています（psutil を利用）。
- DuckDB を使うリサーチ/AI モジュールは、prices_daily 等のテーブル定義が前提です。分析/研究用のデータ準備が必要です。
- OpenAI 呼び出しは各モジュール内でリトライやレスポンス検証を行うようになっており、失敗時は安全フォールバック（例: スコア=0）します。

---

## ディレクトリ構成

リポジトリの重要ファイル・ディレクトリ（src/kabusys 以下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（監視ログ）
    - system_monitor.py       — システム状態監視
    - trade_monitor.py        — 注文監視（滞留・価格異常）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch 実装（flag ファイル）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信処理の管理）※実装ファイル参照
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・投下資金制御
    - risk_adjustment.py      — セクター制限・レジーム乗数
  - research/
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - monitoring/                — （上記）
  - utils/
    - process_priority.py     — プロセス優先度・CPU affinity
  - portfolio/                 — （上記）
  - execution/                 — 注文関連（OrderRepository 等）※詳細は該当ファイル参照
  - data/                      — 実行時に使用される既定の場所（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等）

- project root:
  - .env(.local)              — 環境変数（推奨して Git には含めない）
  - data/                     — 実行時ファイル（kill.flag, stop_requested.flag, *.db, execution.pid など）

---

## よくある運用上の注意

- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を必ず確認してください。validate_config は live 環境向けの追加警告を出します。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。開発用途のみで有効にしてください。
- Paper Trading では本番 DB とは別の PAPER_TRADING_SQLITE_PATH に記録され、MockBrokerClient を使用して実取引を行わないように設計されています。
- OpenAI 利用時は API キーの管理（環境変数）とコストに注意してください。AI モジュールは結果のバリデーション・リトライを行いますが、モデル応答の保証はありません。

---

必要に応じて README の補足（例えば各モジュールの関数一覧、DB スキーマ詳細、サンプル .env テンプレート、CI 用コマンドなど）を追加できます。要望があれば追記します。
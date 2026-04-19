# KabuSys

日本株向けの自動売買システム用コンポーネント群です。  
このリポジトリには実行エンジン／監視／ポートフォリオ構築／リサーチ／AI ベースのニュース解析など、運用に必要なユーティリティが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような役割を持つモジュール群で構成されています。

- ExecutionEngine（run_execution.py）: 発注エンジン（本番 / ペーパートレード対応）
- Monitoring（run_monitoring.py）: システム・注文・リスク監視のポーリングループ
- Portfolio（kabusys.portfolio）: 銘柄選定・重み付け・株数計算・セクター制約など
- Research（kabusys.research）: ファクター計算、特徴量探索、IC 計算
- AI（kabusys.ai）: ニュースのセンチメント解析、レジーム判定（OpenAI API を利用）
- Tools（kabusys.tools）: レポート生成などのユーティリティスクリプト
- utils: ログ設定・プロセス優先度設定など運用ユーティリティ
- config: 環境変数の読み込み・Settings クラス、対話式設定ウィザード・検証ツール

設計上の注意点:
- .env / 環境変数で設定を行う（自動ロード機能あり）。本番運用時は .env をリポジトリに含めないこと。
- Paper Trading（`KABUSYS_ENV=paper_trading`）時は本番 DB と分離された SQLite を使用。
- AI 機能は OpenAI API（API キー）を必要とします。

---

## 主な機能一覧

- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、data/paper_trading.db に記録
  - 停止フラグ（data/stop_requested.flag）で安全停止
  - PID ファイル出力（data/execution.pid 等）
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - SystemMonitor／TradeMonitor／RiskMonitor を使用して定期監視とアラート発行
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- 設定ウィザード: python -m kabusys.config_setup
  - .env の対話式作成／更新
- 設定検証 CLI: python -m kabusys.validate_config
  - .env と config/*.yaml の基本チェック（--strict オプションあり）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ロジック
  - 銘柄選定、等配分／スコア配分、リスクベースの単元株丸め、セクター上限の適用など
- リサーチ機能
  - モメンタム／ボラティリティ／バリュー等のファクター計算、将来リターン、IC、統計要約
- AI 機能
  - ニュース記事を LLM（gpt-4o-mini）でスコアリング（ai_scores 更新）
  - マクロセンチメント + ETF ma200 を使った市場レジーム判定（market_regime 更新）

---

## 前提（依存関係）

最低限必要な Python パッケージ（代表例）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証で必要）

実際の依存関係はプロジェクトの requirements.txt / poetry 等で管理してください。

---

## セットアップ手順（例）

1. リポジトリを取得
   - git clone ... && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って必須値を入力（J-Quants トークン、kabu API パスワード など）

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正（--strict を付ければ警告も失敗扱い）

6. データディレクトリ / ログディレクトリの確認
   - デフォルト DB / ログ:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - logs/: ログファイルを保存
   - 必要に応じて環境変数でパスを上書き可能（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR）

---

## 主要な環境変数

（重要なもののみ抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- OPENAI_API_KEY (AI 機能利用時に必須)
- PAPER_FILL_MODE (paper_trading の MockBroker 挙動; instant | partial | never | reject)
- MONITOR_POLL_INTERVAL (監視ループの秒間隔、run_monitoring 用)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)

Notes:
- Settings クラスが環境変数を読み込みます。
- 自動 .env ロードはプロジェクトルート検出に基づきます。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（実行コマンド）

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると Paper Trading モード（別 DB）になります
  - 停止方法: data/stop_requested.flag を作成するか、エンジンのログを見て手動停止
  - 実行中は data/execution.pid に PID を書きます

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で調整（デフォルト 60）
  - 監視は本番 sqlite_path を使用（環境に依らず）

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラムから呼ぶ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは argument または環境変数 OPENAI_API_KEY

---

## 停止 / Kill スイッチ類

- data/stop_requested.flag
  - run_monitoring / run_execution が見ている停止フラグ。ファイル存在でループを終了します。
- data/kill.flag
  - KillSwitch（リスクトリガー）により作成され、ExecutionEngine に停止を促す手段として扱われます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番注意）。

---

## ログ

- デフォルトは logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ローテーション: 日次、30日分保持
- stdout へも出力されるため、systemd / cron 等のログ統合がしやすい設計です

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — Settings と .env 自動読み込みロジック
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

packages:
- execution/               — 実行エンジン関連（broker, engine, order_manager 等）※詳細は該当ディレクトリ参照
- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化 + 永続化ラッパ
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag の作成 / 解除
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - alert_manager.py       — （アラート発行用。LINE などに通知）
  - trade_monitor.py       — 注文状態監視（滞留注文・約定異常等）
- portfolio/
  - portfolio_builder.py   — 候補選定・重み付け
  - position_sizing.py     — 株数決定・スケーリング・丸め
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — Momentum / Volatility / Value 計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py            — ニュースセンチメント解析（OpenAI）
  - regime_detector.py     — レジーム判定（ma200 + マクロセンチメント）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

プロジェクトルート:
- data/                    — SQLite / PID / flag ファイル等のデフォルト配置先
- logs/                    — ログファイル（デフォルト）

---

## 追加メモ / 運用上の注意

- DB マイグレーション: monitoring_db.init_monitoring_db は冪等にテーブルとカラムを作成します（簡易マイグレーション含む）。
- Paper Trading は本番 DB と分離して運用することを強く推奨します（Settings.is_paper を活用）。
- AI 系機能は外部 API を利用するため、API エラーやレート制限に備えた再試行・フェイルセーフ設計になっています。API キーは厳重に管理してください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。
- run_monitoring は MONITOR_POLL_INTERVAL の値が不正だとデフォルトにフォールバックします（値は 1 秒以上）。

---

README はここまでです。運用に関する補足や実装の詳細について追記希望があれば対象箇所（例: ExecutionEngine の起動フロー、Broker の実装、DB スキーマ詳細など）を指定してください。
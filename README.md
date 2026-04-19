# KabuSys

日本株向けの自動売買／研究プラットフォーム（モジュール群）。  
本リポジトリは運用用の ExecutionEngine／Monitoring、ポートフォリオ構築、ファクター計算、AI を使ったニュース評価などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的をもつモジュール群から構成されます。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注・注文管理・リスク管理を行う。
- 監視（Monitoring）: システム稼働／データ鮮度／注文ログ／リスクを定期的に監視し、kill flag を出すことで実行エンジンを停止させる。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクター制約やレジーム乗数の適用。
- 研究（Research）: DuckDB を使ったファクター計算（モメンタム／ボラティリティ／バリュー）や特徴量解析。
- AI モジュール: OpenAI を使ったニュースセンチメント（news_nlp）、市場レジーム判定（regime_detector）。
- ユーティリティ: 設定読み込み、.env ウィザード、設定検証、ログ設定、プロセス優先度設定など。
- ツール: Paper Trading 検証レポート生成スクリプト等。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード: `python -m kabusys.config_setup`
  - 設定検証 CLI: `python -m kabusys.validate_config [--strict]`
- 実行系
  - `python -m kabusys.run_execution`：ExecutionEngine 起動（KABUSYS_ENV により本番/ペーパー切替）
  - 停止は `data/stop_requested.flag` / `data/kill.flag` を用いる制御
- 監視系
  - `python -m kabusys.run_monitoring`：SystemMonitor をポーリングして監視ログを記録
  - モニタリングエンジンでリスク・注文滞留・プロセス停止等のアラート発行
- データ層
  - DuckDB：分析用（デフォルト `data/kabusys.duckdb`）
  - SQLite：監視・注文ログ（デフォルト `data/monitoring.db`）、ペーパー時は `data/paper_trading.db`
- 研究・ポートフォリオ
  - ファクター計算（momentum / volatility / value）
  - ポートフォリオ候補選定・重み付け・ポジションサイズ算出
- AI（OpenAI）
  - ニュースをまとめて LLM に投げ、銘柄ごとのスコアを ai_scores テーブルへ登録
  - レジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
  - API 呼び出しは再試行（指数バックオフ）付き、安全フォールバックあり
- ツール
  - Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report`

---

## 必要条件（推奨）

- Python 3.10+
- OS: Linux / macOS / Windows（ただし一部機能は POSIX 固有の扱いあり）
- 必要 Python パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML の中身を確認したい場合、なくてもスキップされます）
- SQLite は Python 標準ライブラリに含まれます

例（pip インストール）:
pip install duckdb psutil openai PyYAML

※ requirements.txt はリポジトリに含まれていないため、プロジェクトに合わせて追加してください。

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開する
2. Python 仮想環境を作成して依存パッケージをインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install duckdb psutil openai PyYAML
3. 対話式で .env を作成
   - python -m kabusys.config_setup
   - このウィザードで J-Quants / kabu API 等の必須値を設定します
4. 設定検証
   - python -m kabusys.validate_config
   - 本番準備の場合は --strict を付けて警告も FAIL 扱いにできます
5. ディレクトリ確認
   - data/ ディレクトリ（DB、PID、フラグファイル）と logs/（ログ）が自動作成されますが、パーミッションに注意してください

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な任意/デフォルト:
- KABUSYS_ENV: execution 環境 ("development" | "paper_trading" | "live"), デフォルト "development"
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

その他は `python -m kabusys.config_setup` で設定できます。プロジェクトは .env と .env.local をサポートし、OS 環境変数が優先されます。

---

## 使い方（主要コマンド）

- 対話式設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し DB は `data/paper_trading.db` に分離して記録されます
  - 実行中に `data/stop_requested.flag` が存在するとエンジンは停止します
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL (秒) でポーリング間隔を上書き可能（デフォルト 60）
  - 監視は常に本番 sqlite_path を使用（環境にかかわらず）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合: --db PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）
- AI スコアリング / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OPENAI_API_KEY（または api_key 引数）を必要とします

停止・Kill フラグ:
- data/kill.flag を書き込むことで ExecutionEngine に即時停止シグナルを発行できます（KillSwitch 経由）
- KillSwitch はリスクアラート（ドローダウン・上限超過）などで自動的に書き込まれます
- 起動時に KillFlag をクリアする設定（KILL_FLAG_CLEAR_ON_START）が可能ですが、本番では無効推奨

ログ:
- logs/<app_name>.log に日単位でローテート（デフォルト 30 日保管）
- setup_logging(app_name=...) により共通ログ設定を使用

---

## 実行時の注意点 / トラブルシュート

- Python バージョン: 型ヒント ("A | B") を使用しているため Python 3.10 以上を推奨
- DuckDB / OpenAI クライアントのバージョン差異による API 変更に注意
- PyYAML が無い場合、config validate は YAML 内容チェックをスキップします（警告が出ます）
- OpenAI 呼び出しは再試行ロジックを持ちますが、API キーやレート制限に注意してください
- プロセス優先度の設定や CPU affinity はプラットフォームの制約で失敗する場合があります（警告ログのみ）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス（.env 自動ロードロジック含む）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（pid / stop flag の使用）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- utils/
  - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイルローテーション）
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py — SQLite テーブル作成 & 永続化層
  - system_monitor.py — システム状態・データ鮮度チェック
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - trade_monitor.py — （注文関連の監視: code 内に実装あり）
  - monitoring_engine.py — 各 Monitor を束ねる
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — 通知送信（LINE 等、実装参照）
- execution/
  - execution_engine.py — ExecutionEngine 本体（起動ロジックは run_execution）
  - order_manager.py / order_repository.py / risk_manager.py / reconciler.py / broker_factory.py
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value 等の計算（DuckDB）
  - feature_exploration.py — 将来リターン計算・IC 等
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）と ai_scores 書き込み
  - regime_detector.py — マクロ＋ETF MA によるレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- data/ (実行時に生成・使用)
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid, stop_requested.flag, kill.flag など

---

## 開発者向けメモ

- DuckDB 接続を受け取り SQL + Python でファクターを計算する設計のため、分析ロジックは DB スキーマ（prices_daily / raw_financials 等）に依存します。
- AI モジュールはテスト用に OpenAI 呼び出しを差し替え可能な設計です（テストではモック化推奨）。
- 設定は OS 環境変数を優先しつつ .env / .env.local を読み込むため、CI／本番では環境変数方式が管理しやすいです。
- 本番運用時は KABUSYS_ENV=live 設定に伴う注意（LINE 通知、KILL_FLAG_CLEAR_ON_START の値確認など）があります。validate_config の警告を必ず確認してください。

---

以上が README の要約です。必要であれば、README に含める具体的なコマンド例や systemd / supervisor 用のサービス定義、サンプル .env.example のテンプレートも追加できます。どの詳細を追加しますか？
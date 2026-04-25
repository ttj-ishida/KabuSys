# KabuSys

日本株自動売買システムの軽量実装（ライブラリ＋起動スクリプト群）

このリポジトリは、戦略・ポートフォリオ構築、注文実行（本番／ペーパー分離）、監視、研究用ファクター計算、そして一部 AI 補助モジュールを含むモジュール群で構成されています。実行スクリプトはモジュール化されており、環境変数と `.env` による設定管理を想定しています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド例）
- よく使う環境変数
- ディレクトリ構成（ファイル説明）
- 運用上の注意

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントを持つ日本株向け自動売買プラットフォームのコア実装です。

- Execution Engine：注文作成・管理・約定処理（paper_trading 環境は MockBrokerClient を使用し、本番 DB と完全分離）
- Monitoring：システム状態、注文ログ、リスク（ドローダウン・ポジション上限）などの監視・アラート（kill switch を含む）
- Portfolio Construction：候補選定、重み付け、ポジションサイズ決定、セクター制限など
- Research：DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）や特徴量探索
- AI 補助：ニュース NLP による銘柄センチメント評価、マクロニュースを用いた市場レジーム判定（OpenAI 使用）
- ユーティリティ：設定読み込み、ログ設定、プロセス優先度設定など

---

## 主な機能一覧

- 設定管理
  - .env ワークフロー（自動読み込み、対話式設定ウィザード `config_setup.py`）
  - 設定検証 CLI `validate_config.py`
- 実行・監視
  - Execution 起動スクリプト（`run_execution.py`）
  - Monitoring 起動スクリプト（`run_monitoring.py`）
  - kill.flag による安全停止（KillSwitch）
  - stop_requested.flag による外部停止（起動スクリプト両方で監視）
- データベース
  - DuckDB（分析用、path: デフォルト `data/kabusys.duckdb`）
  - SQLite（監視・発注ログ、monitoring 用: `data/monitoring.db`、paper_trading 用: `data/paper_trading.db`）
  - 監視 DB 初期化・マイグレーションユーティリティ
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重、リスクベースのサイズ決定
  - セクター上限・レジーム乗数
- 研究（Research）
  - DuckDB 上でファクター計算（momentum/volatility/value）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）
  - ニュース集約 → LLM による銘柄別センチメント（`ai.news_nlp.score_news`）
  - マクロニュース + ETF MA200 乖離を合成したレジーム判定（`ai.regime_detector.score_regime`）
  - API 呼び出しは堅牢なリトライ・バリデーション実装あり

---

## セットアップ手順

前提
- Python 3.10 以上（ソースで型注釈に `|` を使用しているため）
- SQLite は標準ライブラリに含まれます
- 推奨 OS: Linux / macOS（プロセス優先度・CPU affinity の差異を吸収する実装あり）

1. リポジトリをクローン／チェックアウトしてプロジェクトルートへ移動
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
3. 必要パッケージをインストール
   - 最低限の依存（例）:
     - duckdb
     - openai
     - psutil
     - PyYAML（`validate_config` の YAML 検証を行う場合、任意）
   - pip install duckdb openai psutil PyYAML
   - 実際の requirements.txt があれば pip install -r requirements.txt を推奨
4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか環境変数をエクスポートしてください
   - 対話式ウィザードで作成: python -m kabusys.config_setup
   - 生成後、必須環境変数が正しく設定されているか検証: python -m kabusys.validate_config
5. データディレクトリ（logs / data）を作成（多くは起動時に作成されますが手動で作成しておくと権限問題が減ります）
   - mkdir -p data logs

---

## 使い方（基本コマンド）

- 設定ウィザード（.env を生成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗として扱う）: python -m kabusys.validate_config --strict

- Execution Engine を起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は `data/paper_trading.db`（本番 DB と完全分離）
    - 起動中に data/stop_requested.flag が作成されると安全に停止します
    - PID ファイル: data/execution.pid（設定可能）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - Monitoring は環境に関係なく本番の sqlite_path を使用して監視テーブルを初期化します（init_monitoring_db）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH で指定できます

- AI モジュール（プログラム経由で利用）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...)）を受け取り、内部で OpenAI API キー（OPENAI_API_KEY）を参照します
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）

---

## よく使う環境変数

（validate_config / Settings の内容を抜粋）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主な任意／設定系
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知（任意）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — Paper トレード時の約定モード（instant / partial / never / reject）

設定自動ロード
- プロジェクトルートから `.env` / `.env.local` を自動読み込み（OS 環境 > .env.local > .env）
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py
  - パッケージ定義（バージョン等）
- config.py
  - Settings クラス、.env 自動ロード、環境変数取得ユーティリティ
- config_setup.py
  - 対話式 `.env` 作成ウィザード
- validate_config.py
  - 設定検証 CLI（必須環境変数・ファイル存在等をチェック）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading は専用 DB を使用）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
- utils/
  - logging_setup.py — 統一的ログ設定（stdout + 日次ローテートファイル）
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・アクセスユーティリティ
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （注文ログの監視ロジック：コード内に参照あり）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の作成・判定
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py —（アラート送信ロジック）
- execution/
  - execution_engine.py, order_manager.py, risk_manager.py, reconciler.py, broker_factory.py, order_repository.py
  - （注文実行ロジック・ブローカ抽象化）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py — モメンタム／バリュー／ボラティリティ計算（DuckDB）
  - feature_exploration.py — forward returns, IC, factor summary
- ai/
  - news_nlp.py — ニュース記事を LLM で評価して ai_scores に書き込む
  - regime_detector.py — マクロニュース + ETF MA200 によるレジーム判定
- data/  (runtime)
  - data/stop_requested.flag — 起動スクリプトはこのファイルの存在を監視して安全停止
  - data/execution.pid — Execution の PID 保存先デフォルト
  - monitoring / db ファイル群（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）
- logs/  (runtime)
  - 日次ローテーションログ（デフォルト `logs/<app_name>.log`）

---

## 運用上の注意

- 本番時は KABUSYS_ENV=live を慎重に使用してください。`validate_config` は live 環境向けの追加警告を出します。
- kill.flag（Settings.kill_flag_path）と stop_requested.flag（data/stop_requested.flag）の挙動を理解して運用してください。
  - KillSwitch はリスク条件（ドローダウン/ポジション上限）で kill.flag を書き、Execution 側でそれを検出して停止できます。
  - start 時の kill_flag 自動クリアは KILL_FLAG_CLEAR_ON_START によって許可できますが、本番では `0` を推奨します。
- Paper trading は本番 DB と明確に分離されます。`KABUSYS_ENV=paper_trading` を設定することで `paper_sqlite_path` が使用されます。
- OpenAI を使う AI 機能は API 呼び出し料金・レイテンシ・信頼性に依存します。API キー管理とレート制限に注意してください。
- ログディレクトリに書き込み権限があることを確認してください。ファイルハンドラ作成に失敗するとコンソールのみでログが出力されます。
- Python バージョン互換性に注意してください（型アノテーション等の使用から Python 3.10+ を想定）。

---

以上が README の概要です。必要であれば次を提供できます：
- 具体的な systemd / supervisor 用の unit ファイル例
- Dockerfile / docker-compose の雛形
- requirements.txt の候補（現在コードで参照されているパッケージを列挙）
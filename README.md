# KabuSys

日本株向け自動売買システムの一部を構成する Python パッケージ。ポートフォリオ構築、リスク管理、監視、ペーパートレード検証、AI ベースのニュースセンチメント評価などの機能を備えています。

---

## 概要

このリポジトリは、自動売買のコアロジックと運用周辺ツールを含むモジュール群です。  
主な目的は以下です。

- 日次/リアルタイムのファクター計算・リサーチ（DuckDB を利用）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- ExecutionEngine（発注管理）の起動サポート（本番／ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- OpenAI を用いたニュース NLP によるセンチメント評価
- ペーパートレード検証レポート生成

---

## 主な機能一覧

- 環境設定ウィザード（.env 自動生成／更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env・config/*.yaml の検証）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
- Monitoring（System / Trade / Risk）起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- Monitor の統合実行エンジン（MonitoringEngine）
- リサーチモジュール（factor, feature exploration）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定・セクター制約）
- AI モジュール
  - news_nlp: OpenAI を使った銘柄毎のセンチメントスコア生成（ai_scores テーブル）
  - regime_detector: ETF 等の指標と LLM センチメントを合成して市場レジーム判定
- ユーティリティ
  - ログ設定（ログローテーション）
  - プロセス優先度 / CPU affinity 設定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート

---

## 前提条件

- Python 3.10+
- 必須（例）パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証であると便利）
- SQLite は標準ライブラリで使用

requirements.txt が無い場合は最低限以下をインストールしてください（例）:

pip install duckdb psutil openai PyYAML

（実際のプロジェクトでは requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - J-Quants や kabuAPI のトークン / パスワードなどを入力します
   - ウィザードで作成した .env は絶対に Git にコミットしないでください

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗と扱います: python -m kabusys.validate_config --strict

5. データディレクトリ（data）やログディレクトリ（logs）が自動作成されることを確認してください。ログ出力先はデフォルト `logs/`、SQLite/DuckDB のデフォルトは `data/` 配下です。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時の DB）
- PAPER_FILL_MODE: ペーパートレード時の fill 振る舞い（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（development 用。0/1）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_pw_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

---

## 使い方

### 環境設定ウィザード
- python -m kabusys.config_setup
  - .env を対話式に作成・更新します。

### 設定検証
- python -m kabusys.validate_config
  - .env と config/*.yaml の存在・簡易整合性をチェックします。
  - --strict を付けると警告も exit(1) 扱いになります。

### ExecutionEngine の起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録します。
  - 実行中の停止はプロジェクトルートの data/stop_requested.flag を作成することで行います（run_execution はこのフラグを監視して安全に停止します）。
  - 起動時、pid ファイル（例: data/execution.pid）を作成します。

### Monitoring の起動
- python -m kabusys.run_monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を使ってポーリング監視を行います。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 停止は data/stop_requested.flag を作成するか、Ctrl+C（KeyboardInterrupt）。

### Kill Switch / Stop フロー
- Kill 条件を検知すると monitoring 側で data/kill.flag を書き込みます（Settings.kill_flag_path）。
- ExecutionEngine は起動時に kill.flag を検出すると起動を阻止・または稼働中に kill.flag を検出すると停止します。
- kill.flag を手動でクリアする場合はファイルを削除（KillSwitch.clear() で自動処理も可能）。KILL_FLAG_CLEAR_ON_START=1 に注意（本番では 0 推奨）。

### Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - PAPER_TRADING_SQLITE_PATH 環境変数を使うか、--db で DB を指定できます。
  - 稼働率、注文成功率、レイテンシ等を解析し PASS/FAIL を出力します。

### AI関連（ニュース NLP / レジーム判定）
- kabusys.ai.score_news（関数）や kabusys.ai.regime_detector.score_regime を用いて、DuckDB 上のニューステーブルからスコアを算出・書き込みします。OPENAI_API_KEY の設定が必要です。
- API 呼び出しはリトライやフォールバックを実装しており、API エラー時はフェイルセーフ（スコア 0 等）で続行します。

---

## ログ

- ログはデフォルトで stdout とファイル（logs/<app_name>.log）へ出力されます（TimedRotatingFileHandler による日次ローテーション、30 日分保持）。
- setup_logging(app_name="execution") などを各起動スクリプトで呼び出しています。
- ログディレクトリは環境変数 LOG_DIR で変更可能。

---

## データベース（概念）

- DuckDB: 分析用（prices_daily, raw_financials, raw_news, ai_scores, market_regime 等）
  - デフォルトファイル: data/kabusys.duckdb
- SQLite: 監視・発注ログ用（monitoring.db）
  - Monitoring 用テーブル: system_status, trade_logs, positions, risk_logs, dashboard
  - ペーパートレード使用時は paper_trading.db に完全分離して記録されます（Settings.paper_sqlite_path）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py               — 環境変数 / 設定読み込み
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py           — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py    — 市場レジーム判定
- monitoring/
  - monitoring_db.py      — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py      — （trade_monitor 実装あり）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py      — （アラート送信処理）
- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

プロジェクトルート:
- .env (生成可能)
- config/ (各種 yaml テンプレート)
- data/ (DB・フラグファイル・pid 等)
- logs/ (ログファイル)

---

## 開発者向けメモ

- 自動ロード: config.py はプロジェクトルート（.git または pyproject.toml）を基に自動で .env を読み込みます。テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト: 各モジュールは純粋関数（DB 参照なし）と DB 操作を分離する設計になっています。ユニットテストは純粋関数を中心に書きやすく設計されています。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル作成・簡易マイグレーション（カラム追加）を行います。
- 外部 API: OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証を行う設計です。API キー管理は .env 経由で行ってください。

---

必要に応じて README に含めたい詳細（例: サンプル .env の完全版、systemd/cron でのデプロイ例、テスト実行手順、CI 設定例など）を教えてください。追加で追記します。
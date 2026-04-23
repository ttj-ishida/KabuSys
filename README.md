# KabuSys

日本株向けの自動売買システム（ライブラリ + 起動スクリプト群）のリポジトリ。  
このREADME はリポジトリ内の主要なモジュール群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニュース解析等）に基づき作成しています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 環境変数 / 設定
- ディレクトリ構成（主要ファイル説明）
- 運用メモ・注意点

---

プロジェクト概要
- KabuSys は日本株市場向けの自動売買プラットフォーム基盤です。
- 発注エンジン（ExecutionEngine）、監視（Monitoring）、リスク管理、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を使用）などを含むモジュール群を備えます。
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）の各モードをサポートし、設定は .env で行います。

---

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録して本番 DB と分離。
  - スレッドでセッションを実行し、stop フラグで優雅に停止。
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングして監視データを SQLite に永続化。
  - KillSwitch により重大事象時に data/kill.flag を書き込んで ExecutionEngine を停止させる仕組み。
  - ログやアラート送信（LINE など）を統合可能（設定次第）。
- 設定ウィザード・検証
  - config_setup.py: 対話式で .env を作成／更新するウィザード。
  - validate_config.py: .env と config/*.yaml の整合性チェック（--strict で警告を FAIL 扱い）。
- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定、重み計算（等金額／スコア加重）、ポジションサイズ計算、セクター制限、レジーム乗数等。
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）、将来リターン計算、IC（Information Coefficient）計測、統計サマリー。
  - DuckDB を用いたローカル集計処理を想定。
- AI（kabusys.ai）
  - ニュース記事を OpenAI（gpt-4o-mini）でスコアリングして ai_scores テーブルへ保存（ニュース NLP）。
  - 市場レジーム判定モジュール（regime_detector）で ETF の MA200 乖離と LLM によるマクロセンチメントを合成。
  - API 呼び出しはリトライやバックオフを備え、フェイルセーフで動く設計。
- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテーションファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - tools: paper_verification_report（ペーパートレード検証レポート生成）

---

セットアップ手順（開発環境例）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
     （プロジェクトに requirements.txt がない場合は次の主要依存に注意）
     - duckdb
     - psutil
     - openai
     - pyyaml（validate_config の YAML 検証オプション）
   - 例: pip install duckdb psutil openai pyyaml
4. .env の作成
   - python -m kabusys.config_setup
     → 対話形式で .env を生成します。
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - エラーがある場合は .env / config/*.yaml を修正してください。

---

使い方（代表的なコマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict
- ExecutionEngine を起動（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって動作が変わります（paper_trading / live / development）。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
- AI 機能（スクリプトや自作バッチから）
  - kabusys.ai.score_news を呼び出してニューススコアを生成（OpenAI API キー必要）
  - kabusys.ai.regime_detector.score_regime でレジーム判定・データベース書き込み

停止 / Kill 操作
- ExecutionEngine / Monitoring の優雅な停止は以下のフラグを使います:
  - data/stop_requested.flag : run_execution/run_monitoring が検知してループを終了します（起動スクリプトの実装参照）。
  - data/kill.flag : KillSwitch により作成されるファイルで、ExecutionEngine の停止トリガーになります。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

---

主要な環境変数（概要）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 運用／オプション
  - KABUSYS_ENV: execution モード（development / paper_trading / live）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB (monitoring.db)（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モードで使用）
  - PAPER_FILL_MODE: ペーパートレードの注文成立挙動（instant|partial|never|reject）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
  - MONITOR_POLL_INTERVAL: monitoring スクリプトのポーリング間隔（秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1）

詳細は kabusys.config.Settings のプロパティ定義を参照してください（バリデーションやデフォルト値を定義しています）。

---

ディレクトリ構成（主要ファイル）
（src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動ロードと Settings クラス（環境変数取得・検証）
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前チェック CLI（必須 env / config/*.yaml / path の存在など）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID 管理・stop フラグ監視）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL に対応）
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ作成・MonitoringDB ラッパー（log_system_status / log_trade_event / upsert_dashboard 等）
    - system_monitor.py
      - システムリソース / データ鮮度 / Execution PID の監視
    - trade_monitor.py
      - （trade monitoring ロジック）
    - risk_monitor.py
      - ドローダウン・ポジション上限監視（RiskMonitor）
    - kill_switch.py
      - kill.flag の作成／管理
    - monitoring_engine.py
      - 各 Monitor を束ねてポーリングし、アラート／KillSwitch をトリガー
    - alert_manager.py
      - （通知管理：LINE 等のラッパー想定）
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/
    - pipeline.py (データ取り込みユーティリティなど)
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

データ / ログファイル（運用時）
- data/: デフォルト DB / フラグ類を格納する想定ディレクトリ
  - data/monitoring.db (監視ログ SQLite)
  - data/paper_trading.db (ペーパートレード用 DB)
  - data/kabusys.duckdb (DuckDB)
  - data/kill.flag, data/stop_requested.flag, data/execution.pid
- logs/: ログファイル（アプリ名ごとに日次ローテート）

---

運用メモ・注意点
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意喚起があります）。
- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨。
- OpenAI を利用する機能は API キーが必要です。API 呼び出しはリトライやフォールバックが実装されていますが、コストやレート制限に注意してください。
- Monitoring / Execution の停止は stop_requested.flag（起動スクリプトで監視）または kill.flag（KillSwitch）で行います。運用手順をドキュメント化してください。
- monitoring_db.py は既存 DB に対して列追加の簡易マイグレーション（peak_value, latency_ms の追加）を行います。大きなスキーマ変更がある場合は注意。

---

さらに詳しく
- 各モジュールの実装コメント（docstring）に設計意図・使用方法が記載されています。具体的な拡張や運用手順は該当ファイルを参照してください。
- config/*.yaml（config ディレクトリ）についてはリポジトリ内のテンプレートや scripts を参照して生成してください（validate_config によるチェックを推奨）。

---

問題報告・開発
- バグや改善提案がある場合は issue を作成してください。機能追加時は既存の設定や DB 互換性に注意して実装してください。

以上。必要であれば README にサンプル .env のテンプレートや運用チェックリスト（起動順・監視項目）を追記します。どの情報を追加しますか？
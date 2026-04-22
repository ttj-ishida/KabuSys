# KabuSys — README (日本語)

概要
---
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。本リポジトリは以下の主要コンポーネントを含みます。
- ExecutionEngine：発注・注文管理・リスク管理等の実行系
- Monitoring：システム状態・注文状態・リスク監視と Kill Switch
- Portfolio / Strategy ツール群：銘柄選定、重み付け、ポジションサイズ計算
- Research：ファクター計算・特徴量探索
- AI モジュール：ニュースセンチメント評価・市場レジーム判定（OpenAI）
- CLI 支援ツール：.env ウィザード、設定検証、Paper Trading レポート生成 等

目的はアルゴリズム売買に必要な典型的な機能を分離して実装し、運用時の安全装置（監視・Kill Switch・ロギング等）を備えることです。

主な機能
---
- 実行環境切替（development / paper_trading / live）
  - paper_trading 時は MockBrokerClient を使って本番 DB と分離（data/paper_trading.db がデフォルト）
- ExecutionEngine（注文作成・約定処理・リコンシリエーション・リスク制御）
- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度の監視
  - TradeMonitor: 注文滞留や約定異常の検出（コード内に実装）
  - RiskMonitor: ドローダウン、ポジション上限の監視とリスクログの記録
  - KillSwitch: 条件に応じて data/kill.flag を書いて ExecutionEngine を停止させる
  - MonitoringEngine: 各 Monitor を束ねるポーリングループ
- ポートフォリオ構築: 候補抽出、等分配・スコア加重、セクター上限適用、ポジションサイズ算出（単元株丸め）
- Research: Momentum/Volatility/Value 等のファクター計算、将来リターン・IC 計算、統計サマリー
- AI:
  - news_nlp: raw_news を OpenAI でスコアリングし ai_scores に書き込む
  - regime_detector: マクロ記事＋ETF MA を合成して日次レジーム判定
- ツール:
  - .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- ロギングセットアップ（コンソール + 日次ローテートファイル）
- プロセス優先度 / CPU affinity の簡易ユーティリティ（psutil 利用）

前提 / 依存関係
---
推奨: Python 3.10+（動作確認は環境に依存します）

必須パッケージ（代表例）
- duckdb
- psutil
- openai  （AI 機能を使う場合）
- そのほか: sqlite3（標準）、logging（標準）

任意（YAML ファイル検証）
- PyYAML

インストール例（仮想環境推奨）
- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate（Windows は .venv\Scripts\activate）
- 必要パッケージのインストール（requirements.txt がない場合は個別に）
  - pip install duckdb psutil openai
  - pip install pyyaml  # 任意（config ファイル検証用）

セットアップ手順
---
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化し、必要パッケージをインストール（上記参照）
3. .env を作成
   - 対話ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
4. 設定の検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになる: python -m kabusys.validate_config --strict
5. データディレクトリ（data/）や logs/ は自動作成されますが、必要に応じて確認してください。

主要環境変数（抜粋）
---
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト 60）

使い方（起動 / 停止 / ツール）
---
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: MONITOR_POLL_INTERVAL=30）

- 停止方法
  - どちらの run_* スクリプトもプロジェクトルート/data/stop_requested.flag の存在を確認して安全に終了します。
  - 停止要求: touch data/stop_requested.flag（あるいはファイルを書き込む）
  - Kill Switch（重大な条件により実行系を即停止させたい場合）は monitoring 側が data/kill.flag を書き込みます。手動で kill.flag を作成すると ExecutionEngine が止まる設計（ただし運用ルールに従ってください）。
  - kill.flag を自動クリアしたい場合は .env の KILL_FLAG_CLEAR_ON_START=1 を設定（本番では推奨されません）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でデフォルト DB を指定可能

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（OPENAI_API_KEY）を必要とします。API の呼び出しは失敗時にフェイルセーフ（代替値）を使う設計ですが、キーの設定を推奨します。

ログ
---
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテート、30日保持）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。
- LOG_DIR 環境変数でログディレクトリを変更できます。

データベース
---
- DuckDB（分析用）: デフォルト data/kabusys.duckdb
- SQLite（監視ログ）: デフォルト data/monitoring.db
- Paper Trading 用 SQLite（paper_trading 時）: デフォルト data/paper_trading.db
- 起動時に必要なテーブルは init_monitoring_db により冪等的に作成されます。

ディレクトリ構成（主なファイル・概要）
---
src/kabusys/
- __init__.py
- config.py
  - .env の自動読み込み・Settings クラス（環境設定取得）
- config_setup.py
  - 対話式 .env ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングスクリプト

サブパッケージ（主要）
- kabusys/execution/
  - ExecutionEngine、OrderManager、RiskManager、BrokerFactory 等（発注ロジック）
- kabusys/monitoring/
  - monitoring_db.py（SQLite 永続化層）
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py, kill_switch.py, alert_manager.py 等
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築）
- kabusys/research/
  - factor_research.py, feature_exploration.py（ファクター計算・評価）
- kabusys/ai/
  - news_nlp.py（ニュースセンチメント -> ai_scores）
  - regime_detector.py（レジーム判定）
- kabusys/utils/
  - logging_setup.py（ログ設定）、process_priority.py（優先度設定）
- kabusys/tools/
  - paper_verification_report.py（Paper Trading レポート）

（例）簡易ツリー
- src/kabusys/
  - run_execution.py
  - run_monitoring.py
  - config.py
  - config_setup.py
  - validate_config.py
  - execution/
  - monitoring/
  - portfolio/
  - research/
  - ai/
  - utils/
  - tools/

設計上の注意 / 運用メモ
---
- paper_trading は本番 DB と分離するため、KABUSYS_ENV=paper_trading に設定してから起動してください。
- 環境変数は OS の値 > .env.local > .env の順で上書きされます。テスト用途で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。
- 実行中プロセスの優先度変更や CPU affinity の設定を行います（psutil を利用）。権限により設定できない場合は警告のみ出力します。
- OpenAI を使う機能は外部 API に依存するためレート制限やネットワークエラーに対応したリトライやフォールバック処理が入っていますが、API キーや利用料金に注意してください。

貢献 / 拡張
---
- Strategy・Execution の詳細ロジックは拡張可能です。mock ブローカー・テストスイートの追加を推奨します。
- 単元株（lot_size）や銘柄ごとの情報を持つマスタ実装、手数料・スリッページモデルの強化、バックテスト用インターフェース追加などが考えられます。

ライセンス
---
本リポジトリにはライセンス記述がない場合、利用前に作者に確認してください。

---

不明点や README に追加してほしい情報があれば教えてください（実行例や .env のサンプル、より詳しいディレクトリツリーなどを追加できます）。
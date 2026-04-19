# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）。

このリポジトリは戦略（ファクター計算・ポートフォリオ構築）、実行エンジン、監視（モニタリング）、AI（ニュースセンチメント / レジーム判定）などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つコンポーネント群を提供します。

- 戦略・研究:
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量探索・IC 計算・統計サマリー
  - ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制約 等）
- 実行:
  - ExecutionEngine（ブローカー抽象化を経由した発注管理・リスク管理）
  - paper_trading モードでは MockBroker による完全分離の DB を利用
- 監視:
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - kill.flag による ExecutionEngine 強制停止（Kill Switch）
- AI:
  - ニュース記事のセンチメントを OpenAI に問い合わせて ai_scores に保存
  - マクロニュース + ETF MA を用いた市場レジーム判定
- ユーティリティ:
  - ログ設定、プロセス優先度設定、.env ウィザード、設定検証、レポート 等

設計方針として、ルックアヘッドバイアス回避、フェイルセーフ（API失敗時のフォールバック）、DB の冪等操作を重視しています。

---

## 主な機能一覧

- .env 作成ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker（data/paper_trading.db を使用）
- 監視プロセス起動: python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.score_news — ニュースセンチメントを計算して ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime — レジーム判定と market_regime への保存
- ポートフォリオ構築ユーティリティ:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - セクターキャップ・レジーム乗数の適用

---

## 前提・依存関係（例）

最低限必要な Python ライブラリ（プロジェクトに requirements.txt がない場合の例）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の内容を検証したい場合に必要）

インストール例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン / checkout

2. 仮想環境を作成して依存パッケージをインストール
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt  (もし用意されていれば)
   - または個別に: pip install duckdb psutil openai pyyaml

3. .env の作成
   - 対話式ウィザードを推奨:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に `.env` を作成。
   - 自動ロード: デフォルトでプロジェクトルートの `.env` および `.env.local` を読み込みます。
     - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ等の作成（通常は自動作成されますが手動で準備しておくと安心）
   - data/
   - logs/

---

## 主要な環境変数（代表）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注は MockBroker、DB は data/paper_trading.db
  - live: 本番
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- OPENAI_API_KEY（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）
  - 1 未満や不正値はデフォルトにフォールバックされます
- PAPER_FILL_MODE（paper_trading の fill モード: instant | partial | never | reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（1 にすると ExecutionEngine 起動時に既存の kill.flag を自動でクリア）

サンプル最小 .env（例）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_pwd_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

注意: .env は絶対にリポジトリにコミットしないでください。

---

## 使い方（実行例）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 実行中に data/stop_requested.flag を作成すると安全に停止します
  - PID ファイル: data/execution.pid（設定で変更可）

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で設定:
    - export MONITOR_POLL_INTERVAL=30
  - 監視スクリプトは monitoring DB（SQLite）にシステム状態・ログを記録します
  - 監視は stop_requested.flag を監視し、存在すれば停止します

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告を FAIL 扱い（exit code 1）

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可）

- AI（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY、または各関数の引数で指定）
  - プログラムから呼ぶ例:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, date(2026,4,1))
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, date(2026,4,1))

---

## 停止・Kill フラグの扱い

- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring, run_execution はこのファイルを確認して停止します（外部からの graceful stop 用）
- kill.flag（デフォルト: data/kill.flag、Settings.kill_flag_path で変更可能）
  - KillSwitch が条件を満たすとこのファイルを書き込み、ExecutionEngine に停止シグナルを送る用途で使用します
  - kill.flag は起動時に自動クリア（KILL_FLAG_CLEAR_ON_START=1 の場合のみ）

---

## ログ & DB

- ログ:
  - デフォルト出力先: logs/<app_name>.log（app_name は "execution" / "monitoring" 等）
  - 日次ローテーション（30 日分保持）
  - コンソール出力は stdout に統一
- DB:
  - DuckDB: 分析用データ（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・トレード履歴（デフォルト data/monitoring.db）
  - Paper Trading 用 SQLite は別ファイルに分離（data/paper_trading.db）

---

## 主要モジュール概観

- kabusys.config — 環境変数 / .env の読み取り、Settings オブジェクト
- kabusys.config_setup — .env 対話式ウィザード
- kabusys.validate_config — 起動前の設定検証 CLI
- kabusys.run_execution — ExecutionEngine 起動スクリプト
- kabusys.run_monitoring — SystemMonitor ポーリング起動スクリプト
- kabusys.monitoring — monitoring_db, system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, alert_manager 等
- kabusys.execution — ブローカーファクトリ、エンジン、オーダー関連（発注・再調整・リスク管理）
- kabusys.portfolio — portfolio_builder, position_sizing, risk_adjustment（ポートフォリオ構築ロジック）
- kabusys.research — factor_research, feature_exploration（DuckDB 接続を用いたファクター計算）
- kabusys.ai — news_nlp（ニュース NLP）、regime_detector（レジーム判定）
- kabusys.utils — logging_setup, process_priority（ログ設定・プロセス優先度）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下のおおまかな構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照元コードベースに依存)
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
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                  # 実行時に生成される想定のディレクトリ
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/                  # ログ出力先（デフォルト）

---

## 運用上の注意・ベストプラクティス

- 本番（KABUSYS_ENV=live）では LINE 通知や kill flag 等の設定を十分に確認してください（validate_config が注意喚起します）。
- paper_trading では発注ロジックを実際のブローカーから分離しているため、安全な検証が可能です。DB も別ファイルに分離されます。
- AI 機能を使う場合は OPENAI_API_KEY を適切に管理してください。API 呼び出しはレート制限やネットワークエラーに対してリトライ処理を備えていますが、コスト監視を行ってください。
- ログディレクトリや data ディレクトリの権限やディスク容量に注意してください。monitoring はディスク使用率等も監視します。

---

## トラブルシューティング

- .env を読み込まない場合
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を確認
  - プロジェクトルートが .git または pyproject.toml を含んでいるか
- 起動時に DB/ログディレクトリが作れない場合
  - ログはコンソールのみで継続します。パーミッションやディスク容量を確認してください
- OpenAI 関連の JSON パースエラー等
  - レスポンスのバリデーションは保守的です。モデルやレスポンス形式を変更する場合はパース部分の調整が必要です

---

README は必要に応じて更新してください。より詳しい実装・設計情報（PortfolioConstruction.md、StrategyModel.md 等）がプロジェクト内にある場合はそちらを参照してください。
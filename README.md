# KabuSys

日本株自動売買システムのライブラリ / 実行スクリプト群。  
このリポジトリはトレード実行エンジン、監視・アラート、リサーチ（ファクター計算）、ポートフォリオ構築、AI によるニュース評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買システム向けユーティリティ群です。主要な役割は次の通りです。

- ExecutionEngine（発注ロジック、リスク管理、注文管理）
- Monitoring（システム状態・注文状況・リスク監視、Kill Switch）
- Portfolio（銘柄選定・重み計算・ポジションサイズ決定）
- Research（ファクター計算、前方リターン、IC 計算など）
- AI（ニュースのセンチメント評価や市場レジーム判定。OpenAI を利用）
- 各種 CLI ツール（.env ウィザード、設定検証、Paper Trading レポート生成等）

設計方針の一部:
- 本番/ペーパートレードは DB を分離（paper_trading モード時は data/paper_trading.db を使用）
- 設定は .env ファイル（または環境変数）で管理
- ロギングは統一的に設定（logs/<app>.log、日次ローテート）
- OpenAI を使う処理は API キー必須。API 呼び出しはリトライ、フェイルセーフ設計

---

## 主な機能一覧

- 環境設定ウィザード（.env の作成 / 更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml チェック）: python -m kabusys.validate_config
- Execution 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- Portfolio 構築ユーティリティ:
  - 銘柄選定（select_candidates）
  - 等分配 / スコア重み配分（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- Research（DuckDB を利用したファクター計算・IC / 統計）
- AI:
  - news_nlp.score_news: ニュース記事を OpenAI でスコアリングして ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF MA とマクロ記事でレジーム判定し market_regime に書き込み
- ユーティリティ:
  - ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度設定・CPU affinity（kabusys.utils.process_priority）
  - MonitoringDB（SQLite）ヘルパー（監視ログ、trade_logs、risk_logs、dashboard）

---

## セットアップ手順（開発 / 実行環境）

以下は一般的なセットアップ手順です。実行環境や OS により一部手順は変わる場合があります。

1. Python 環境
   - 推奨: Python 3.10+（コードは typing の新しい構文を使用）
   - 仮想環境の作成（例）
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージをインストール
   - 代表的な必須ライブラリ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証用、オプション）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - 実際は requirements.txt / pyproject に依存関係をまとめている想定です（なければ上記を参考にインストールしてください）。

3. プロジェクトルートに移動
   - パッケージ内の設定自動読み込みはプロジェクトルート（.git または pyproject.toml がある階層）を基準に行われます。

4. .env を作成
   - 対話式ウィザードで生成できます:
     ```
     python -m kabusys.config_setup
     ```
   - ウィザード後は `python -m kabusys.validate_config` で設定を検証してください。

5. データディレクトリの確認
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db (KABUSYS_ENV=paper_trading 時)
   - 必要に応じて環境変数で上書き可能（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）。

6. OpenAI を使う場合
   - 環境変数 OPENAI_API_KEY を設定するか、score_news/score_regime 呼び出しで api_key を渡してください。

注意:
- process priority の設定や CPU affinity の変更は psutil で行います。権限により設定できない場合があります（警告でスキップされます）。
- ログディレクトリ（default: logs/）は書き込み権限が必要です。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用、デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO)
- OPENAI_API_KEY (AI 関連の API 呼び出しに必要)
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔[s]、デフォルト: 60)
- KILL_FLAG_CLEAR_ON_START (起動時の kill.flag 自動クリア: 0/1)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)

簡単な .env サンプル（config_setup によって生成される内容に準ずる）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...
```

---

## 使い方（主要コマンド）

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も失敗扱い
  ```

- Execution エンジン起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading DB に記録します。
  - 起動前に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中に stop flag を置く（data/stop_requested.flag を作成）とエンジンは停止します。

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（秒）。
  - 監視は本番 sqlite_path を常に使用（KABUSYS_ENV に依存しない）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます。

- Paper Trading 検証レポート出力
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB は data/paper_trading.db。--db で指定可能
  ```

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーの指定が必要（引数 or OPENAI_API_KEY 環境変数）

ログ:
- デフォルトで logs/<app_name>.log に日次ローテートで保存されます（例: logs/execution.log）。

停止・Kill Switch:
- Kill Switch は監視モジュールが条件（例: ドローダウン超過、ポジション超過等）を満たした時に data/kill.flag を書き込みます。ExecutionEngine はこの kill.flag を検知して安全に停止する設計です。
- stop_requested.flag（プロジェクト内 data/stop_requested.flag）は管理者が手動で作成して監視／実行スクリプトを停止させるために使われます（run_execution/run_monitoring がチェック）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下に含まれる主要ファイル・モジュールのツリー（コードベースの抜粋に基づく）です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数/.env の読み込み・Settings
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        # （抜粋では内容を省略）
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py        # （抜粋では内容を省略）
    - kill_switch.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - (その他: execution, data, strategy 等のサブパッケージが存在・参照されますが、本 README の抜粋には含まれていないファイルがあります)

---

## 開発者向けメモ / トラブルシュート

- DB スキーマ自動作成 / マイグレーション
  - monitoring_db.init_monitoring_db は監視テーブルを冪等に作成します。既存カラムがない場合は ALTER TABLE による簡易マイグレーションも行います。

- OpenAI 呼び出しでの堅牢性
  - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライします。その他のエラーはロギングしてスキップする方針です。

- process priority 設定
  - set_process_priority は Windows / POSIX（Linux/macOS）を吸収して優先度を設定しようとしますが、権限不足や未対応 OS の場合は警告を出してスキップします。

- ログディレクトリ作成に失敗した場合
  - logging_setup はディレクトリ作成に失敗するとファイル出力を無効化し、コンソール出力のみで継続します。

- Paper Trading
  - KABUSYS_ENV=paper_trading のときは paper_trading 専用の SQLite を使う、実トレード API 呼び出しは行わない（MockBroker を使う）。これにより本番 DB と完全分離されます。

---

## 参考コマンドまとめ

- .env を対話式で作成:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に含めるべき追加情報（必要に応じて追記してください）:
- 実際の requirements.txt / pyproject.toml（依存関係の固定）
- 実際の ExecutionEngine / Broker 実装のドキュメント（発注フロー、OrderRepository の契約）
- alert_manager の通知先設定（LINE など）と .env の設定例
- テストの実行方法（ユニットテスト、CI 設定）

ご希望があれば、上記の追加情報やチュートリアル（実際にローカルで Execution と Monitoring を立ち上げる手順やデバッグ方法）を追記します。
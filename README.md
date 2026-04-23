# KabuSys

日本株自動売買システム（ライブラリ＋起動スクリプト群）の README。  
この README はリポジトリ内のコード構成と運用向けの基本的な使い方・セットアップ手順をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコアロジック群を集めたパッケージです。  
主な機能は以下のカテゴリに分かれます。

- Execution: 発注エンジン（ExecutionEngine）と関連コンポーネント（OrderManager、RiskManager 等）
- Monitoring: システム稼働監視、リスク監視、アラート・Kill Switch
- Portfolio construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約
- Research: ファクター計算・特徴量解析・IC計算など
- AI 補助: ニュース NLP によるセンチメント評価、レジーム判定（OpenAI を利用）
- Tools: 検証レポート等のユーティリティスクリプト
- Utils: ロギング設定、プロセス優先度設定など運用ユーティリティ

アプリケーションはローカル実行用の `paper_trading` モードや、本番 `live` モードなど複数の環境で動作するよう設計されています。

---

## 機能一覧（抜粋）

- 起動スクリプト
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視ループ起動: python -m kabusys.run_monitoring
- 設定管理 / ツール
  - 対話式 .env 作成: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築
  - 候補選定: select_candidates
  - 重み算出: calc_equal_weights / calc_score_weights
  - ポジションサイズ計算: calc_position_sizes
  - セクター上限適用: apply_sector_cap
  - レジーム乗数: calc_regime_multiplier
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン算出 / IC 計算 / ファクター統計
- AI（OpenAI）
  - ニュースを用いたセンチメント算出（ai_scores テーブルへ書込み）
  - マクロニュース + ETF MA200 を使った市場レジーム判定
- Monitoring
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化（SQLite）
  - RiskMonitor によるドローダウン・ポジション上限監視
  - KillSwitch による停止フラグ生成（data/kill.flag）

---

## 必要条件（推奨）

- Python 3.10+
- pip でインストールするパッケージ例:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の内容検証を行う場合）
- SQLite（標準ライブラリに含まれます）
- ネットワーク接続（OpenAI / kabu API 使用時）

requirements.txt がある場合はそれを利用してください（本リポジトリにない場合は上のパッケージを個別にインストールしてください）。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動します。
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （requirements.txt があれば `pip install -r requirements.txt`、なければ例示パッケージを個別に）
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数の初期化（推奨: 対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - これによりプロジェクトルートの `.env` を作成／更新できます。
   - 重要な必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV（development / paper_trading / live）を設定します。

5. 設定検証（オプション）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

6. データディレクトリ（`data/`）やログディレクトリ（`logs/`）は起動時に自動作成されることが多いですが、必要に応じて手動で作成してください。

---

## 環境変数（代表的なものとデフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用
- KABU_API_PASSWORD: （必須）kabuステーション API 用
- KABU_API_BASE_URL: デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト: data/kabusys.duckdb
- SQLITE_PATH: デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 時）デフォルト: data/paper_trading.db
- LOG_LEVEL: デフォルト: INFO
- LOG_DIR: デフォルト: logs/
- PID_FILE_PATH: デフォルト: data/execution.pid
- KILL_FLAG_PATH: デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）デフォルト: 0
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）デフォルト: 60
- PAPER_FILL_MODE: paper_trading モックの約定挙動（instant/partial/never/reject）デフォルト: instant
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で使用

.env には機密情報（API トークン等）を含むため絶対に Git にコミットしないでください。

---

## 使い方（主要スクリプト）

- ExecutionEngine（発注エンジン）を起動
  ```
  python -m kabusys.run_execution
  ```
  動作:
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用 SQLite に記録（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在する場合は起動せずに終了。
  - 実行中に data/stop_requested.flag を書くことでエンジンに停止シグナルを送れます。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  動作:
  - Settings に基づき sqlite/duckdb に接続して SystemMonitor.check_once() を定期実行します。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒、デフォルト 60）。
  - 停止フラグ: data/stop_requested.flag を検知すると監視ループを終了します。

- .env 対話ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  引数:
  - --from / --to: レポート期間（YYYY-MM-DD）
  - --db: SQLite DB パス（省略時は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 機能（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  いずれも OpenAI API キー（引数または OPENAI_API_KEY 環境変数）が必要です。

---

## ログと永続化

- ログ: デフォルト `logs/` にアプリ名ごとの日次ローテーションログが作成されます（TimedRotatingFileHandler）。コンソールは stdout に出力されます。
- 永続ストレージ:
  - DuckDB: 分析用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・トレードログ（デフォルト data/monitoring.db）
  - Paper trading は `data/paper_trading.db` に分離（KABUSYS_ENV=paper_trading 時）

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の `src/kabusys` を基準に抜粋）

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py         — 対話式 .env 作成ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite テーブル定義と MonitoringDB クラス
    - monitoring_engine.py  — 監視エンジン（各 Monitor を束ねる）
    - system_monitor.py     — システム状態・データ鮮度監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 管理
    - trade_monitor.py      — （参照されるが抜粋省略）
    - alert_manager.py      — （警告・通知処理、抜粋省略）
  - execution/              — 発注関連コンポーネント（OrderManager 等、抜粋）
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
  - tools/
    - paper_verification_report.py

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では kill フラグ・通知設定（LINE 等）を必ず確認してください。validate_config は本番向けのガードチェックを行います。
- .env は機密情報を含むため絶対にバージョン管理に含めないでください。
- Paper trading モードは本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH を使用）するよう設計されていますが、環境変数の設定ミスにより上書きされないよう注意してください。
- OpenAI を利用する処理は API 呼び出しに伴うレートリミットや課金が発生します。API キー・コストに注意して実行してください。
- process_priority, cpu_affinity の設定は OS により権限が必要になる場合があります（警告はログに出ますが例外で停止しない設計です）。

---

## 開発者向けメモ

- 型注釈や Python 3.10 の構文（X | Y）を利用しているため Python 3.10 以上を推奨します。
- DuckDB 接続（duckdb.DuckDBPyConnection）を渡して分析関数を呼ぶことで、SQL と Python を組み合わせた高速なデータ処理が可能です。
- テスト時は外部 API 呼び出し（OpenAI 等）をモックする設計になっています（コード内にモック用注記あり）。
- monitoring_db.init_monitoring_db() は冪等操作を行い、既存スキーマに対する簡易マイグレーションを実行します。

---

この README はコードベースの主要点をまとめた導入ドキュメントです。さらに詳しい設計仕様（PortfolioConstruction.md、StrategyModel.md 等）がリポジトリに含まれている場合はそちらを参照してください。問題・質問があればソース内の docstring やログメッセージも参照すると実装意図が分かりやすいです。
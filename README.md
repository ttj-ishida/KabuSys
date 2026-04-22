# KabuSys

日本株向けの自動売買システム（ライブラリ／サービス群）の README。  
本ドキュメントはリポジトリ内の主要スクリプトとモジュールの概要、セットアップ、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、日本株の自動売買を支援するためのモジュール群（データ処理、リサーチ／ファクター計算、ポートフォリオ構築、ExecutionEngine、監視・アラート、AI を用いたニュース/NLP 処理等）を含むシステムです。  
設計上の方針として、以下を重視しています。

- 実行環境（development / paper_trading / live）による挙動切替
- Paper trading（ペーパートレード）では本番 DB と分離して安全に検証可能
- DuckDB を用いた分析用クエリ、SQLite を用いた監視・ログ永続化
- OpenAI（LLM）連携によるニュースセンチメント評価（任意）
- モジュールは純粋関数・副作用最小化を意識（テストしやすい設計）

---

## 機能一覧（主なモジュール）

- 実行系・起動スクリプト
  - run_execution.py — ExecutionEngine の起動（本番 / ペーパートレード対応）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（監視）
- 設定・検証
  - config_setup.py — .env を対話式に作成・更新するウィザード
  - validate_config.py — 環境変数や config/*.yaml を事前検証する CLI
  - config.py — Settings クラス（環境変数ラッパ）
- 監視関連
  - monitoring/monitoring_db.py — 監視ログ（SQLite）初期化・永続化層
  - monitoring/system_monitor.py — システムリソース／データ鮮度監視
  - monitoring/trade_monitor.py 等 — 発注・約定監視（滞留注文・約定異常検出）
  - monitoring/risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring/kill_switch.py — 条件により kill.flag を書いてエンジン停止
  - monitoring/monitoring_engine.py — 各 Monitor を統合して定期実行
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py — 候補選定・重み計算
  - portfolio/position_sizing.py — 発注株数計算・上限制御・単元丸め
  - portfolio/risk_adjustment.py — セクター上限・レジーム乗数
- 研究・ファクター
  - research/factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB）
  - research/feature_exploration.py — 将来リターン計算・IC 等
- AI（OpenAI）関連
  - ai/news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込み
  - ai/regime_detector.py — マクロセンチメント + ETF MA で市場レジーム判定
- ユーティリティ
  - utils/logging_setup.py — 統一ログ設定（stdout + 日次ローテーション）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成

---

## 必要要件（主な依存パッケージ）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証を有効にする場合）
- そのほか標準ライブラリ（sqlite3 等）

インストール例（仮）:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成・有効化します。
2. 必要なパッケージをインストールします（上記参照）。
3. 初期設定ファイル（.env）を作成します。対話式ウィザードを推奨：
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成し、重要なキー（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を対話で入力できます。

4. 設定検証を実行します：
   ```
   python -m kabusys.validate_config
   ```
   警告も含めて厳密にチェックしたい場合：
   ```
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じてデータディレクトリやログディレクトリの作成（通常はスクリプトが自動作成します）:
   - デフォルト DB / ファイルパス
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID/Flags: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/

---

## 環境変数（主なもの）

主に config.py / validate_config.py を参照してください。代表的なもの：

必須（少なくとも設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用・オプション
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先ディレクトリ
- OPENAI_API_KEY — OpenAI API キー（AI 機能）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)

詳細は config.py を参照してください。

---

## 使い方（実行コマンド）

すべてパッケージをパスに入れた状態で、モジュールとして実行します（プロジェクトルートで実行するのが推奨）。

- ExecutionEngine を起動（本番または PAPER_TRADING に従う）:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動中に data/stop_requested.flag が存在すると起動を中止／実行中は停止します。
  - プロセス優先度は自動で "high" に設定されます（set_process_priority）。

- 監視ループを起動（SystemMonitor）:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定（秒）。デフォルト 60 秒。
  - 監視は Settings に定義された sqlite_path（監視 DB）を利用します（環境に関わらず本番 sqlite_path を参照する点に注意）。

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- .env 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  --db オプションで SQLite パスを手動指定可能。

- AI 関連（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらは DuckDB 接続オブジェクトを受け取り、内部で OPENAI_API_KEY（または引数）を参照します。API キーが未設定だと例外になります。

---

## 実行時の運用注意

- Paper trading は本番 DB と分離するため、KABUSYS_ENV=paper_trading を使うことで安全に検証できます（paper_sqlite_path を確認）。
- kill.flag（Settings.kill_flag_path で指定）を書き込むことで ExecutionEngine に停止シグナルを送る仕組みがあります。KILL_FLAG_CLEAR_ON_START に注意してください（本番で自動クリアは危険）。
- run_monitoring/run_execution は内部で PID・flag ファイルを参照／作成します（data ディレクトリのパーミッション等に注意）。
- OpenAI を使う機能は API 利用量が発生するため、APIキー設定と利用ポリシーの確認が必要です。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリの作成に失敗するとコンソール出力のみになります。

---

## ディレクトリ構成（主要ファイル）

（project root の下に `src/kabusys` というパッケージがある想定）

- src/kabusys/
  - __init__.py
  - config.py — Settings クラス（環境変数ラッパ）
  - config_setup.py — .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・永続化 API
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — システム状態／データ鮮度監視
    - risk_monitor.py — ドローダウン／ポジション数監視
    - kill_switch.py — kill.flag 書き込みロジック
    - trade_monitor.py — 発注／約定の監視（ログ参照）※ファイル内に詳細実装あり
    - alert_manager.py — アラート送信（LINE 等）※実装に依存
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度設定
  - data/（実行時に作成されることが多い）
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード）
    - kabusys.duckdb（デフォルト）
    - execution.pid / kill.flag / stop_requested.flag

---

## 開発者向けメモ

- DuckDB 接続を受け取り SQL + Python の組合せでファクター計算・リサーチ処理を行う設計です（analysis 用の高速処理に最適化）。
- 監視用 DB スキーマは monitoring/monitoring_db.py の init_monitoring_db で冪等的に構築されます。既存 DB に対する簡易マイグレーション（列追加）も実装されています。
- ログ設定は utils/logging_setup.setup_logging を各起動スクリプトの最初で呼び出して統一してください。
- 外部 API 呼び出し（kabu API / J-Quants / OpenAI 等）は設定とエラーハンドリングに注意して実装されています。テスト時はモック化が可能な設計になっています（例: news_nlp._call_openai_api を patch）。

---

もし README に追加したい具体的な例（.env のサンプル、systemd unit ファイル例、Dockerfile、CI 手順など）があれば教えてください。それに合わせてセクションを追加します。
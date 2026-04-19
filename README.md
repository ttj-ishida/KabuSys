# KabuSys

日本株自動売買システムのリポジトリ（簡略版ドキュメント）。

この README ではプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。主な目的は次のとおりです。

- 発注エンジン（ExecutionEngine）による自動発注（本番 / ペーパートレード対応）
- 監視サブシステム（Monitoring）によるプロセス・リソース・データ鮮度・取引ログ監視、および Kill Switch の実装
- ポートフォリオ構築（選定・重み付け・位置サイズ決定・リスク調整）
- リサーチ（ファクター算出、特徴量探索、IC 計算など）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート生成など）

設計上の特徴：
- 本番用 DB（SQLite）とペーパートレード用 DB を分離
- DuckDB を分析向けに利用
- 環境変数 / .env による柔軟な設定
- OpenAI API（gpt-4o-mini など）を用いた NLP 機能（任意）

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して発注を行う（本番 / paper_trading 切り替え）
  - ブローカークライアントの抽象化（モックと実ブラウザの切替）
  - リスクマネージャ、OrderManager、Reconciler を通じた堅牢な発注制御

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor：注文滞留・約定異常などの検出（ログから）
  - RiskMonitor：ドローダウンやポジション上限のチェック、リスクイベント記録
  - KillSwitch：致命的なリスク発生時に data/kill.flag を作成して Execution を停止
  - MonitoringEngine：上記をまとめてポーリングし、AlertManager へ通知

- Portfolio（純粋関数群）
  - 候補選定、等金額／スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman rank）や統計サマリー

- AI
  - news_nlp: raw_news を集約して OpenAI API に投げ、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF（1321）MA とマクロニュースの LLM スコアを合成して market_regime を算出

- ツール
  - config_setup: .env を対話式に生成・更新するウィザード
  - validate_config: .env と config/*.yaml の整合性チェック CLI
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## セットアップ手順（開発・運用共通）

注意: 本リポジトリに requirements.txt は含まれていないため、下記は推奨パッケージ例です。適宜環境に合わせてインストールしてください。

1. Python 環境
   - Python 3.9+ を推奨

2. 必要パッケージ（例）
   - duckdb, psutil, openai, sqlite3（標準）, その他プロジェクト内で使用するライブラリ
   - 例:
     ```
     pip install duckdb psutil openai
     ```

3. リポジトリのルートへ移動し、.env を作成
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作る場合は `.env.example` を参考に `.env` を作成し、必須環境変数を設定してください。

4. 設定検証
   - 自動検証ツールで事前チェック:
     ```
     python -m kabusys.validate_config
     ```
   - 警告もエラー扱いにしたい場合:
     ```
     python -m kabusys.validate_config --strict
     ```

5. データディレクトリ
   - デフォルトで以下のファイル/ディレクトリを利用します（必要に応じて .env で変更可能）:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - ログディレクトリ: logs/
     - kill.flag / stop_requested.flag: data/kill.flag, data/stop_requested.flag
   - ログディレクトリは起動時に自動作成されますが、data/ フォルダを手動で作成しておくと運用で便利です:
     ```
     mkdir -p data logs
     ```

6. OpenAI / API キー
   - AI 機能を使う場合は環境変数 `OPENAI_API_KEY` を設定します。
   - ニュース NLP やレジーム判定では OpenAI API を利用します（失敗時はフェイルセーフが働く場合がありますが、正確な結果を得るには API キーが必要です）。

7. 必須の機密情報
   - J-Quants: `JQUANTS_REFRESH_TOKEN`
   - kabuステーション: `KABU_API_PASSWORD`
   これらは .env に設定しておきます（config_setup で入力可能）。

---

## 使い方（主要 CLI / 実行例）

- .env の準備（対話ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（本番 / ペーパートレードは KABUSYS_ENV で切替）
  ```
  # デフォルト: KABUSYS_ENV が .env に設定される
  python -m kabusys.run_execution
  ```
  - ペーパートレードにするには .env の KABUSYS_ENV を `paper_trading` にするか、環境変数を設定します。
  - ExecutionEngine は `data/execution.pid` を PID ファイルとして扱います。
  - `data/stop_requested.flag` が存在すると起動しない / ループ中に停止します。
  - `KillSwitch` により `data/kill.flag` が書き込まれると ExecutionEngine に停止シグナルが送られます。

- Monitoring 起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）。
  - Monitoring は本番用の sqlite_path を常に使用します（環境に関わらず）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを直接指定する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- AI モジュール呼び出し（プログラムから）
  - news_nlp の例:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    score_news(conn, target_date=date(2026,4,15), api_key="YOUR_OPENAI_KEY")
    ```

- 研究モジュール（例: モメンタム）
  ```python
  from kabusys.research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  from datetime import date
  records = calc_momentum(conn, target_date=date.today())
  ```

---

## 主要な環境変数（抜粋）

- 必須（最低限設定すること）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行 / DB 関連
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch のフラグ（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒、デフォルト: 60）

- ログ
  - LOG_LEVEL — ログ出力レベル（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR — ログディレクトリ（デフォルト: logs/）

- AI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能の利用に必須）

- Paper Trading 挙動
  - PAPER_FILL_MODE — MockBroker のフィルモード（instant / partial / never / reject、デフォルト: instant）

---

## プロセス制御 / フラグファイル

- data/stop_requested.flag
  - run_execution / run_monitoring のループ停止用フラグ。存在するとループを終了します（運用者が停止を要求する際に作成）。

- data/kill.flag
  - KillSwitch が作成するファイル。存在すると ExecutionEngine に停止命令を送る（致命的リスク発生時など）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なので注意。

---

## ディレクトリ構成（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照実装想定)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリには上記以外の補助モジュールや設定テンプレートが含まれます）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）で実行する前に、必ず `python -m kabusys.validate_config` で設定を検証してください。
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- AI モジュールは外部 API を利用するため、API 利用料が発生します。利用前にコストとリクエスト制限を確認してください。
- process_priority や cpu_affinity の変更は権限に依存するため、設定に失敗すると警告が出ますが処理は続行されます。
- Monitoring は監視ログ（SQLite）に書き込みます。バックアップ・ローテーション方針は運用に合わせて検討してください。

---

以上が本プロジェクトの README 相当の概要です。必要であれば、セットアップ用の requirements.txt やより詳細な運用手順（systemd ユニットファイルの例、Docker 化手順、CI の設定など）も作成しますのでご依頼ください。
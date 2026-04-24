# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリ（モジュール群）の README です。本リポジトリは以下の主要機能を提供します。

- 注文実行エンジン（ExecutionEngine）
- 監視ループ（Monitoring）
- ポートフォリオ構築（選定・配分・株数決定）
- 研究用ファクター計算 / 特徴量解析
- ニュースセンチメント（OpenAI を用いた NLP）
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザード / 設定検証ツール

以下は導入・利用方法、主要コンポーネントの説明、ディレクトリ構成です。

## 主要機能（ざっくり）

- Execution
  - 本番 / ペーパートレード両対応（KABUSYS_ENV により切替）
  - ブローカークライアントの抽象化（Mock を使った paper_trading）
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカーなど）
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - Execution プロセスの生存監視、データ鮮度チェック
  - 取引ログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch（閾値超過時に stop フラグを書き出し発注停止）
- Portfolio
  - 候補選定 / 等配分・スコア加重配分 / リスク調整（セクター上限、レジーム乗数）
  - 株数計算（lot 単位丸め・aggregate cap によるスケーリング）
- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI（OpenAI）
  - ニュース記事を LLM でセンチメント化し ai_scores テーブルに保存
  - マクロセンチメント + ETF MA による市場レジーム判定（bull / neutral / bear）
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools.paper_verification_report）

---

## 必要条件（目安）

- Python 3.10+
- SQLite（Python 標準ライブラリで同梱）
- DuckDB パッケージ（duckdb）
- psutil（プロセス／リソース監視）
- OpenAI SDK（AI 機能を使う場合）
- （オプション）PyYAML（設定ファイル検証機能で利用）

依存パッケージは requirements.txt や pyproject.toml を参照してインストールしてください。

例:
```bash
pip install -r requirements.txt
# または
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンする
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt
   ```

4. 環境変数の初期設定
   - 対話式ウィザードで .env を生成できます:
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザード実行後は `.env` に必要な変数が保存されます（絶対に Git にコミットしないでください）。

5. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

6. data/ や logs/ ディレクトリが必要に応じて自動作成されますが、権限等に問題がある場合は手動で作成してください。

---

## 重要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

主要（デフォルト値あり）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の模擬約定モード: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）を有効にする場合必須
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）

操作用フラグファイル / PID:
- data/stop_requested.flag — run_monitoring / run_execution の外部停止フラグ（存在すると起動ループを終了）
- data/kill.flag — Kill Switch による発注停止フラグ
- data/execution.pid — ExecutionEngine の PID 保存先（デフォルト）

---

## 主要スクリプト（使い方）

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Execution Engine 起動
  - 本番・開発・ペーパートレードは KABUSYS_ENV によって振る舞いが変わります。
  - paper_trading 環境では MockBroker を使い、data/paper_trading.db にログを記録します。
  ```bash
  # 例: ペーパートレード環境で起動
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  # 例: 本番環境で起動
  KABUSYS_ENV=live python -m kabusys.run_execution
  ```

- Monitoring 起動
  - MONITOR_POLL_INTERVAL によりポーリング間隔（秒）を指定可能（デフォルト 60）。
  - Monitoring は監視用の sqlite_path（通常 data/monitoring.db）を使用します（KABUSYS_ENV に依存しない）。
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート生成
  ```bash
  # 全期間（DB 内の全データ）
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB を直接指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す例）
  - news_nlp.score_news / ai.regime_detector.score_regime は OpenAI API キーが必要です（OPENAI_API_KEY）。
  - 直接の CLI エントリポイントは用意されていませんが、モジュール API を呼んで利用します。

---

## 運用メモ / 制御フラグ

- 停止（即時）
  - プロセスを止めるには `data/stop_requested.flag` を作成します。run_monitoring / run_execution はこのファイルを検出して安全に停止します。
- Kill Switch
  - 監視の結果、ドローダウンやポジション上限を超えた場合、KillSwitch が `data/kill.flag` を書き込みます。ExecutionEngine は起動時にこのフラグがあると起動を抑止できます（設定により起動時に自動クリア可）。
- ログファイル
  - デフォルトで logs/ ディレクトリに日次ローテーションでログが保存されます（kabusys.utils.logging_setup によりセットアップ）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数/.env の読み込みと Settings クラス
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (ランタイムで利用するファイルや DB を配置)
  - logs/ (ログ出力先)

（上記は主要モジュールの一覧であり、実際のファイル構成はリポジトリの最新版を参照してください。）

---

## 開発者向けメモ

- Settings クラス（config.py）はアプリケーションの設定アクセスポイントです。プロジェクトルートの .env / .env.local が自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- Monitoring の DB 初期化（init_monitoring_db）は冪等であり、既存スキーマへのマイグレーション処理も一部実装されています。
- AI 機能（news_nlp / regime_detector）は OpenAI API に依存します。API 呼び出し周りはリトライ・バックオフやレスポンス検証を備え、失敗時はフォールバック動作をとる設計です。
- DuckDB は分析用途（prices_daily / raw_financials 等）の高速集計に使用します。適切にデータを投入してから research モジュールを利用してください。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。各起動スクリプトは最初にこの関数を呼びます。

---

## トラブルシュート（よくある注意点）

- .env をリポジトリにコミットしないでください（機密情報を含む）。
- OpenAI を使う場合は API キーのレート制限・料金管理に注意してください。
- Monitoring は MONITOR_POLL_INTERVAL によってループ間隔を調整できます。短くすると負荷が上がります。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（誤って kill.flag をクリアする設定は危険）。
- DuckDB / SQLite のファイルパスは Settings で指定できます。デフォルトは data/ 以下です。適切なバックアップ・アクセス権を確保してください。

---

もし README に追加したい内容（例: 実際の起動例、CI 設定、データ投入手順、API ドキュメント等）があれば教えてください。必要に応じて追記します。
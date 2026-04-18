# KabuSys

日本株自動売買システムの軽量モジュール群（ライブラリ＋CLI）。  
このリポジトリはトレーディングロジック（ポートフォリオ構築・ポジションサイジング等）、モニタリング、ペーパートレード検証、AI ベースのニュース解析・レジーム判定ユーティリティなどを含みます。

---

## プロジェクト概要

- 目的: 日本株自動売買システムのコア機能を分離したライブラリと実行用スクリプト群を提供する。
- 特徴:
  - ポートフォリオ構築（候補選定・重み計算）
  - ポジションサイジングとリスク制御（セクターキャップ、ドローダウン監視）
  - モニタリングエンジン（システム状態、注文滞留、リスクイベントの監視）
  - Execution エンジン起動スクリプト（paper_trading 環境では MockBroker を使用）
  - AI モジュール（ニュースの NLP スコアリング、レジーム判定） — OpenAI API を利用
  - DuckDB / SQLite を用いたデータ保存・分析
  - 設定ウィザード / 設定検証用 CLI

---

## 主な機能一覧

- ポートフォリオ
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - apply_sector_cap / calc_regime_multiplier

- リサーチ
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary

- AI（OpenAI を利用）
  - news_nlp.score_news: ニュース記事を LLM でセンチメント評価して ai_scores に格納
  - regime_detector.score_regime: MA200 とマクロニュースを組み合わせて市場レジーム判定

- モニタリング
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch / AlertManager 経由での停止・通知連携
  - MonitoringEngine: 複数モニタの統合ポーリング

- 実行用スクリプト
  - run_execution.py: ExecutionEngine を開始（paper_trading 環境では専用 DB に分離）
  - run_monitoring.py: SystemMonitor の単独ポーリングループ

- ユーティリティ
  - config_setup.py: .env を対話的に生成 / 更新するウィザード
  - validate_config.py: 起動前に環境変数や config/*.yaml を検証
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成

- DB 層
  - monitoring_db.py: SQLite 監視 DB のスキーマ作成 / マイグレーション / CRUD ユーティリティ

---

## セットアップ手順

前提: Python 3.10+ を想定（typing 表記に依存）。以下は例です。

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb psutil openai
   ```
   - 追加（任意）: PyYAML（config ファイル検証を有効化）
     ```
     pip install pyyaml
     ```

3. data ディレクトリ作成（スクリプトが自動作成することもありますが、手動作成して権限や初期ファイルを用意する場合）
   ```
   mkdir -p data
   ```

4. 環境変数の準備
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードはリポジトリ直下の `.env` を作成／更新します。

   - 手動で `.env` を作る場合（最小例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

注意:
- OpenAI を使う機能を利用する場合、環境変数 `OPENAI_API_KEY` を設定してください。
- `KABUSYS_ENV` は次のいずれか: `development`, `paper_trading`, `live`（大文字小文字は区別されません）。`paper_trading` では専用の paper DB を使用します。

---

## 主要な環境変数（デフォルト・説明）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能で必要)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート送信用、任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV (default: development) — 有効値: development / paper_trading / live
- LOG_LEVEL (default: INFO)
- KILL_FLAG_CLEAR_ON_START (0/1) — 本番での自動クリアは非推奨（デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading 時の MockBroker の fill モード（instant/partial/never/reject）

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動
  - 開発 / 本番モードは KABUSYS_ENV で切替（paper_trading は専用 DB を使用）
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 起動前に `data/stop_requested.flag` が存在すると起動しません（停止フラグ）。
  - 実行中は `data/execution.pid` に PID を書き込みます。pid の stale 検出時は自動削除されます。

- Monitoring 起動（SystemMonitor 単体）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト 60）。
  - 監視は常に本番用の sqlite_path を参照（環境に関係なく同じ monitoring DB を使用）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプション、または環境変数 `PAPER_TRADING_SQLITE_PATH` を使用。

- AI 機能（モジュールを直接呼び出す）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、API キーを使って呼び出します。
  - 例（スクリプト化して呼ぶ想定）:
    - Python コード内で OpenAI API キーを環境変数 `OPENAI_API_KEY` にセットして呼び出す。

---

## 停止・Kill Switch の扱い

- KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります。
- run_execution / run_monitoring はプロセス優先度を上げて開始します（psutil を利用）。権限不足等で設定できない場合は警告が出ます。
- `data/stop_requested.flag` があると run_execution は起動を抑止し、run_monitoring のループも終了します。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では危険な設定のためデフォルトは 0）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動読み込みロジック、Settings クラス
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py  (一部省略)
  - execution/              — （発注エンジン、OrderRepository 等; スクリプトで利用）
  - utils/
    - process_priority.py
  - data/                   — 実行時生成されるファイル（デフォルトパス）
    - monitoring.db (SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kill.flag / stop_requested.flag / execution.pid

※ 上はソース上で参照されている主要モジュールの一覧です。詳細はソースファイル内の docstring を参照してください。

---

## 注意事項・運用上のヒント

- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します。自動クリアは危険です。
- OpenAI API を用いる機能は API 料金が発生します。ロールアウト前に該当機能を無効化するか、API キーを設定しない運用を検討してください。
- DuckDB / SQLite のファイルは適切にバックアップしてください（履歴・レポートに依存します）。
- run_execution は paper_trading 環境時に発注処理を実 URL に送らず MockBroker を使用します（本番 DB と分離）。
- `validate_config.py` を CI / デプロイ前に実行して、重大な設定漏れを早期に検出してください。

---

この README はコードベースの主要な機能と起動方法をまとめたものです。より詳細な API 仕様や内部アルゴリズム（PortfolioConstruction.md、StrategyModel.md 等の設計文書）に関してはプロジェクト内の追加ドキュメントを参照してください。必要であれば README に追記しますので、特に詳述してほしい項目を教えてください。
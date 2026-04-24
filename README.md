# KabuSys

日本株向けの自動売買 / リサーチ基盤の一部を抜粋した実装です。  
この README はリポジトリ内の主要モジュール（実行エンジン・監視・ポートフォリオ構築・リサーチ・AI ニュース処理等）を対象に、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けのコンポーネント群です。主な役割は次のとおりです。

- ExecutionEngine：発注ロジック、注文管理、リスク管理、reconciler などを統合して発注セッションを実行する（本番 / ペーパートレード対応）。
- Monitoring：システム状態・発注ログ・リスク（ドローダウン・ポジション上限）を継続監視し、必要に応じてアラート発行や Kill Switch（停止フラグ）を書き込む。
- Portfolio：銘柄選定、重み付け、ポジションサイズ計算、セクター制限、レジーム補正といったポートフォリオ構築ロジック（純粋関数群）。
- Research：DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量評価ユーティリティ。
- AI：ニュース記事を LLM（OpenAI）でセンチメント評価し ai_scores へ書き込む機能や市場レジーム判定。
- ユーティリティ：設定（.env）ロード、対話式設定ウィザード、設定検証、ロギングセットアップ、プロセス優先度設定等。

設計方針として、データベース接続や外部 API 呼び出しを呼び出し元から注入したり、フェイルセーフ（API失敗時に継続）などを採用しています。

---

## 主な機能一覧

- 実行関連
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード分離（ペーパートレードは独立 DB に書き込み）
  - ブローカークライアントをファクトリで生成（MockBroker を含む）

- 監視関連
  - SystemMonitor：CPU / メモリ / ディスク / プロセス死活 / データ鮮度監視
  - TradeMonitor：滞留注文・約定異常検出（コードベースに定義あり）
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新、risk_logs 登録
  - MonitoringEngine：各モニタを束ねてポーリング、Kill Switch 書き込み、AlertManager へ通知

- ポートフォリオ構築
  - 候補選定・スコア順ソート（select_candidates）
  - 等金額・スコア重み割当（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（risk_based / equal / score）・単元株丸め（calc_position_sizes）
  - セクターキャップ適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - ニュース記事を LLM でセンチメント化して ai_scores に書き込み（news_nlp.score_news）
  - マクロニュースと ETF 200日MA 乖離を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しは再試行・バックオフ等の対処あり

- 開発 / 運用支援
  - 環境設定ウィザード（config_setup.py）で .env を対話的に作成
  - 設定検証 CLI（validate_config.py）
  - Paper Trading レポート生成ツール（tools/paper_verification_report.py）
  - 統一ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度 & CPU affinity ヘルパー（utils/process_priority.py）

---

## セットアップ手順

1. Python（3.9+ 推奨）を用意します。

2. 必要な Python パッケージをインストールします（例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML の検証を行う場合、任意）
   - 他、標準ライブラリのみで動く部分も多いです。

   例（pip）:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. プロジェクトルートに .env を用意します（推奨手順は次）。
   - 対話式ウィザードで作成：
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは J-Quants / kabuステーション / DB パス / ログレベル等の設定を促します。
   - 既存の .env があればそれを置くことも可能ですが、`.env` を絶対に Git にコミットしないでください。

4. 設定検証（必須項目の確認）:
   ```
   python -m kabusys.validate_config
   ```
   本番で警告も許容しない場合は `--strict` を付けて実行してください。

5. データディレクトリ確認：
   - デフォルトで使用されるパス（.env で上書き可能）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - ログディレクトリ：logs/（デフォルト。権限等を確認）

6. OpenAI を使用する機能を使う場合は環境変数 `OPENAI_API_KEY` を設定してください。

注意:
- .env の自動読み込みはデフォルトで有効です。テストや特殊用途で自動ロードを止める場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env.example があればそれを参考に必須値を設定してください（本コードベースに .env.example のファイルは含まれていない可能性があります）。

---

## 使い方（起動 / コマンド例）

- 設定ウィザード（.env の作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（フォアグラウンド）
  ```
  python -m kabusys.run_execution
  ```
  挙動：
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_sqlite_path に書き込む（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に data/stop_requested.flag が作成されると安全に停止します。
  - pid ファイル（デフォルト data/execution.pid）を利用。

- Monitoring を起動（監視ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  オプション的設定：
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番用 monitoring.db）を使用します（監視は本番 DB を参照する設計）。
  - 起動中にプロジェクトルート/data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを明示
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコア生成 / レジーム判定（ライブラリ関数）
  - ニューススコア生成:
    ```python
    from kabusys.ai.news_nlp import score_news
    # conn: DuckDB connection (duckdb.connect(...))
    score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

- ログ出力
  - logs/<app_name>.log に日次ローテーションで出力（30 日保持）。各起動スクリプトは setup_logging(app_name="execution" / "monitoring") を呼び出します。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: monitoring DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの fill 挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1） — 本番では 0 推奨

注意: 必須環境変数が未設定だと各所で ValueError が発生します。`python -m kabusys.validate_config` で確認してください。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内 `src/kabusys` の主要ファイル/ディレクトリ構成（抜粋）です。

コードブロック形式で示します:

```
src/kabusys/
├─ __init__.py
├─ config.py                 # Settings / .env 自動ロードロジック
├─ config_setup.py           # .env 対話ウィザード
├─ validate_config.py        # 設定検証 CLI
├─ run_execution.py          # ExecutionEngine 起動スクリプト
├─ run_monitoring.py         # Monitoring 起動スクリプト
├─ tools/
│  ├─ __init__.py
│  └─ paper_verification_report.py
├─ utils/
│  ├─ __init__.py
│  ├─ logging_setup.py       # ログ設定ユーティリティ
│  └─ process_priority.py    # プロセス優先度 / CPU affinity
├─ monitoring/
│  ├─ monitoring_db.py       # SQLite スキーマ・永続化層
│  ├─ monitoring_engine.py
│  ├─ system_monitor.py
│  ├─ trade_monitor.py
│  ├─ risk_monitor.py
│  ├─ kill_switch.py
│  └─ alert_manager.py       # （実装がある場合）
├─ execution/
│  ├─ execution_engine.py
│  ├─ broker_factory.py
│  ├─ order_manager.py
│  ├─ order_repository.py
│  ├─ reconciler.py
│  └─ risk_manager.py
├─ portfolio/
│  ├─ __init__.py
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
└─ data/                     # 実行時に使用するファイル（DB・フラグ・pid 等）
   ├─ monitoring.db          # デフォルト sqlite monitoring DB
   ├─ paper_trading.db       # ペーパートレード用 DB（存在しない場合は作成）
   ├─ execution.pid
   ├─ kill.flag
   └─ stop_requested.flag
```

（上記は抜粋です。実際のリポジトリに合わせてファイルが存在することを確認してください。）

---

## 監視 DB（monitoring_db）について（簡易説明）

`monitoring_db.init_monitoring_db(conn)` は必要なテーブルとインデックスを冪等に作成します。主なテーブル：

- system_status: CPU/メモリ/ディスク/プロセス状態の時系列ログ
- trade_logs: 発注・約定などのイベントログ（latency_ms カラムあり）
- positions: 保有ポジション（code を主キー）
- risk_logs: リスクイベント（ドローダウン・ポジション上限等）
- dashboard: 集計（id=1 の単一行で保持） — portfolio_value / cash / drawdown_pct / open_order_count / position_count / peak_value など

Monitoring / RiskMonitor はこれらを読み書きし、Kill Switch の評価やアラート発行を行います。

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください。`validate_config.py` は live 時に追加チェックや警告を出します。
- .env は秘密情報（API キー・パスワード）を含むため、絶対にリポジトリへコミットしないでください。
- Monitoring は監視用 DB（SQLITE_PATH）を参照します。監視が本番 DB を参照する設計になっている点に注意してください。
- Kill Switch（data/kill.flag）は ExecutionEngine を停止させる安全機構です。`KILL_FLAG_CLEAR_ON_START=1` を本番で設定することは危険です（自動クリアされるため）。
- OpenAI API を使う処理（news_nlp / regime_detector）は API 失敗時にフォールバックやリトライを行いますが、API キーやコスト管理には注意してください。

---

以上がこのコードベースの README 的なまとめです。必要であれば、具体的な起動スクリプトのオプション、実行例、よくあるトラブルシュート（例: DuckDB ファイルの権限、psutil による優先度設定の権限エラーの対処）などを追記できます。どの情報をより詳しく書きたいか教えてください。
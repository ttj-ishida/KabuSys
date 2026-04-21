# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0 — 2026-04-21

## [0.1.0] - 2026-04-21
初回リリース。以下の主要機能・ユーティリティ・CLI を含む日本株自動売買システムの基盤を実装しました。

### 追加
- 基本パッケージ構成
  - パッケージ情報: `src/kabusys/__init__.py` にバージョン情報（0.1.0）と公開サブパッケージ定義を追加。
- 起動スクリプト
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - 停止フラグ検知（`data/stop_requested.flag`）で安全にループを終了。
    - 監視用 DB は環境に依らず本番用 `sqlite_path` を使用する仕様を採用。
  - `run_execution.py`
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、発注データは専用の Paper Trading DB（デフォルト: `data/paper_trading.db`）に記録して本番 DB と分離。
    - スレッドで ExecutionEngine を実行し、停止フラグ（`data/stop_requested.flag`）で安全に停止。
    - 実行 PID を `data/execution.pid` に出力する仕組みをサポート。
- 設定管理・検証・ウィザード
  - `config.py`
    - 環境変数の取得をラップする `Settings` クラスを実装。
    - `.env` 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。OS 環境変数は保護して上書きしない。
    - 多数の環境変数をサポート（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `KABUSYS_ENV`, `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`, `PAPER_FILL_MODE` 等）。
    - `PAPER_FILL_MODE` の妥当性チェック（"instant" / "partial" / "never" / "reject"）。
  - `validate_config.py`
    - `.env` と `config/*.yaml` の簡易検証 CLI 実装。
    - 必須環境変数チェック、`KABUSYS_ENV`/`LOG_LEVEL` の妥当性チェック、DB パスや config YAML の存在/パース（PyYAML が未インストールの場合はスキップして警告）などを行う。
    - `--strict` オプションで警告を FAIL 扱いにできる。
  - `config_setup.py`
    - 対話式ウィザードで `.env` を初期作成・更新する CLI を実装。
    - 推奨値・説明・シークレットマスク表示・デフォルト選択をサポートし、最終的に `.env` を出力。
- ロギング / プロセス管理ユーティリティ
  - `utils/logging_setup.py`
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト保存日数 30）を設定するユーティリティ `setup_logging()` を提供。
    - ログディレクトリ自動作成（失敗時はコンソール出力のみで継続）。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
  - `utils/process_priority.py`
    - Windows と POSIX(Linux/macOS/FreeBSD) を吸収したプロセス優先度設定 `set_process_priority()` を提供（"high" / "normal" / "low"）。
    - CPU affinity を設定する `set_cpu_affinity()` を提供（権限不足や未対応 OS の場合は警告ログを出してスキップ）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - `portfolio/portfolio_builder.py`
    - シグナル選定（`select_candidates`）、等配分（`calc_equal_weights`）、スコア加重配分（`calc_score_weights`）。
    - 同点処理やスコアが全て 0 の場合のフォールバック挙動を実装。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限を適用する `apply_sector_cap`（既存ポジションと当日売却予定の除外対応、"unknown" セクターは無視）。
    - 市場レジームに基づく投下資金乗数 `calc_regime_multiplier`（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームはフォールバック）。
  - `portfolio/position_sizing.py`
    - 各銘柄の発注株数計算 `calc_position_sizes`（allocation_method: "risk_based"/"equal"/"score"）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、コストバッファ考慮、スケールダウンと残差処理（lot-size 単位での追加配分）を実装。
- ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用 SQLite データを解析して検証レポートを出力する CLI。
    - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）。
    - デフォルト閾値を定義（例: 稼働率 >= 99%、Fill rate >= 90%、P95 <= 200 ms など）と PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）及び DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
- データベース初期化/接続
  - `monitoring/monitoring_db.py` 経由で監視テーブルの初期化を行う呼び出し（`init_monitoring_db`）を各起動スクリプトで確実に実行。
  - DuckDB と SQLite の双方を利用する設計（DuckDB は分析、SQLite は監視 / 履歴）。
- 監視 / 実行コンポーネント（構成）
  - 実行コンポーネント群（`execution` パッケージ）を組み立てるロジック（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の呼び出し・初期化が `run_execution.py` にて実装され、デフォルトの RiskConfig パラメータ（max_position_pct=0.20 等）を設定。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の制限 / 注意点
- `config.py` の自動 `.env` ロードはプロジェクトルート検出に依存する（`.git` または `pyproject.toml` が存在しない状況では自動読み込みをスキップ）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `monitoring` は環境に関係なく本番の `sqlite_path` を参照する設計であるため、開発環境での運用時は DB パスに注意してください（Paper Trading の発注履歴は `PAPER_TRADING_SQLITE_PATH` で分離可能）。
- `utils/process_priority` / `set_cpu_affinity` は環境によっては権限不足で動作しない場合があり、その場合はログで警告を出してスキップします。
- 一部モジュール（例: `research/factor_research.py` 内のモメンタム計算実装）はファイル末尾が不完全に見える箇所があり、今後の追加実装・整備が必要です。
- `tools/paper_verification_report.py` は SQLite のスキーマ（`system_status`, `trade_logs`, `risk_logs` 等）に依存します。スキーマが存在しない/異なる場合には一部指標が N/A になったり例外が処理されます。

### セキュリティ
- `.env` は絶対にリポジトリにコミットしない旨をドキュメントと `config_setup.py` のヘッダーに明記。

---

今後の予定（例）
- factor 計算モジュール（research）を完成させ、DuckDB ベースのファクター生成パイプラインを追加。
- Execution / Broker クライアントのテスト用スタブ改善と paper_trading のエミュレーション強化。
- 監視アラートの LINE 通知統合（`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID` を利用）。
- CI / デプロイ・リリース手順の整備と CHANGELOG の自動更新に向けたワークフロー導入。
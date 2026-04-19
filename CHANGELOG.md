# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のリリース履歴は以下の通りです。

## [0.1.0] - 2026-04-19

最初の公開リリース。KabuSys のコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築ロジック、および検証／レポート用ツール群を追加しました。

### 追加
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パッケージ公開用モジュールエクスポート (`__all__`) を追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル `data/stop_requested.flag` を検知してループを終了。
    - 監視用 SQLite は環境に依らず本番（`Settings.sqlite_path`）を使用する仕様。
    - duckdb 接続を併用。
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレーディング用 DB（`data/paper_trading.db` / `PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と完全分離。
    - 停止フラグ（`data/stop_requested.flag`）検知によりエンジン停止を実装。
    - 実行中プロセス情報の PID ファイル (`data/execution.pid` など) を利用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager を組み合わせて ExecutionEngine を構成。

- 設定管理 / CLI
  - config.py
    - 環境変数・設定管理クラス `Settings` を実装。多くのプロパティを提供（J-Quants/KabuAPI/LINE/データベース/監視閾値/システム設定 等）。
    - 自動 .env ロード機能を追加（プロジェクトルートを .git または pyproject.toml で判定）。優先順位は OS 環境 > .env.local > .env。
    - `.env` 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - `PAPER_FILL_MODE`（`instant|partial|never|reject`）の検証。
    - `KABUSYS_ENV`（`development|paper_trading|live`）や `LOG_LEVEL` の検証。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 入力済み値のマスキング（シークレット項目）や選択肢サポート、既存 .env の読み込み/Enter での再利用をサポート。
  - validate_config.py
    - 起動前に .env および config/*.yaml の妥当性を検証する CLI を追加。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の検証、DB パス親ディレクトリ確認、YAML のパースチェック（PyYAML 未インストール時はスキップ）、本番環境向けのガードチェック（LINE 設定・KILL フラグ）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 全アプリケーションで共通に使えるロギング初期化ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定（既存ハンドラはクリアして二重設定を防止）。
    - ログレベル・ログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみでフォールバック。
  - utils/process_priority.py
    - Windows（psutil の priority class）と POSIX（nice 値）を吸収するプロセス優先度設定ユーティリティを追加。
    - `set_process_priority(level)`（high/normal/low）を提供。アクセス権限や未対応 OS の場合は警告を出してスキップ。
    - `set_cpu_affinity(cpu_count)` でプロセスの CPU affinity を固定する機能を追加（未対応環境は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、signal_rank でタイブレーク）を行う `select_candidates`。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap`（既存保有に基づくセクター比率算出、当日売却予定銘柄の除外、"unknown" セクターは制限対象外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算を行う `calc_position_sizes` を実装。
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株丸め（lot_size）、per-stock 上限・aggregate cap（available_cash）スケーリング、cost_buffer による保守見積り、端数配分ロジックを実装。

- リサーチ / ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB 接続を受け取り、モメンタム／ボラティリティ／バリュー等のファクター計算を行う設計で骨格を追加（モメンタム計算の関数定義開始、定数定義を含む）。※ ファイル末尾で実装が途中まで（calc_momentum の続きは別コミットで追加予定）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
    - デフォルト DB パスは `data/paper_trading.db`、コマンドラインで `--db`、`--from`、`--to` を指定可能。
    - 各指標に対する PASS/FAIL 判定閾値を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）。

### 変更
- .env ローダーの優先順位と安全策を確立
  - OS 環境変数を保護するため `.env` ロード時に既存 OS 環境を protected として扱い `.env.local` は上書き可能だが OS 環境は上書きしない。
- ログ設定の振る舞い
  - 既存ハンドラをクリアしてから再設定することでログハンドラの重複出力を防止。
  - StreamHandler は stderr ではなく stdout を使用（タスクスケジューラや cron で stdout/stderr を一本化する運用を想定）。
- 実行系の DB 運用
  - run_monitoring は環境に依らず monitoring 用 sqlite_path（本番設定）を使用する旨を明示。
  - run_execution は paper_trading 環境時に専用の paper SQLite を使うように変更（本番 DB と明確に分離）。

### 修正（バグ修正 / 安全性向上）
- .env パーサ
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い（クォート外での "#" の取り扱い）など、.env ファイル解析を堅牢化。
  - 無効行のスキップやエラーハンドリング（読み込み失敗時に警告）を追加。
- MONITOR_POLL_INTERVAL の不正値対応
  - 0 以下や非整数の指定があった場合は警告を出しデフォルト（60 秒）にフォールバックする実装を追加（time.sleep に渡す値で ValueError を防止）。
- process_priority / set_cpu_affinity の堅牢化
  - アクセス権限不足や未対応 OS の場合は警告を出して安全にスキップするように変更。
- ログディレクトリ作成失敗のフォールバック
  - ログディレクトリ作成失敗時にファイルハンドラの作成をスキップし、標準出力のみで続行するように修正（起動停止を防止）。

### ドキュメント / その他注記
- config_setup により生成される .env ファイルに対して「.env を絶対に Git にコミットしないこと」を明記。
- portfolio モジュールは純粋関数でメモリ内計算を前提とし、DB 参照を行わない設計にしている（Unit Test が容易）。
- research/factor_research の calc_momentum 実装は途中までであり、今後のリリースで続きの実装・最適化を予定。

---

今後の予定（短期）
- research/factor_research の完全実装（モメンタム／ATR／Liquidity 等の計算実装完了）。
- ExecutionEngine / EngineConfig 周りの追加テストとペーパートレード動作検証。
- 追加の CLI（レポートの CSV 出力やメール通知等）の実装検討。

もし CHANGELOG に追加してほしい点（重要な変更や補足の強調）があれば教えてください。
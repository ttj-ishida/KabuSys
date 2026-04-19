# CHANGELOG

すべての重要な変更を記録します。本ファイルは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-19

初回公開リリース。KabuSys のコア機能と運用用ユーティリティ群を導入します。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依存せず本番用の SQLite パスを使用する実装。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
    - SQLite / DuckDB 接続の初期化とクローズ処理を実装。
  - run_execution: ExecutionEngine 起動用スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は専用の Paper Trading SQLite（data/paper_trading.db）と MockBrokerClient を使用して本番 DB と分離。
    - プロセス優先度を「high」に設定してエンジンを起動。
    - ストップフラグ・PID ファイルの取り扱い、バックグラウンドスレッドでのセッション実行と安全停止をサポート。

- 設定管理
  - config.py: 環境変数／.env 自動読み込み（.env/.env.local）機能を追加。
    - プロジェクトルートの推定（.git または pyproject.toml）に基づき .env を自動読み込み。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込みを無効化可能（テスト等向け）。
    - 各種設定プロパティを提供（DB パス、API トークン、PID path、閾値など）。
    - `PAPER_FILL_MODE` のバリデーション（instant/partial/never/reject）。
    - `KABUSYS_ENV`、`LOG_LEVEL` の許容値チェック、is_live/is_paper/is_dev ヘルパー。
    - `paper_sqlite_path`、`pid_file_path`、各種閾値（cpu/memory/disk）等のデフォルトを定義。

- 設定検証 / ウィザード
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）のチェック。
    - KABUSYS_ENV、LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLITE パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在確認および PyYAML 利用時はパース検証。
    - `--strict` オプションで警告を FAIL として扱う機能。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加。
    - 対話形式で主要環境変数を入力し .env を書き出し。
    - シークレット項目はマスク表示、既存値の読み込みと再利用、キャンセル時の安全処理を実装。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - stdout に出力する StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログレベル（引数 > 環境変数 LOG_LEVEL > デフォルト）・ログディレクトリ（引数 > LOG_DIR > logs/）の解決。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみ継続。
    - ファイルローテーションは 30 日保持。
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加（psutil 使用）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足時は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補を選抜（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコア 0 の場合は等配分にフォールバックし WARNING）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックし、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは警告のうえ 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出を実装。
    - リスクベース算出（risk_pct, stop_loss_pct）、単元株丸め（lot_size）、1 銘柄上限・アグリゲートキャップ（available_cash）や cost_buffer を考慮したスケーリング配分をサポート。
    - 価格欠損時のスキップや、キャッシュ不足時の比例縮小と残差処理を実装。

- Execution 関連コンポーネント（参照・結合のみ）
  - run_execution から組み立てられるコンポーネント群に対するインターフェース（BrokerClientFactory、ExecutionEngine、OrderRepository、OrderManager、Reconciler、RiskManager、init_monitoring_db 等）を利用する形で起動ロジックを実装（実体は別モジュールに存在する想定）。

- 監視 / モニタリング補助
  - monitoring 側初期化（init_monitoring_db 呼び出し）を起動時に保証。
  - run_monitoring で DuckDB 結合や例外ハンドリング（check_once の例外はログ出力して次ループに継続）を実装。

- Tools
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値（稼働率 99%、成功率 90% など）に基づいて PASS/FAIL 判定を出力。
    - コマンドライン引数で期間（--from/--to）および DB パス（--db）を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を利用。
    - SQLite のテーブル欠如時にも安全に動作し、該当指標を N/A / 0 と扱うフォールバックを実装。

- Research
  - research/factor_research.py（未完の一部を含む）:
    - DuckDB 接続から Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計を追加。モメンタム期間や ATR 等の定数を定義。
    - 設計方針: DuckDB の prices_daily / raw_financials を参照し純粋関数で結果を返す。

### 変更 (Changed)
- なし（初回リリースのため履歴上の変更は無し）。

### 修正 (Fixed)
- なし（初回リリースのため履歴上の修正は無し）。

### 削除 (Removed)
- なし。

### 非推奨 (Deprecated)
- なし。

### セキュリティ (Security)
- なし。

---

注記:
- ドキュメント・詳細な設計（PortfolioConstruction.md, StrategyModel.md 等）を参照する実装メモがソース内に多数あります。実行前に `python -m kabusys.config_setup` と `python -m kabusys.validate_config` の実行を推奨します。
- 本 CHANGELOG はソースコードから推測してまとめたもので、外部モジュール（例えば broker 実装や ExecutionEngine の内部実装）については呼び出し側の差分を記述しています。実際の動作確認・統合テストの結果に応じて追記・修正してください。
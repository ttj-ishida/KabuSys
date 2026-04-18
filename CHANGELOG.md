# Changelog

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

全般的な注記
- このリポジトリの初期リリースとして 0.1.0 を作成しました。
- 日付は生成時の参照日です。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージとバージョン情報
  - パッケージメタ情報を追加: `kabusys.__version__ = "0.1.0"`。

- 環境設定 / 設定管理
  - Settings クラスを実装（`src/kabusys/config.py`）。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env のパース機能（`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いなどをサポート）。
    - 環境変数の必須チェック `_require()` を提供（未設定時は ValueError）。
    - 各種設定プロパティを提供（J-Quants、kabuAPI、LINE、DuckDB/SQLite パス、Paper Trading 関連、監視しきい値、PID/kill flag 管理等）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化に対応。
    - `paper_fill_mode` の検証（有効値チェック）を導入。
    - 環境種別（development / paper_trading / live）とログレベルのバリデーションを実装。

- .env 作成ウィザード CLI
  - `src/kabusys/config_setup.py` に対話式ウィザードを追加。
    - 多項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DBパス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話的に作成・更新。
    - 既存 .env 読み込み、シークレットのマスク表示、確認プロンプト、.env 生成ロジックを提供。
    - `.env` ファイル書き出しのテンプレートを追加。

- 設定検証 CLI
  - `src/kabusys/validate_config.py` に設定検証ツールを追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML があれば内容検証）を実行。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - `--strict` オプションで警告を FAIL 扱いにする機能を提供。
    - エラー/警告/情報を標準出力へ整形して出力。

- 起動スクリプト
  - 実行エンジン起動スクリプト `src/kabusys/run_execution.py` を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - Paper Trading（KABUSYS_ENV=paper_trading）では専用 SQLite (`PAPER_TRADING_SQLITE_PATH` / デフォルト: data/paper_trading.db) を使用し、本番 DB と完全分離。
    - `BrokerClientFactory` を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、`ExecutionEngine` の起動ループ（デーモンスレッド）を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う停止・終了の仕組みを実装。
    - `init_monitoring_db()` を呼んで監視テーブルの存在を保証。

  - 監視ループ起動スクリプト `src/kabusys/run_monitoring.py` を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は環境設定にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用する挙動を明記。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。チェック中の例外を捕捉してログ出力し続行。
    - duckdb 接続を併用。

- ロギング / 実行環境ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通初期化機能を追加。
    - ログディレクトリ自動作成（失敗時はファイルハンドラをスキップし stdout のみで継続）。
    - 引数/環境変数でログレベルおよびログディレクトリを解決。

  - `src/kabusys/utils/process_priority.py`
    - マルチプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）を実装。
    - CPU affinity を最初 N コアに固定する `set_cpu_affinity()` を追加。
    - 権限不足時や未対応環境では警告ログを出して安全にスキップ。

- Portfolio 構築ライブラリ
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定関数 `select_candidates()` を追加（スコア降順、同点は signal_rank の昇順でタイブレーク）。
    - 重み計算: `calc_equal_weights()`, `calc_score_weights()` （スコア合計が 0 の場合は等配分へフォールバックして警告）。

  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap()` を実装（既存ポジションのセクター別エクスポージャ算出、上限超過セクターの新規候補除外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier()` を実装（bull/neutral/bear マッピング、未知レジームは警告の上 1.0 でフォールバック）。
    - ドキュメントに設計上の注意点（unknown セクターの扱いや price フォールバックの TODO 等）を明記。

  - `src/kabusys/portfolio/position_sizing.py`
    - ポジションサイズ計算 `calc_position_sizes()` を実装。
      - allocation_method: "risk_based"（リスクベース） / "equal" / "score" に対応。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、全体利用上限（max_utilization）、コストバッファ（cost_buffer）を考慮。
      - aggregate cap（全銘柄の投資合計が available_cash を超える場合のスケールダウン）と、ロット単位での残余配分ロジックを実装。
      - 価格欠損や非正数価格はスキップしてログを出力する。

  - `src/kabusys/portfolio/__init__.py` に上記関数をエクスポート。

- 研究 / ファクター計算
  - `src/kabusys/research/factor_research.py`（計算ロジックの骨格）
    - モメンタム、Value、Volatility、Liquidity 等のファクターを DuckDB 上の prices_daily / raw_financials テーブルから計算する設計を記述。
    - モメンタム計算関数 `calc_momentum()` の仕様と定数（1M/3M/6M、MA200、ATR など）を追加（関数の途中まで実装）。
    - DuckDB を用いた分析ワークフローを想定。

- Paper Trading 向け検証レポートツール
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から各種指標を集計し標準出力にレポートを出す CLI を追加。
    - 指標:
      - 稼働率（uptime_pct）、総ポーリング数、エラー数
      - 注文関連（Created / Filled / Sent のカウント）から注文成功率・送信率
      - risk_logs からリスク却下数
      - レイテンシ（avg, max, P95）
    - P95 計算ユーティリティ、期間フィルタ（--from/--to）、閾値定義（稼働率 99%、成立率 90% 等）を実装。
    - DB 存在チェックと sqlite3.OperationalError による耐障害的なデフォルト化を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境ファイルの生成テンプレートに「.env を絶対に Git にコミットしないこと」という注意を追加。

補足
- 起動スクリプト・各コンポーネントはログ出力・例外捕捉を意識して実装されており、運用時の観測性と安全性（プロセス優先度設定、stop flag による外部制御、paper_trading の DB 分離など）に配慮しています。
- 一部モジュール（factor_research など）は設計段階から実装途中まで含まれており、将来的に追加実装・拡張されることを想定しています。
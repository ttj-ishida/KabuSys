# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

履歴のフォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

## [0.1.0] - 2026-04-17
初回公開リリース（ベース実装）。自動売買システム KabuSys のコア機能群を追加しました。

### Added
- 基本パッケージ情報
  - パッケージのバージョンを設定: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - 環境変数/.env の自動読み込みを実装（プロジェクトルートの .git または pyproject.toml を起点に探索）。
  - .env パース機能を実装:
    - export プレフィックス、引用符付き値、エスケープ、行内コメントの扱いに対応。
  - 自動ロードの無効化オプション: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - Settings クラスを実装し、各種設定アクセスプロパティを提供（J-Quants / kabuAPI / DB パス / Paper Trading など）。
  - 各種設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 設定支援 CLI
  - 対話式 .env 作成・更新ウィザード: `kabusys.config_setup`（.env テンプレート生成、シークレットのマスク表示、保存確認）。
  - 設定検証 CLI: `kabusys.validate_config`（必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml の存在とパース検証、"live" 環境向けガード）を追加。
    - `--strict` オプションで警告も失敗（exit 1）扱いに可能。

- 実行エントリ / 監視エントリ
  - ExecutionEngine 起動スクリプト: `run_execution.py`
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper_trading 用 SQLite (`data/paper_trading.db`) を使用して本番 DB と分離。
    - 停止フラグ / PID ファイルによる制御を実装。
    - 各コンポーネント（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立て・起動フローを実装。
  - 監視ループ起動スクリプト: `run_monitoring.py`
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は本番の sqlite_path を参照（環境に依らず監視 DB は本番設定を使用する設計）。
    - stop フラグ検知で安全にループ終了、例外発生時はログを残して次ポーリングへ。

- DB / 分析基盤
  - DuckDB 接続を組み込み（analytics 用: settings.duckdb_path）。
  - 監視 DB 初期化ヘルパーを呼び出すフローを追加（起動時に監視テーブルの存在を保証、冪等性を確保）。

- ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定: score 降順・同点は signal_rank でタイブレーク（select_candidates）。
  - 重み計算: 等分配（calc_equal_weights）、スコア加重（calc_score_weights）。全スコアが 0 の場合は等分配へフォールバックして警告を出力。
  - リスク調整:
    - セクター集中制限（apply_sector_cap）。既存ポジションや当日売却予定を考慮して候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）: bull/neutral/bear に対応、未知レジームは警告して 1.0 にフォールバック。
  - 株数決定（calc_position_sizes）:
    - allocation_method に応じた株数計算（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate 上限の適用、cost_buffer を考慮したスケールダウン処理を実装。
    - 現金不足時のスケーリングと残余キャッシュを使った優先配分ロジック。

- 研究モジュール（DuckDB ベース）
  - ファクター計算モジュール（research.factor_research）を実装:
    - Momentum: 1M/3M/6M リターン、MA200 偏差（データ不足扱いの挙動を定義）。
    - Volatility / Liquidity: ATR, ATR 比率、20日平均売買代金、出来高比率等を計算。
    - DuckDB の SQL を用いた高速集計を採用。

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils.process_priority）:
    - Windows / POSIX を吸収する実装（psutil を利用）。
    - 権限不足や未対応 OS の場合は警告を出してフォールバック。

- ツール
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）:
    - DB から集計して稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出。
    - P95 計算、期間フィルタ、CLI オプション（--from, --to, --db）を提供。
    - デフォルト閾値を設定して PASS/FAIL 判定を行う（稼働率 99% 等）。

### Changed
- 設定ロード順序の明確化: OS 環境変数 > .env.local > .env の優先順位を採用。
- .env 読み込み時の既存 OS 環境変数保護機構を導入（protected set）。
- run_monitoring / run_execution 起動時に最初にプロセス優先度を上げる処理を共通化（set_process_priority("high") を呼ぶように実装）。

### Fixed
- MONITOR_POLL_INTERVAL のパースを堅牢化:
  - 非整数・0 以下の値が設定された場合は警告を出してデフォルト（60 秒）にフォールバックするように修正。
- 監視 DB 初期化（init_monitoring_db）呼び出しを冪等に確実に行うことで、起動時に監視用テーブルが存在しない問題を回避。

### Notes / Implementation details
- 設定ファイルテンプレート（.env）に重要な注意書きを含め、誤って Git にコミットしないよう指示を追加。
- Paper Trading と本番 DB を分離することで誤発注リスクを軽減。
- DuckDB を分析用途に導入し、research / portfolio ロジックは基本的に DB を読み取り専用で使用（発注 API にはアクセスしない設計）。
- 一部の処理（例: price が欠損した場合のエクスポージャー過少見積りなど）について TODO コメントで将来改善の指針を残しています。

### Deprecated
- なし（初回リリースのため該当なし）。

### Removed
- なし（初回リリースのため該当なし）。

### Security
- 機密情報（API トークン / パスワード等）は .env に保存する設計。config_setup での注意喚起を追加。
- 実運用環境（KABUSYS_ENV=live）における通知設定未設定や Kill Switch の安全設定に関する警告を validate_config で出力。

---

今後のリリースでは、ドキュメントの充実、ユニットテスト追加、エラー / 例外処理のさらなる堅牢化、各種パラメータ（lot_size 等）を銘柄ごとに扱える拡張などを予定しています。
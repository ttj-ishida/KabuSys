CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

注: バージョン情報は src/kabusys/__init__.py の __version__ に基づきます。

Unreleased
----------

(なし)

0.1.0 - 2026-04-24
------------------

Added
- 初回リリース: 基本的な日本株自動売買フレームワークを追加。
- コア設定/環境管理
  - .env 自動読み込み機能（プロジェクトルートの .env / .env.local、OS 環境変数を保護して読み込み）。
  - Settings クラスを追加し、環境変数経由で各種設定を取得可能に（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH 等）。
  - .env のパースロジックを強化（export 形式対応、クォート／エスケープやインラインコメントの扱い）。
  - 設定ウィザード CLI（kabusys.config_setup）を追加し、対話式に .env を作成・更新可能。
  - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数・パス・YAML ファイル存在・本番環境向けガード等をチェック。--strict により警告をエラー扱いにできる。

- 実行・監視スクリプト
  - run_execution: ExecutionEngine を起動するエントリスクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite を使用して本番 DB と分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番の sqlite_path を利用。
  - 停止制御用のフラグファイル（data/stop_requested.flag）および PID ファイル管理に対応。

- データベース / 分析
  - DuckDB および SQLite への接続を前提にした設計（Settings.duckdb_path / sqlite_path / paper_sqlite_path）。
  - 監視テーブル初期化ユーティリティ（monitoring_db.init_monitoring_db の利用）を起動時に呼び出す。

- ロギング / 運用ユーティリティ
  - 統一ログ設定ユーティリティ kabusys.utils.logging_setup を追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力をサポート。LOG_DIR / LOG_LEVEL からの解決、ログディレクトリ作成失敗時のフォールバック対応あり。
  - プロセス優先度／CPU affinity 設定ユーティリティ kabusys.utils.process_priority を追加（Windows/Linux/Mac を抽象化）。set_process_priority / set_cpu_affinity を提供。権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N を選択。タイブレークは signal_rank。
    - calc_equal_weights: 等金額配分を生成。
    - calc_score_weights: スコア比率で重み付け。全スコアが 0 の場合は等金額にフォールバック。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を抑制する候補フィルタリング。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバック）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数算出ロジックを実装。単元株（lot_size）丸め、per-stock 上限、集約上限（available_cash）に基づくスケーリング、cost_buffer による保守的見積りをサポート。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加。期間指定オプション、P95 レイテンシ計算、稼働率・注文成功率・送信率・リスク却下数などを出力し、簡易 PASS/FAIL 判定を行う。
  - 各種 CLI スクリプトにおけるフラグ/オプション（--from/--to/--db 等）を提供。

- 研究用モジュール（開始）
  - kabusys.research.factor_research のスケルトンを追加。DuckDB を利用したモメンタム・ボラティリティ等のファクター計算を設計。モメンタム計算関数 calc_momentum の導入（実装途中まで含む）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- .env は絶対にバージョン管理に含めない旨をドキュメント化（config_setup のヘッダに記載）。
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能にしてテスト安全性を確保。

Notes / Implementation details
- 実行時の挙動:
  - run_monitoring は MONITOR_POLL_INTERVAL を参照してポーリング頻度を決定（不正値はデフォルトにフォールバック）。停止フラグ検知でループを終了。
  - run_execution は paper_trading 環境では paper_sqlite_path を使用し、BrokerClientFactory によるブローカークライアントの切替を行う。
- ログ: ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続するよう安全化。
- process_priority: OS による差異を吸収する実装。権限不足等で設定できない場合は警告を出して継続。
- 既知の制限:
  - portfolio.risk_adjustment.apply_sector_cap は price_map に価格が欠損（0.0）の場合に過少評価の可能性がある旨を TODO コメントで記載。将来的にフォールバック価格対応を検討する予定。
  - research.factor_research は一部実装が途中（ファイル末尾が切れているため追加実装が必要）。

参考: バージョン
- src/kabusys/__init__.py にて __version__ = "0.1.0"

今後の予定（例）
- factor_research の完全実装（ファクター算出と正規化パイプライン）。
- ExecutionEngine / SystemMonitor の詳細なテストとエンドツーエンド検証。
- 単体テスト・統合テストの追加と CI 統合。
- 銘柄毎の lot_size 管理（マスタ化）や手数料モデルの拡張。

---
# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
この CHANGELOG はソースコードの内容から機能・変更点を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース（ソースコード解析に基づく機能まとめ）。

### Added
- 全体
  - パッケージ初期実装を追加。モジュール群は運用（execution）、監視（monitoring）、ポートフォリオ構築（portfolio）、リサーチ（research）、ユーティリティ（utils）、設定管理（config）および各種 CLI ツールを含む。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じた SQLite 接続分離（paper_trading 時は専用 DB を使用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動/停止制御。
    - スレッドでのエンジン実行と安全な停止処理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視用 DB 初期化（monitoring テーブル）を保証。
    - 監視は環境にかかわらず本番 sqlite_path を使う旨の実装。
    - 停止フラグ検知でループ終了、例外発生時はログを残して次ポーリングへ継続。

- 設定 / CLI
  - config.py: 環境変数 / .env 読み込みロジックを実装。
    - プロジェクトルート自動検出（.git / pyproject.toml）に基づく .env 自動読み込み（.env, .env.local）。
    - .env のパースは引用符・エスケープ・コメント等に配慮した堅牢な実装。
    - Settings クラスで各種設定値（DB パス、API トークン、環境フラグ、監視閾値 等）を提供。値検証（有効値チェック）を実装。
  - config_setup.py: 対話式 `.env` 作成ウィザードを追加。
    - 初期項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）に対応。
    - 既存 .env 読み込み、値の確認と保存機能を実装。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML 未インストール時はスキップ）。
    - `--strict` フラグで警告を失敗扱いにできる。

- ロギング / プロセス管理
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通ユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソール出力のみで継続。
    - ログレベル・ログディレクトリの解決ルールを実装。
  - utils/process_priority.py:
    - Windows / POSIX（Linux, macOS 等）を吸収したプロセス優先度設定機能（high/normal/low）を追加。
    - CPU affinity 設定補助関数を追加（N コアに固定）。
    - 権限不足や未対応環境を想定したフォールバックとログ出力を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順選定（タイブレーク: signal_rank）。
    - calc_equal_weights, calc_score_weights: 等金額配分およびスコア正規化配分（全スコア 0 の場合は等分配にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数算出ロジック。
    - lot_size（単元）丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合はスケールダウン）を実装。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的な見積り。

- リサーチ / ツール
  - research/factor_research.py:
    - DuckDB を用いたファクター計算基盤（Momentum, Value, Volatility, Liquidity）を設計。モメンタム計算等のための定数とインタフェースを定義（関数未完の箇所あり）。
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite データベースから稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定付きレポートを生成する CLI を追加。
    - P95 計算、期間フィルタ、閾値（稼働率 99%、成立率 90% 等）判定を実装。

### Changed
- なし（初回リリース想定のため該当なし）

### Fixed
- なし（初回リリース想定のため該当なし）

### Security
- なし

注記:
- 上記はリポジトリ内のコードから推測してまとめた CHANGELOG です。実際のコミット履歴に基づくものではありません。実際のリリースノート作成時はコミットや PR 情報を参照してください。
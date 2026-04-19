CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に基づきます。

Unreleased
----------

- （現在なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 設定管理:
  - .env ファイルと環境変数を統合して読み込む自動ローダを実装（プロジェクトルート探索は .git / pyproject.toml を起点に行う）。
  - .env のパース機能を独自実装（export プレフィックス、クォート／エスケープ、インラインコメント対応）。
  - Settings クラスを導入し、各種設定値（J-Quants トークン、kabu API、DB パス、paper_trading 関連、閾値、ログレベル等）をプロパティ経由で取得可能に。
  - KILL_FLAG_CLEAR_ON_START 等の起動フラグを環境変数で制御可能。
- 設定ユーティリティ / CLI:
  - 対話式 .env 作成ウィザード（kabusys.config_setup）を実装。既存 .env を読み込み、値のマスク表示、確認・保存機能を提供。
  - 設定検証 CLI（kabusys.validate_config）を実装。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML があればパース検証）を実行。--strict オプションで警告を FAIL 扱いにできる。
- 実行用スクリプト:
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。プロセス優先度を上げる、Paper Trading 時は paper_trading 用 DB を使用して本番 DB と分離する、BrokerClientFactory によるブローカー抽象化、ExecutionEngine の起動／停止管理（スレッド起動・停止フラグ監視、PID ファイル指定）を行う。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。監視 DB 初期化、停止フラグ検知、例外ハンドリングを備える。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
- 監視 / モニタリング:
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼び出してテーブル存在を保証する処理を両スクリプトで導入（冪等性確保）。
- ロギング / プロセス管理ユーティリティ:
  - 統一ロギング設定ユーティリティ（kabusys.utils.logging_setup）を実装。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ自動作成（失敗時はファイル出力をスキップ）や LOG_LEVEL / LOG_DIR の解決ロジックを実装。
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）を実装。Windows / POSIX 差分吸収（psutil 使用）、優先度設定のフォールバックと例外ハンドリングを実装。
- ポートフォリオ構築ロジック:
  - 銘柄選定・重み計算モジュール（kabusys.portfolio.portfolio_builder）を実装。候補選択（スコア降順）、等金額配分、スコア正規化配分（全銘柄スコア 0 の場合は等分にフォールバック）を提供。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）を実装。既存ポジションに基づくセクターエクスポージャ計算と候補除外、レジームに応じた投下資金乗数（bull/neutral/bear）を提供。
  - ポジションサイズ計算（kabusys.portfolio.position_sizing）を実装。allocation_method に応じた株数算出（risk_based / equal / score）、単元株（lot_size）丸め、per-stock 上限・aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer を考慮した保守的見積もり、残差処理による追加配分ロジックを提供。
  - portfolio パッケージの __all__ エクスポートを整備。
- 研究用モジュール:
  - ファクター計算モジュール（kabusys.research.factor_research）の骨組みを追加。Momentum（1M/3M/6M）、MA200 乖離、ATR、出来高指標などの計算方針を記載し、DuckDB 接続を受けて prices_daily / raw_financials を参照して計算する設計を採用。モメンタム計算関数 calc_momentum の実装を開始（ファイル末尾で実装継続中の痕跡あり）。
- ツール:
  - ペーパートレード検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を実装。system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL を判定。P95 計算、日付フィルタ、DB 存在チェック、出力フォーマットを備える。
- パッケージ情報:
  - パッケージバージョンを __version__="0.1.0" に設定。

Changed
- ログ出力の標準出力は stderr ではなく stdout を使用する方針を採用（cron / Task Scheduler 等でのリダイレクトを想定）。
- .env 自動読み込みの優先順位を明確化（OS 環境 > .env.local > .env）。OS 環境変数は保護され、.env.local は上書き可能。

Fixed
- 起動時の監視テーブル未存在による障害対策として、init_monitoring_db を実行して冪等的にテーブルを保証する処理を追加。

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues / TODO
- position_sizing.calc_position_sizes 内で価格が欠損（0.0）の場合の扱いについて注記あり。前日終値等のフォールバック価格を将来的に検討する旨を記載。
- factor_research モジュールは設計方針と一部実装を含むが、全文実装（データ取得・各ファクターの完全な SQL / 集計処理）が引き続き必要。
- config/*.yaml を生成するスクリプト（scripts/generate_config.py）への言及があるが、本リリースに同梱されていない可能性あり（validate_config からの案内）。
- ExecutionEngine / BrokerClientFactory 等、実行系の詳細実装は別モジュール（execution/*.py）に依存。実運用前に各ブローカークライアントとリスク設定の検証を推奨。

References
- この CHANGELOG はコードベース（src/ 以下のファイル群）に基づき推測して作成しています。運用ルールや追加的な変更履歴はリポジトリのコミットログに基づいて補完してください。
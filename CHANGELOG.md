# CHANGELOG

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠します。

全般:
- 仕様や設計に関する注記・ログ出力を充実させ、起動時・運用時の診断をしやすくしています。
- 環境変数やファイルパスの取り扱いは安全性を考慮しており、デフォルト値・検証・フォールバック動作を明示しています。

## [0.1.0] - 2026-04-17

初回公開リリース。主要な機能群をまとめて追加しました。

### Added
- 基本パッケージ構成
  - パッケージルートとバージョンを追加（kabusys.__version__ = "0.1.0"）。
  - エクスポート対象モジュールを __all__ で定義（data, strategy, execution, monitoring 等）。

- 環境設定関連
  - Settings クラス（kabusys.config）を追加し、環境変数から各種設定（DBパス、APIトークン、監視閾値、実行環境判定等）を取得可能にしました。
  - .env 自動ロード機能を導入（プロジェクトルートを .git / pyproject.toml で検出）。OS 環境変数を保護する仕組みを備え、.env と .env.local の読み込み順を制御します。
  - .env ファイルパース機能の強化：export プレフィックス対応、シングル/ダブルクォート内のエスケープ文字処理、インラインコメント処理などに対応。

- 設定ウィザード / 検証ツール
  - config_setup CLI（kabusys.config_setup）を追加。対話式ウィザードで .env の初期作成・更新を行えます（シークレット値のマスク表示、選択肢、デフォルト、保存確認を実装）。
  - validate_config CLI（kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が無ければ YAML 検証はスキップ）などを行い、--strict オプションで警告をエラー扱いにできます。
  - validate_config に本番（live）向けのガードチェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性警告）を追加。

- 実行・監視ランチャー
  - run_execution（kabusys.run_execution）を追加。ExecutionEngine の起動スクリプトで、プロセス優先度設定、Paper Trading 時の専用 SQLite DB 分離（data/paper_trading.db を既定）、BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てとスレッド駆動のエンジン実行、停止フラグ（data/stop_requested.flag）検知による安全停止を実装。
  - run_monitoring（kabusys.run_monitoring）を追加。SystemMonitor のポーリングループ起動スクリプトで、MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（検証とフォールバック含む）、監視 DB 初期化（本番 sqlite_path を利用）、停止フラグ検知処理を実装。

- モニタリング / レポート
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼び出すフローを追加（冪等に監視テーブルを保証）。
  - tools/paper_verification_report を追加。Paper Trading の検証レポート生成スクリプトで、稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを計算・表示し、閾値に基づく PASS/FAIL 判定を出力します。期間フィルタ（--from / --to）、DB パスの上書き (--db) に対応。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位 N 件抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全銘柄スコアが 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中に対する新規候補フィルタリング（sell コード除外や "unknown" セクターの取り扱いを考慮）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック挙動）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく各銘柄の発注株数計算、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、残差処理によるロット単位の追加配分ロジックを実装。
    - 将来的な拡張点（個別銘柄の lot_size マップ導入）を TODO コメントで明示。

- 研究 / ファクター計算
  - research/factor_research.py を追加。DuckDB 接続を受け取り prices_daily テーブルを参照してモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、流動性指標を計算する関数を実装。P95 計算ユーティリティなども含む。計算ウィンドウやスキャン範囲は定数で管理。

- ユーティリティ
  - utils/process_priority.py を追加。クロスプラットフォームでプロセス優先度（Windows の priority class / POSIX の nice 値）と CPU affinity を設定するユーティリティを提供。アクセス権限・未対応環境は警告ログでフォールバックします。

### Changed
- .env 読み込みの優先順を明確化（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止を追加。
- run_monitoring が監視 DB に対して環境にかかわらず本番 sqlite_path を使用する仕様に統一（監視データは環境分離しない設計）。
- run_execution が paper_trading 環境時に専用の paper_trading DB を使用して発注履歴等を本番 DB から完全分離する動作を実装。
- MONITOR_POLL_INTERVAL の値検証を実装し、不正値（0 以下・非数）時はデフォルトにフォールバックして警告を出すようにしました。
- validate_config の出力を情報/警告/エラーに分類して端末出力するよう改善。--strict モードで警告を失敗扱いにできます。
- process_priority: 未対応 OS や権限不足時に例外で落とさず警告ログでスキップする堅牢化を追加。

### Fixed
- .env パースの不正処理（クォート内のエスケープやインラインコメント誤解釈）に対応し、より堅牢にしました。
- ExecutionEngine 起動前に停止フラグが既に存在する場合は起動せずに終了する安全チェックを追加。
- スレッドを使用したエンジン実行中に停止フラグを検知した際、エンジン.stop() を呼んで安全に停止を試みる動作を実装。

### Notes / Known issues
- portfolio/position_sizing.calc_position_sizes:
  - 銘柄ごとの lot_size を将来的に導入する予定（現状は全銘柄共通の lot_size を想定）。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）がある場合にエクスポージャーが過少見積もられる可能性がある旨をコメントで残しています。将来的には前日終値やコストベースのフォールバックを導入予定です。
- research/factor_research の一部クエリはデータ前提（prices_daily の連続性や行数）に依存します。データ不足時は None を返す設計です。
- tools/paper_verification_report はローカルの SQLite DB 構造（system_status / trade_logs / risk_logs）を前提としているため、スキーマが異なる DB では一部クエリが失敗する可能性があります。該当エラーは OperationalError を捕捉して N/A 表示にフォールバックします。

### Security
- 秘密情報（API トークン等）は .env に保存する設計とし、config_setup ではマスク表示を行います。*.env をリポジトリにコミットしない旨の注記を .env 生成ファイルに記載しています。

-----------------------------------------------------------------------

今後の予定例（未実装 / 検討中）
- 個別銘柄単位の lot_size サポート（stocks マスタの導入）
- price の欠損時フォールバックロジック（前日終値や原価ベース）
- SystemMonitor / ExecutionEngine の詳細なインストルメンテーションおよび外部監視連携（LINE 通知等）の拡張
- DuckDB 上の集計クエリ最適化と大規模データ対応

（この CHANGELOG はソースコードから推測して作成しています。実装方針や将来計画はリポジトリのドキュメントやコミット履歴に従ってください。）
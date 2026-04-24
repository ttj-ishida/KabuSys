CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ修正

[Unreleased]

## [0.1.0] - 2026-04-24
初回リリース

Added
- 実行/監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用に data/paper_trading.db を使用して本番 DB と分離して運用可能。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に依らず本番用 sqlite_path を使用する仕様。
  - 両スクリプトは起動時にプロセス優先度を "high" に設定し、停止はプロジェクト直下の data/stop_requested.flag で制御。

- 設定・環境関連
  - config.py: Settings クラスを導入し、環境変数を一元管理。自動でプロジェクトルートの .env / .env.local をロードする（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。各種設定項目（DB パス、PID/kill フラグパス、しきい値、PAPER_FILL_MODE 等）とバリデーションを提供。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。デフォルト値や秘密値の扱いをサポート。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加（--strict オプションで警告を FAIL 扱いにできる）。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ初期化関数 setup_logging を追加。コンソール（stdout）出力と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加（Windows/POSIX 対応、権限不足時は警告ログでスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選択するユーティリティを追加。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の算出関数を追加（スコアが全て 0 の場合は等配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）を適用する関数を追加。既存保有のセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告後 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 重み・候補・現金・既存保有などを考慮して各銘柄の発注株数を算出。allocation_method に "risk_based" / "equal" / "score" をサポート。lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer（手数料等の保守見積り）による aggregate cap スケーリング、残差処理による追加配分ロジックを実装。

- 解析 / レポートツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。デフォルトしきい値:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - コマンド例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト data/paper_trading.db）。

- 研究用ファクター計算（基盤）
  - research/factor_research.py: DuckDB 接続を受け価格データからモメンタム・ボラティリティ・流動性等のファクターを計算するための関数群（設計・定数・calc_momentum の実装開始）。DuckDB 上の prices_daily / raw_financials を前提。

- パッケージ情報
  - __init__.py にてバージョンを 0.1.0 として定義。

Changed
- デフォルトのログ出力を stdout に統一（cron/スケジューラ起動での扱いを考慮）。
- .env 自動ロードの挙動:
  - 読み込み順: OS 環境 > .env.local > .env。既存 OS 環境は保護され上書きされない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数の必須値が未設定の場合に起動時エラーを出すヘルパー（Settings._require）を導入し、認証情報の未設定を明確化。config_setup ウィザードは .env に秘密情報を書き込むことを前提としており、.env を Git にコミットしないことを明記。

Notes / Known limitations
- research/factor_research.py はファクター計算ロジックの一部実装（calc_momentum の続き）を含み、完全実装は今後の改良対象。
- apply_sector_cap 内の価格欠損時（price == 0.0）によりエクスポージャが過少評価されうる旨の TODO コメントあり（将来的にフォールバック価格導入を検討）。
- process_priority および CPU affinity の設定は OS 権限に依存し、権限不足時は警告ログでスキップされる。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップしてコンソール出力のみで継続する設計。

作者・貢献方法
- 初回リリースです。バグ・要望・改善提案は issue を立ててください。README の導入手順・運用手順を参照のこと。
CHANGELOG
=========

すべての重要な変更点を記録します。この CHANGELOG は "Keep a Changelog" の形式に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 全体
  - 初回リリース (0.1.0)。自動売買システム "KabuSys" のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、解析ツール等を導入。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度の設定、SQLite/DuckDB 接続の確立、Broker クライアントの生成、OrderManager / RiskManager / Reconciler の組み立て、エンジンのスレッド実行と停止フラグ検出を行う。
    - KABUSYS_ENV=paper_trading のときはペーパートレード用 DB (data/paper_trading.db) を使用して本番 DB と分離。
    - 起動時に停止フラグ (data/stop_requested.flag) を検出した場合は起動を抑止する。
    - 実行時に execution.pid を生成して PID 管理を想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ / KeyboardInterrupt に対応して安全にクリーンアップ。

- 設定管理 / ツール
  - config.py: Settings クラスを導入。環境変数のアクセスを集中管理し、デフォルト値、検証、Path 変換を提供。
    - PAPER_FILL_MODE のバリデーション、paper_trading 用 sqlite パス、監視用しきい値等をサポート。
    - .env の自動読み込み機構を追加（プロジェクトルートを .git / pyproject.toml で検出）。OS 環境変数を保護するための上書きルールを導入。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。既存 .env の読み込み・マスク表示、項目定義、書き込み機能を提供。
  - validate_config.py: 起動前に設定不備を検出する CLI を追加。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在とパースをチェック。--strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御
  - utils/logging_setup.py: 一貫したログ設定ユーティリティを追加。stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続。
  - utils/process_priority.py: プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加。Windows / POSIX(nice) を考慮し、CPU affinity を設定する関数も導入（set_cpu_affinity）。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 銘柄選定と重み計算関数を追加
    - select_candidates: スコアでソートして上位 N を選出
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア正規化配分（スコア合計が 0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限を適用し、上限超過セクターの候補銘柄を除外（"unknown" セクターは制限対象外）
    - calc_regime_multiplier: マーケットレジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数を計算するアルゴリズムを実装。risk_based / equal / score の配分方式、単元株丸め、per-position と aggregate の上限、利用可能現金に基づくスケーリング、手数料・スリッページを見積もる cost_buffer を考慮したスケーリング処理等をサポート。

- 解析 / レポート
  - tools/paper_verification_report.py: ペーパートレード実行結果を解析して PASS/FAIL 判定を行うレポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し、閾値に基づいた判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB パス指定可能。

- 研究用ユーティリティ
  - research/factor_research.py: ファクター計算モジュール（モメンタム、ボラティリティ、バリューなど）の骨組みを追加。DuckDB を用いて prices_daily / raw_financials を参照する設計。calc_momentum のインターフェースと定数群を実装（注: 関数実装の一部は継続開発の余地あり）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Implementation details
- .env 自動ロード
  - プロジェクトルートが検出されない場合は自動ロードをスキップするため、パッケージ配布後やテスト実行時に予期せぬ環境汚染を防止。
  - .env の読み込みは OS 環境変数を保護（既存値は上書きしない）し、.env.local は override=True で読み込む挙動。

- ロギング
  - コンソール出力は stdout を使用（cron 等で stdout/stderr を統合している環境を考慮）。

- ペーパートレード分離
  - Execution は paper_trading 環境で専用 SQLite を使用するため、本番監視 DB とデータが混在しない設計。

- 停止フラグ
  - run_execution / run_monitoring ともにプロジェクト内 data/stop_requested.flag を参照して安全に停止する仕組みを提供。

今後の予定（Short roadmap）
- factor_research の各ファクター実装完了（残処理の実装・最適化）
- ExecutionEngine / SystemMonitor の詳細実装および統合テスト
- 単体テスト・CI 設定の追加
- ドキュメント（ユーザー向けセットアップ手順、運用ガイド）の整備

もし CHANGELOG に追記したい詳細（例えば実際のリリース日を別にしたい、Unreleased セクションに今後の変更を入れたい、特定のファイルの変更点をより細かく書きたい等）があれば教えてください。
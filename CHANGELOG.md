CHANGELOG
=========

すべての重要な変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

注: 以下はリポジトリ内のコードから推測して作成した変更履歴です。

## [Unreleased]
- 次回リリースに向けた変更点はここに記載します。

## [0.1.0] - 2026-04-18
初回公開リリース。

### Added
- コア実行スクリプトと監視スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用のペーパートレード DB を使用し MockBrokerClient を使って本番 DB と分離して動作する。
  - run_monitoring.py: SystemMonitor をポーリングする監視ループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。停止フラグファイル検知による安全停止に対応。
- 設定管理・ウィザード・検証ツールを追加
  - config.py: 環境変数/ .env 読み込みロジックを実装。プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み。quoted 値や export 形式に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化あり。Settings クラスで各種設定プロパティを提供（DB パス、ペーパートレード設定、閾値等）。
  - config_setup.py: .env を対話式に生成・更新するウィザードを実装。シークレット項目のマスク表示、既存値の再利用、書き込みテンプレートを提供。
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV の値チェック、DB パス確認、YAML パース（PyYAML がない場合はスキップ）や本番環境向けのガード（LINE 通知設定、Kill Switch 設定）を実施。--strict により警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリを追加（pure functions）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等比率/スコア加重の重み計算（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数の算出（calc_regime_multiplier）を実装。未知レジームはフォールバックして 1.0 を返す。
  - portfolio.position_sizing: 発注株数計算（calc_position_sizes）を実装。allocation_method として "risk_based", "equal", "score" をサポート。lot_size（単元）やコストバッファ、aggregate cap によるスケーリング、端数処理の再配分ロジックなどを備える。
  - portfolio パッケージのエクスポートを整備（__all__ に主要関数を列挙）。
- 実行系コンポーネントの組立て
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 用の組立てコード（run_execution 側）。RiskManager のデフォルト構成値（max_position_pct 等）を設定し、初期ポートフォリオ値をブローカーから取得して利用する。
  - BrokerClientFactory を利用して環境に応じたブローカークライアントを生成（ペーパートレードと本番を切り替え）。
- 監視 DB 初期化ユーティリティを追加（monitoring.monitoring_db.init_monitoring_db を利用）
- ログ設定ユーティリティを追加
  - utils.logging_setup.setup_logging: ルートロガーに stdout 出力（StreamHandler）と日次ローテーションファイル出力（TimedRotatingFileHandler）を設定。ログディレクトリ自動作成、失敗時のフォールバック（コンソールのみ）に対応。環境変数 LOG_LEVEL / LOG_DIR に対応。
- プロセス優先度・CPU affinity 設定ユーティリティを追加
  - utils.process_priority: Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity 設定用の set_cpu_affinity を実装。psutil によるエラーを安全にハンドリングして警告出力。
- ペーパートレード検証ツールを追加
  - tools.paper_verification_report: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL レポートを生成。期間フィルタ、--db オプション、閾値はソース中の定数で定義。テーブルが存在しない場合も安全に扱う。
- research.factors：ファクター計算基盤を追加
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity 等の計算方針を定義。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。モメンタム計算関数（calc_momentum）の実装開始（ファイル末尾で実装途中の箇所あり）。

### Changed
- なし（初回リリースにつき差分変更は無し）

### Fixed
- .env パーサーの堅牢化
  - import 時に読み込む .env パーサーは export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い（クォート有無で異なる解釈）に対応するよう実装。既存の OS 環境変数は保護され、.env.local で上書きできる挙動を採用。
- ログディレクトリ作成に失敗した場合の挙動を明確化（ファイル出力をスキップしてコンソールログのみ継続）。

### Security
- シークレット項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の取り扱いに配慮
  - config_setup の対話ではシークレットをマスク表示。Settings._require による未設定時の早期例外処理を実装。

### Documentation
- 各モジュールに docstring を充実させ、CLI の使用法や設定項目説明（config_setup の項目説明、validate_config の使い方等）を追加。

### Internal
- モジュール構成を整理し、各責務を明確化（utils/*, portfolio/*, execution/*, monitoring/*, research/*, tools/*）。
- logging_setup と process_priority など共通ユーティリティを各起動スクリプトから再利用する設計に統一。

---

注記:
- 本 CHANGELOG はソースコードの内容から推測して作成したものであり、実際のコミット履歴と完全に一致しない可能性があります。必要に応じて追記・修正してください。
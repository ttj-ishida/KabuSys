CHANGELOG
=========

すべての重要な変更点を記録します。  
このファイルは Keep a Changelog の記法に準拠しています。  

フォーマット:
- Unreleased: 今後のリリース向けの未反映項目や既知の TODO
- 各リリース: 追加(Added)、変更(Changed)、修正(Fixed)、非推奨(Deprecated)、削除(Removed)、セキュリティ(Security)

Unreleased
----------
### 追加予定 / 既知の課題
- research/factor_research.py の実装が途中で終了しているため（ファイル末尾が切れている）、Momentum 等のファクター計算が未完成。完成・テスト・ドキュメント化が必要。
- position_sizing.calc_position_sizes の価格欠損時の扱いに対する TODO コメント有り: price が欠損した場合のフォールバック（前日終値や取得原価など）の追加検討。
- 一部関数のエッジケース（ゼロ除算や DB の欠落テーブル）に対する追加のユニットテストを推奨。

0.1.0 - 2026-04-23
-----------------
### Added
- 基本アーキテクチャ・起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の際は専用のペーパートレード用 SQLite を使用する（data/paper_trading.db、環境変数で上書き可能）。停止フラグ（data/stop_requested.flag）検出による安全停止、PID ファイル管理、スレッド実行ロジックを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に関わらず本番 sqlite_path を使用する仕様。
- 設定・検証・ウィザード
  - config.py: 環境変数管理を実装。プロジェクトルートの探索（.git または pyproject.toml）を起点に .env / .env.local 自動読み込み（無効化フラグ有り）。Settings クラスに多数のプロパティ（DB パス、KABUSYS_ENV、ログレベル、paper_trading 関連設定等）を提供。PAPER_FILL_MODE のバリデーションを実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを提供。シークレット項目のマスク表示、既存 .env の読み込み、書き出しテンプレートを実装。
  - validate_config.py: 起動前に環境変数や config/*.yaml の存在・基本整合性をチェックする CLI を提供。--strict モードで警告も失敗扱いにできる。PyYAML がない場合のフォールバック処理を備える。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR の解決ルール・ハンドラの重複防止を実装。
  - utils/process_priority.py: psutil を用いてプロセス優先度（high/normal/low）および CPU affinity 設定を行うユーティリティを追加。Windows / POSIX（Linux/macOS/FreeBSD）向け差分処理とエラーハンドリングを実装。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等分配にフォールバックする挙動を持つ。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックで 1.0 を返す。
  - portfolio/position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に対応した株数決定ロジック、単元株（lot_size）丸め、aggregate cap（available_cash を超える場合のスケーリング）および残余キャッシュを用いた分配ロジックを実装。コストバッファ（cost_buffer）を考慮した保守的見積りを実装。
- 実行系コンポーネント（初期接続 / 組み立て）
  - Execution 側で BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager の組み立てを追加。RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 設定、max_drawdown 等）を含む。
  - ExecutionEngine の起動/停止管理、PID ファイル指定対応を実装。
- 監視・分析関連
  - monitoring.monitoring_db (利用される初期化関数の呼び出し箇所を含む): run_execution/run_monitoring から監視テーブルの初期化を保証（冪等）。
  - duckdb を用いた分析用 DB パス（Settings.duckdb_path）の統合。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間フィルタ、稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数などを集計して PASS/FAIL を判定する。閾値（稼働率 99%、成功率 90% 等）はファイル内定数で定義。DB 不在やテーブル欠如に対する耐性を実装（該当項目は N/A / 0 にフォールバック）。
- パッケージメタ
  - __init__.py にてバージョンを "0.1.0" に設定し、主要サブパッケージを __all__ で公開。

### Changed
- （初期リリース）プロジェクトの基本設計に沿った各種 API と起動フローを整備。ログ出力や優先度設定など共通ユーティリティによる統一を行った。

### Fixed
- validate_config と config 系の頑健性向上:
  - .env のパースでシングル/ダブルクォート、エスケープ、コメント処理、export プレフィックスに対応。
  - .env 自動読み込み時に OS 環境変数を保護するための protected set を導入。

### Known issues / Notes
- research/factor_research.py は途中で切れている（未完成）ため、本リリースでは一部ファクター計算が未提供。
- position_sizing と risk_adjustment の一部ロジックに将来的改善のための TODO が残っている（価格欠損時のフォールバック等）。
- 一部外部パッケージ（psutil, duckdb, PyYAML など）への依存がある。未インストール時の挙動はモジュール内で考慮されている箇所があるが、完全な機能を得るためには依存関係のインストールが必要。

Deprecated
----------
- なし

Removed
-------
- なし

Security
--------
- なし（本リリースで明示的なセキュリティ修正は検出されませんでした。機密情報（トークン・パスワード）は .env に保存し、config_setup で Git コミット禁止の注意を明示しています。）

クレジット / 備考
----------------
- 本 CHANGELOG はリポジトリ内のソースコードから推測して作成しました。実際の変更履歴（コミットログ）と差異がある可能性があります。必要に応じて実際のコミット履歴に基づいて修正してください。
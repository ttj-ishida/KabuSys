# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
注: 以下の履歴はリポジトリ内のコード内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。

Unreleased
---------
### Added
- research/factor_research モジュールの初期実装（モメンタム / 移動平均 / ATR / 出来高等の計算ロジックの骨組み）。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。
- portfolio モジュール向けのユーティリティ関数の追加（エクスポージャー・ポジション調整等の追加改善予定）。
- 一部のドキュメントコメントを拡充。

### Changed
- なし（未リリースのため差分は暫定的）。

### Fixed
- なし（未リリースのため差分は暫定的）。

0.1.0 - 2026-04-19
------------------
### Added
- 初版リリース: KabuSys 自動売買システムのコア機能群を追加。
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じて本番/ペーパートレード DB を分離し、BrokerClientFactory 経由でブローカークライアントを生成。停止フラグ（data/stop_requested.flag）の検知で安全に停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数による間隔上書き（デフォルト 60 秒）。Monitoring は環境に関係なく本番 sqlite_path を使用。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツール（期間指定オプション、P95 計算、稼働率／注文成功率／レイテンシ等の判定）。
  - kabusys.config_setup: .env 初期作成・更新ウィザード（対話式）。
  - kabusys.validate_config: .env と config/*.yaml の起動前検証 CLI（--strict モード対応）。
- 設定 / 環境読み込み
  - kabusys.config: 高度な .env パーサーを実装（export プレフィックス対応、クォート内部のバックスラッシュエスケープ処理、インラインコメント処理など）。プロジェクトルート自動検出による .env/.env.local の自動読み込み（OS 環境変数は保護）。Settings クラスで各種設定値をラップし、値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実施。
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: シグナルのスコア降順選抜。
    - calc_equal_weights / calc_score_weights: 重み計算（スコアが全て 0 の場合は等金額にフォールバック）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限フィルタ。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の各配分方式を実装。単元株（lot_size）丸め、per-position および aggregate cap、コストバッファ考慮、利用可能現金に応じたスケーリングを実装。
- 実行系コンポーネント組み立て
  - ExecutionEngine の組み立て例を run_execution で実装（OrderRepository / OrderManager / RiskManager / Reconciler の結合、デフォルト RiskConfig の設定）。
- ロギング・プロセス制御ユーティリティ
  - kabusys.utils.logging_setup: StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定する共通ユーティリティ。ログディレクトリ作成失敗時のフォールバック対応あり。
  - kabusys.utils.process_priority: クロスプラットフォームでプロセス優先度設定（Windows は HIGH_PRIORITY_CLASS 等、POSIX は nice 値）。CPU affinity を設定する set_cpu_affinity も提供。set_process_priority はアクセス権限不足時に警告でスキップ。
- DB 初期化 / 監視関連
  - monitoring.monitoring_db.init_monitoring_db 呼び出しにより監視テーブルの存在を保証（冪等）。
  - SystemMonitor のワンショットチェックを実行する loop を run_monitoring に実装。
- パッケージ情報
  - kabusys.__version__ を "0.1.0" として設定。

### Changed
- none（初版リリース） — 多数の新規追加により機能群が整備された状態。

### Fixed
- MONITOR_POLL_INTERVAL の不正値（整数変換失敗や 0 以下）に対して警告を出しデフォルトへフォールバックする処理を実装（run_monitoring）。
- ログディレクトリ作成に失敗した場合にファイルハンドラをスキップしてコンソール出力のみで継続するよう保護（logging_setup）。
- .env 読み込みで OS 環境変数を保護し、.env.local での上書きを許可するロード順を実装（config）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし。

Notes / 既知の制約・ TODO
- sector_exposure 計算で price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性あり（apply_sector_cap 内の TODO）。将来的に前日終値や取得原価を使うフォールバックを検討。
- position_sizing は現状全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_map のサポートを予定（TODO コメントあり）。
- research/factor_research は大部分の設計が整っているが、実装の細部や追加ファクターの検証・テストが必要（現段階では一部未完の可能性あり）。
- 実行には外部依存がある:
  - psutil: プロセス優先度 / CPU affinity 設定に使用（必須ではないが推奨）。
  - duckdb: ファクター計算や分析処理に使用。
  - PyYAML: config/*.yaml のパース検証で任意（インストールされていない場合は検証をスキップして警告）。
- 本番運用時の安全対策:
  - validate_config の追加チェックにより KABUSYS_ENV=live の場合に LINE 通知設定や Kill Switch の設定を警告する。
  - run_execution / run_monitoring は stop/kill フラグを検知して安全に停止するフローを持つ。

以上。今後のリリースでは実装済み機能のテストケース追加、研究モジュールの完成、銘柄単位の lot_size 対応、監視・アラートの強化等が想定されます。
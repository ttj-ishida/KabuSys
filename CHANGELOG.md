# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
新しいセクションはすべて日付付きのリリース単位で記載します。

## [0.1.0] - 2026-04-19

### Added
- プロジェクト初版リリース。
- 実行/監視用エントリポイントを追加
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory によるブローカー選定、OrderRepository/OrderManager/RiskManager/Reconciler を組み立ててエンジンを別スレッドで実行。paper_trading 環境では paper 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知で安全に終了。
- 環境・設定管理
  - config: 環境変数取得用 Settings クラスを実装。.env 自動ロード機構（プロジェクトルート検出、.env / .env.local のロード順序、OS 環境変数の保護）を実装。各種設定プロパティ（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 用設定など）を提供。PAPER_FILL_MODE の検証や各種閾値取得も実装。
  - config_setup: .env を対話式に生成/更新するウィザードを追加。既存 .env 読み込み、シークレットマスク表示、保存前確認を備える。
  - validate_config: 起動前に .env と config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや YAML ファイルの存在/パース確認（PyYAML 未導入時は警告）、本番環境向けの追加ガードを実装。--strict オプションで警告を失敗扱いに可能。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア全て 0 の場合は等配分にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックに基づく候補フィルタ。sell_codes を考慮したエクスポージャー算出や "unknown" セクターの扱いを実装。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはフォールバックし警告）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。単元株丸め、1 銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングと残余配分ロジックを備える。
- ユーティリティ
  - utils/logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。ログレベル・出力先の解決ルールを定義。
  - utils/process_priority: Windows/Linux/macOS を吸収するプロセス優先度設定ユーティリティを追加。nice 値・Windows 優先度クラスに対応し、アクセス権限不足等は警告でスキップする。CPU affinity を設定するヘルパーも実装。
- ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。system_status/trade_logs/risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出し、閾値に基づく PASS/FAIL 判定を出力。日付フィルタ・DB パスの指定に対応。
- research/factor_research: DuckDB 接続を受けてモメンタム等のファクターを計算するモジュールの雛形を追加（prices_daily / raw_financials を参照する設計、計算定数を定義）。※一部未完（実装継続予定）。

### Changed
- ログ出力の実装方針
  - logging_setup で標準出力を stdout に統一（stderr ではなく stdout を使用）。cron/Task Scheduler などでのリダイレクト運用を考慮。
- データベースの扱い
  - 監視（monitoring）側は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計（監視テーブルの常設を想定）。一方で run_execution は paper_trading 時は専用 DB を使用し本番と分離。

### Fixed
- .env パーサーの堅牢性向上
  - config モジュール内の .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールを考慮して正しく値を抽出するよう実装。無効行やキー欠落時の扱いを改善。

### Notes / Implementation details
- stop/kill フラグの扱い
  - run_execution / run_monitoring はプロジェクト内の data/stop_requested.flag を監視して安全に終了する仕組みを採用。ExecutionEngine は実行中にフラグ検知で engine.stop() を呼び出す。
  - pid ファイルの利用（execution.pid など）と pid_file の設定をサポート。
- 安全設計
  - process_priority やログディレクトリ作成等、権限不足や未対応 OS の場合は例外で落とさず警告ログを出してフォールバックする実装。
- 設定検証
  - validate_config は PyYAML 未導入環境でも graceful に振る舞い、YAML 検証はスキップして警告を出す（任意依存の扱い）。
- Paper Trading の検証基準（tools/paper_verification_report）
  - 稼働率: >= 99.0%
  - 注文成功率 (Filled/Created): >= 90.0%
  - 送信率 (Sent/Created): >= 95.0%
  - P95 レイテンシ: <= 200 ms

### Known limitations / TODO
- research/factor_research は一部実装が継続中（コメント内に設計指針あり）。
- position_sizing の lot_size は現状全銘柄共通で 100 を想定。将来的に銘柄別単元対応を検討。
- apply_sector_cap の価格欠損時の扱いについて注記（TODO: フォールバック価格の導入検討）。
- PAPER_FILL_MODE 等の詳細な動作（MockBrokerClient の実装）に関するテスト・ドキュメント整備が必要。

---

保持ポリシー: 重要な後方互換性のない変更は今後のリリースで明示します。新機能追加・バグ修正は次回リリースで逐次追記してください。
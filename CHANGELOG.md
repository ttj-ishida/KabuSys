# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在のバージョン: 0.1.0 — 2026-04-18

## [0.1.0] - 2026-04-18

### 追加
- 初回リリースを追加。
- 実行用スクリプトを追加:
  - run_execution: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient による仮想発注をサポート。実行中の停止フラグ管理、PID ファイル出力、スレッドによるセッション実行を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB は環境に関係なく本番 sqlite_path を使用。
- 設定関連 CLI を追加:
  - config_setup: 対話式ウィザードで .env を作成・更新するユーティリティ（項目の説明・シークレット入力・デフォルト値サポート）。
  - validate_config: .env と config/*.yaml の事前検証ツール。--strict オプションで警告も失敗扱いにできる。
- ユーティリティを追加:
  - utils.logging_setup: stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定する共通ログ設定。ログディレクトリ作成に失敗してもコンソール出力で継続する。
  - utils.process_priority: Windows / POSIX を透過してプロセス優先度（high/normal/low）を設定。CPU affinity を最初の N コアに固定するヘルパーも提供。
- 設定管理を追加:
  - config.Settings クラス: 環境変数取得ラッパー（検証付き）。J-Quants / kabu API / DB パス / 監視閾値 等のプロパティを提供。settings インスタンスをエクスポート。
  - 自動 .env ロード機能: プロジェクトルート（.git / pyproject.toml）を探索して .env/.env.local を自動読み込み（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサーは export プレフィックス、クォート文字、エスケープ、インラインコメント（条件付き）に対応。
- ポートフォリオ構築モジュールを追加（pure functions、DB非参照）:
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づいて新規候補を除外。sell_codes（当日売却予定）をエクスポージャー計算から除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック、警告ログ）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算。リスクベースの計算、単元（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap のスケーリングと残余配分ロジックを実装。
- リサーチ / ファクター計算の下地を追加:
  - research.factor_research: momentum 等のファクター計算を行うモジュール骨格（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。（実装の続きあり）
- ツールを追加:
  - tools.paper_verification_report: Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH または --db）から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計し検証レポートを出力。閾値に基づく PASS/FAIL 判定を実装。P95 計算ユーティリティを提供。

### 変更（設計上の決定・振る舞い）
- ログ出力:
  - コンソール出力は stderr ではなく stdout に出力（Task Scheduler / cron 等で stdout/stderr を一本化する運用を想定）。
  - 日次ローテーションと 30 日保持をデフォルトに設定。
- DB の扱い:
  - 監視（monitoring）用 DB は環境にかかわらず本番 sqlite_path を使用する設計。Execution は paper_trading 時に専用 DB を使用して本番 DB と分離。
- 環境変数ロード優先度:
  - OS 環境変数 > .env.local（上書き）> .env（未設定時のみセット）。既存の OS 環境変数は保護される。

### 修正 / 改良
- .env パーサーの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い改善などを実装し、実運用で見られる .env の多様な書式に対応。
- 設定検証ツール（validate_config）:
  - 必須環境変数の未設定検出、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在チェックと YAML パースの試行（PyYAML がない場合はスキップ）を実装。
  - KABUSYS_ENV=live のときに本番向けチェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を追加。

### 既知の制限 / TODO
- research.factor_research モジュールは実装の途中（ファイル末尾が途中で切れている箇所あり）。momentum 等のファクター計算は継続実装が必要。
- position_sizing の価格欠損時の扱い（price == 0.0 の場合にエクスポージャーが過少見積もられる問題）について注記を残し、将来的にフォールバック価格（前日終値・取得原価等）を導入する想定。
- 一部の機能は実際のブローカークライアント実装に依存（BrokerClientFactory 等）。paper_trading モードでの動作確認を推奨。

### セキュリティ
- .env ファイル生成ウィザードで生成される .env にはシークレットが含まれるため、コメントに「.env は絶対に Git にコミットしないこと」を明記。

---

今後のリリースでは以下を検討しています:
- research モジュールの完全実装（全ファクター計算・正規化ユーティリティ）
- テストカバレッジの追加（ユニットテスト・統合テスト）
- 銘柄毎の lot_size 備考（マスタ導入）と手数料 / スリッページの詳細な扱い
- Windows / POSIX のさらなる互換性テストおよび CI 統合

(注) 本 CHANGELOG はソースコードから推測してまとめたものであり、実運用状況に応じて差分が生じる可能性があります。
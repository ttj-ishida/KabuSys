# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース

### Added
- 基本ライブラリ・CLI を追加
  - パッケージ初期化: kabusys/__init__.py（バージョン 0.1.0）
- 設定管理
  - kabusys.config.Settings: 環境変数から設定を取得する集中管理クラスを提供。
    - KABUSYS_ENV（development / paper_trading / live）検証
    - LOG_LEVEL 検証
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - PAPER_FILL_MODE 検証（instant / partial / never / reject）
    - 各種監視・PID ファイル・閾値設定のプロパティを提供
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）
    - export 構文・クォートあり/なし・インラインコメントに対応する独自パーサを実装
- .env 対話式ウィザード（CLI）
  - kabusys.config_setup: 対話的に .env を作成/更新するウィザードを提供（--env-file でパス指定可能）
  - 秘匿項目のマスク表示、デフォルト・選択肢サポート、確認プロンプト、ファイル書き出し
- 設定検証 CLI
  - kabusys.validate_config: 必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在/パース（PyYAML がある場合）を検証
  - --strict オプションで警告も失敗扱いにできる
- 実行関連スクリプト
  - kabusys.run_execution: ExecutionEngine を起動するランチャー
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db 既定）を使用して本番 DB と分離
    - BrokerClientFactory 経由でブローカークライアント生成（Mock 対応）
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てとデーモンスレッド実行
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止
    - PID ファイル管理（data/execution.pid）
    - 起動時にプロセス優先度を "high" に設定
  - kabusys.run_monitoring: SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、負値や 0 はデフォルトへフォールバック）
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化
    - 停止フラグ（data/stop_requested.flag）検出で終了
    - 起動時にプロセス優先度を "high" に設定
- ロギング・プロセスユーティリティ
  - kabusys.utils.logging_setup.setup_logging:
    - ルートロガーを統一的に設定（stdout StreamHandler と 日次ローテーションの TimedRotatingFileHandler）
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみ継続）
    - LOG_LEVEL / LOG_DIR の解決ロジック
  - kabusys.utils.process_priority:
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度を設定（psutil 使用、失敗時は警告でスキップ）
    - set_cpu_affinity(cpu_count): 指定コア数への固定（psutil に依存、失敗時は警告）
- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等金額にフォールバック）
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは上限適用除外）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear、および未知値フォールバック）
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく株数計算
    - 単元（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）でのスケーリング、コストバッファ考慮、残差の lot 単位での再配分アルゴリズムを実装
- Research / ファクター計算（基盤）
  - kabusys.research.factor_research: DuckDB 接続を受け取って Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計（関数群の骨格と定数を実装）
- ツール
  - kabusys.tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB 指定可能
    - システム稼働率（uptime）、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定（閾値はソース内定義）
    - 空データやテーブル欠損に対する堅牢なフォールバック実装
- パッケージエクスポート
  - kabusys.portfolio.__init__ によりポートフォリオ関数を簡易インポート可能にした

### Notes (動作上の重要な点)
- run_monitoring は監視に本番用 sqlite_path を使用する設計（KABUSYS_ENV に依存せず監視データを一元化）
- run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用し、ペーパートレード用 DB と本番 DB を分離
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後の動作でも CWD に依存せず機能する（プロジェクトルートが見つからない場合は自動ロードをスキップ）
- ログは標準出力（stdout）へ出力するため、cron やプロセスマネージャでのリダイレクト運用が容易
- psutil による優先度・CPU affinity 設定は権限やプラットフォームによって失敗することがあり、失敗時は警告ログが出力され処理は継続される

### Changed
- 初版のため該当なし

### Fixed
- 初版のため該当なし

### Deprecated
- 初版のため該当なし

### Removed
- 初版のため該当なし

### Security
- .env は生成時に README に注意書きを入れ、Git へ絶対にコミットしない旨を明示

---

注: 本 CHANGELOG は与えられたコードベースの内容から重要な追加機能・動作仕様を推測して作成しています。実際のリリースノートとして使用する場合は、必要に応じて日付・詳細・影響範囲をチーム内で確認の上、調整してください。
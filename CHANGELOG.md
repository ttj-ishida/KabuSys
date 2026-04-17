Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

KEEP A CHANGELOG
================

すべての変更はセマンティックバージョニングに従って記載します。

## [0.1.0] - 2026-04-17
初回リリース

### 追加
- 基本アーキテクチャとコアユーティリティを実装
  - パッケージバージョン: __version__ = 0.1.0
- 環境/設定管理
  - kabusys.config: .env 自動読み込み機能（.env → .env.local、OS環境変数優先）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能
    - .env パーサは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメント（空白前の # をコメントとみなす）に対応
  - Settings クラス: 環境変数アクセスのラッパー（各種プロパティとバリデーション）
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 等のプロパティを提供
    - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の値検証を実装
- 設定支援 CLI
  - kabusys.config_setup: 対話式ウィザードで .env を作成・更新するツールを追加
  - kabusys.validate_config: 起動前に環境変数・config/*.yaml の整合性チェックを行う CLI を追加
    - --strict オプションで警告を FAIL 扱いにできる
    - PyYAML がない場合は YAML の内容検証をスキップし警告を出す
- 実行 / 監視起動スクリプト
  - kabusys.run_execution: ExecutionEngine の起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db を既定）および MockBrokerClient を使用（本番 DB と分離）
    - プロセス優先度を起動時に "high" に設定
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応
    - RiskManager 初期設定値（max_position_pct, max_utilization, rate_limit_per_sec 等）をデフォルトで設定し、initial_portfolio_value を broker.get_available_cash() から取得
  - kabusys.run_monitoring: SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）
    - 監視は環境にかかわらず「本番 sqlite_path」を使用する旨をドキュメント化（監視 DB は production path を参照）
    - 停止フラグ（data/stop_requested.flag）を検知してループ停止
    - 例外時にログを出力して次ポーリングへ継続
- モニタリング DB 初期化・SystemMonitor 連携（init_monitoring_db 呼び出し）
- DuckDB を分析用 DB として利用（duckdb.connect を使用）
- Process ユーティリティ
  - kabusys.utils.process_priority: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定を追加
    - Windows / POSIX(Linux, Darwin, FreeBSD) に対する振る舞いを実装、権限不足や未対応 OS の場合は警告を出してスキップ
    - set_process_priority(level: "high" | "normal" | "low")
    - set_cpu_affinity(cpu_count: int | None)
- ポートフォリオ構築モジュール（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N 件を選定（タイブレークルールあり）
    - calc_equal_weights / calc_score_weights（スコア全ゼロ時は等金額配分へフォールバック）
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有から算出、"unknown" セクターは除外対象外）
    - calc_regime_multiplier: レジームに応じた資金乗数（bull/neutral/bear、未知レジームはフォールバック 1.0）
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の配分ロジック、単元株（lot_size）丸め、aggregate cap のスケーリングと残差処理を実装
    - cost_buffer による手数料・スリッページ保守的見積もりをサポート
- 研究用ファクター計算（DuckDB ベース）
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比等（部分的に実装、SQL ベース）
    - DuckDB の prices_daily テーブルを前提に計算
- ペーパートレード検証ツール
  - kabusys.tools.paper_verification_report: Paper Trading の検証レポート出力ツールを追加
    - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms
    - 日付フィルタ (--from / --to)、--db オプションに対応
    - trade_logs / system_status / risk_logs テーブルから指標を集計して PASS/FAIL 判定を出力
- いくつかのユーティリティ（フォーマッタ関数等）

### 変更
- （初回リリースのため特になし）

### 修正
- （初回リリースのため特になし）

### 既知の制約・注意事項
- run_monitoring は明示的に「環境にかかわらず本番 sqlite_path を使用する」実装となっているため、意図しない DB を参照しないよう設定に注意してください。
- apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過小評価される可能性がある（TODO コメントあり）。将来的にフォールバック価格の導入を検討。
- position_sizing:
  - 現状 lot_size は全銘柄共通。将来的に銘柄別 lot_map に拡張する予定（TODO コメントあり）。
- process_priority / cpu_affinity:
  - OS や権限によっては設定が失敗する可能性があり、その場合は警告を出してスキップする。
- .env パーサはできる限り柔軟に対応するが、極端に破壊的な行や非互換な構文は想定外。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- calc_score_weights は全スコアが 0 の場合、等金額配分へフォールバックして警告を出します。
- calc_regime_multiplier は未知のレジーム値の場合 1.0 でフォールバックして警告を出力します。

### 将来的な改善予定（言及点）
- apply_sector_cap の価格フォールバック（前日終値や取得原価の使用）
- position_sizing の銘柄別 lot_size サポート
- factor_research の追加ファクター・最適化と DuckDB ベースの高速化
- モニタリング/実行のメトリクスやアラートを外部サービス（LINE 等）へ通知する仕組みの強化

------------------------------------------------------------
注: 上記は提供されたコードベースの内容から推測してまとめた CHANGELOG です。実際のリリースノートとして公開する場合は、リリース日や責任者、追加のリリース手順（DB マイグレーション等）があれば追記してください。
# Changelog

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠の形式で記載しています。

## [0.1.0] - 2026-04-19

初回リリース。本リポジトリの基礎機能を実装しました。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを公開（kabusys v0.1.0）。
  - プロジェクトルート自動検出ロジックを実装し、.env の自動読み込み（.env / .env.local）を行う機能を追加。
  - 環境変数の強力なパーサ実装（クォート、エスケープ、コメント処理対応）。

- 設定管理
  - Settings クラスを実装。環境変数に基づく設定取得 API を提供（J-Quants / kabu API / DB パス / ログ等）。
  - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等の Paper Trading に関する設定と検証を追加。
  - KABUSYS_ENV / LOG_LEVEL 等のバリデーションを実装。is_live / is_paper / is_dev のヘルパーを追加。

- CLI / ユーティリティ
  - config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加（シークレット項目のマスク表示、既存値の再利用対応）。
  - validate_config: .env と config/*.yaml の起動前検証ツールを追加。必須環境変数・パス・YAML パース（PyYAML 任意）・本番環境向けガードをチェック。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のバックグラウンドスレッド実行、停止フラグおよび PID ファイル管理を実装。
    - RiskManager の初期デフォルト設定を追加（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - data/stop_requested.flag による停止フラグ検知を実装。
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）等を集計し PASS/FAIL を判定。
    - コマンドラインで期間指定 (--from/--to) と DB パス指定 (--db) に対応。
    - デフォルト DB パスは data/paper_trading.db。

- ロギング / プロセス管理
  - utils.logging_setup: 全起動スクリプトで共通利用できるロギング初期化を実装。
    - コンソール出力は stdout、ファイル出力は日次ローテーション（TimedRotatingFileHandler）で 30 日保持。
    - LOG_DIR / LOG_LEVEL 経由での設定、ディレクトリ作成失敗時はフォールバックする堅牢設計。
  - utils.process_priority: psutil を利用したクロスプラットフォームのプロセス優先度設定と CPU affinity のユーティリティを追加。
    - Windows / POSIX(nice) を吸収し、アクセス権限エラー等は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコアソート（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。スコアが全て 0 の場合は等分配にフォールバック。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックと候補除外ロジック（max_sector_pct）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）。未知レジームは警告を出してフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method (risk_based / equal / score) による発注株数計算、単元株丸め、1 銘柄上限、aggregate cap（available_cash に合わせたスケールダウン）を実装。
    - cost_buffer（スリッページ・手数料の保守見積り）対応および残余キャッシュ分配ロジックを実装。

- リサーチ
  - research.factor_research: ファクター計算モジュールの骨組みを実装（モメンタム等の定数・関数設計を含む）。DuckDB 接続で prices_daily / raw_financials を参照する設計。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の問題 / 制限 (Known issues / Limitations)
- apply_sector_cap 内の価格欠損ハンドリングについて TODO コメントあり:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があるため、将来的に前日終値や取得原価などのフォールバック価格を導入予定。
- calc_position_sizes:
  - lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_size を持つ設計への拡張予定（TODO コメント）。
- research.factor_research:
  - 実装が途中（ソース末尾が途中で切れている箇所があります）。完全なファクター計算は今後の実装課題。
- 依存:
  - psutil, duckdb は必須依存。PyYAML は validate_config の YAML 内容検証で任意依存（未インストール時は検証をスキップして警告）。
- run_monitoring:
  - 監視 DB に常に本番 sqlite_path を使う設計のため、ローカル開発で別 DB を使いたい場合は注意が必要。

### セキュリティ (Security)
- （現時点で特筆すべきセキュリティ修正はなし）
- 注意: .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダに明記）。

---

今後の予定（例）
- research.factor_research の完成・テスト追加
- 銘柄別 lot_size、価格フォールバック実装
- 追加のユニットテストおよび CI 設定
- 実行・監視周りの運用ドキュメント整備

以上。必要であれば、リリースノートを英語や別フォーマットで出力します。
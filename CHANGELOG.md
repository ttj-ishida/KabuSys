# CHANGELOG

すべての notable な変更を記載します。形式は "Keep a Changelog" に準拠しています。

全体のバージョン: 0.1.0 — 2026-04-18

## [0.1.0] - 2026-04-18

### Added
- 基本バイナリ / 起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。プロセス優先度を高に設定してから起動。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - BrokerClientFactory を使ってブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）に対応。停止フラグ検知時に安全に停止。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して状態を記録。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt にも対応。

- 設定管理 / 初期化ツール
  - config.py
    - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - 強化された .env パーサ（`export KEY=val`、クォート文字列とバックスラッシュエスケープ、インラインコメント処理等に対応）。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス /監視・システム設定等をプロパティで提供。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path 等ペーパートレード関連設定を提供。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新可能。項目定義とマスク表示（シークレット）をサポート。
    - 既存 .env の読み込み・再利用、保存前の確認ダイアログ付き。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 等の値検証、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML が無ければ警告）などを実施。
    - `--strict` オプションで警告も失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - コンソール出力は stdout を使用し、日次ローテート（TimedRotatingFileHandler）でログファイル（logs/<app_name>.log）にも出力。ファイル出力失敗時はコンソールのみで継続。
    - 環境変数 LOG_LEVEL / LOG_DIR を尊重。既存ハンドラをクリアして二重出力を防止。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）をプラットフォーム差を吸収して設定するユーティリティ。
    - Windows（HIGH_PRIORITY_CLASS 等）と POSIX (nice) をサポート。アクセス権限不足等は警告でスキップ。
    - set_cpu_affinity を追加し、プロセスを最初の N コアに固定可能（未指定時は変更なし）。
    - 例外ハンドリングとログを適切に行うよう実装。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分。スコア合計が 0 の場合はフォールバックで等配分。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を判定し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す。未知のレジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて株数を計算。
    - risk_based: 損切り・リスク率に基づいてベース株数を算出。
    - equal/score: 重みを用いた配分。1 銘柄上限（max_position_pct）・lot_size（単元）で丸め。
    - aggregate cap（available_cash を超える場合）のスケーリング処理を実装。cost_buffer を考慮し、余りは fractional remainder に基づき lot 単位で追加配分。
    - lot_size 固定（将来的に銘柄別対応を検討する旨コメントあり）。

- リサーチ / ファクター計算（骨組み）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity などのファクター計算を行うモジュールの骨組みを追加（DuckDB 接続を受け、prices_daily / raw_financials を参照して計算する設計）。
    - calc_momentum の実装開始（関数と定数が追加） — 実装途中の箇所あり（ファイル末尾が途中で切れているため作業継続が必要）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレードの検証レポート生成ツール。
    - `--from` / `--to` / `--db` オプションをサポート。デフォルト DB は data/paper_trading.db。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等を算出し、閾値に基づいて PASS/FAIL を判定。P95 計算ロジック、欠損時の N/A 表示を実装。
    - デフォルト閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）を定義。

- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリースとして新規追加が中心）

### Fixed
- なし（初回リリース）

### Notes / Implementation details / 限界事項
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされる。また、OS 環境変数を保護する仕組み（protected keys）を採用。
- config.validate_config は PyYAML が存在しない環境では YAML のパース検査をスキップして警告する。
- process_priority/set_cpu_affinity はプラットフォームや権限に依存するため、失敗した場合は警告を出して安全にスキップする設計。
- portfolio/position_sizing の lot_size は現状グローバル固定で、銘柄別単位（異なる単元）の考慮は将来の拡張事項としてコメントあり。
- research/factor_research.py はファイル末尾が途中で切れており、いくつかの関数（calc_momentum の完全実装等）が未完。リサーチファクター群の完成は今後の課題。
- run_monitoring は monitoring 用 DB を環境に関係なく本番 sqlite_path に接続する設計のため、開発/テスト時の扱いに注意（意図的な分離は run_execution 側で paper_trading 用 DB を使う形で実現）。

---

今後の予定（提案）
- research/factor_research の完成（全ファクターの実装・テスト）。
- 発注ロジック ExecutionEngine のエンドツーエンド統合テスト、mock ブローカーの拡充。
- 銘柄別 lot_size / 手数料モデルの導入（position_sizing の拡張）。
- 監視・アラート（LINE）連携の追加テストと本番ガードの強化。

もし CHANGELOG の粒度（個別ファイル別のコミット単位やより古い履歴の分割）を細かくしたい場合は、どの単位で分けるか（例: CLI / core / portfolio / utils）を教えてください。
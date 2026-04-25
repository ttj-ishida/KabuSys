# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
リリース日付はコードベースの最終更新日（2026-04-25）です。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-25

Added
- 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag ファイルで行う。監視は常に本番用 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient（BrokerClientFactory 経由）で本番 DB と分離。エンジンはデーモンスレッドで実行し、停止フラグ/pid ファイルを管理。

- 設定関連の追加/改善
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を実装し、.env/.env.local の自動読み込みを実現（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パース機能を強化（export 形式対応、クォート文字・バックスラッシュエスケープの処理、インラインコメント処理の改善）。
    - Settings クラスを導入。環境変数経由の設定取得をプロパティで行う（DB パス、LINE トークン、監視閾値、KABUSYS_ENV バリデーション、PAPER_FILL_MODE の検証など）。
    - paper_trading 用専用パス（paper_sqlite_path）と paper_fill_mode のバリデーションを追加。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。シークレット項目はマスク表示、確認後に .env を出力。

  - validate_config.py
    - 起動前に .env と config/*.yaml の基本チェックを行う CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、YAML の存在・パースチェック、KABUSYS_ENV=live 時の追加警告などを実施。--strict オプションで警告を失敗扱いにできる。

- ログ関連ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。LOG_DIR/LOG_LEVEL を尊重。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（Windows と POSIX を吸収）。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応環境では警告を出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates（スコア順ソート）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）を追加。
  - portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中上限による候補除外）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）を追加。
  - portfolio/position_sizing.py
    - calc_position_sizes を実装。allocation_method（"risk_based" / "equal" / "score"）に対応。単元株（lot_size）で丸め、1 銘柄上限や aggregate cap（available_cash）を考慮したスケーリング、手数料・スリッページ見積りを考慮する cost_buffer を実装。残差配分ロジック（fractional remainder による lot 単位での追加配分）を備える。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を読み取り、稼働率・注文成功率・送信率・API レイテンシ（P95 など）に基づく PASS/FAIL レポートを生成する CLI を追加。閾値はスクリプト内定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。--from/--to/--db オプションをサポート。

- データベース初期化/監視連携
  - 監視用 DB の初期化関数 init_monitoring_db を利用して、起動時に監視テーブル存在を保証（冪等）。

- パッケージメタ
  - __version__ を "0.1.0" に設定。

Changed
- ロギング出力を stdout に統一（cron/Task Scheduler 等からのリダイレクト運用を想定）。
- .env 自動ロードの優先順位を明確化（OS 環境 > .env.local > .env）。.env.local は既存の OS 環境変数を保護しつつ上書き可能。

Fixed / Improved
- .env パースの堅牢化（クォートされた値のエスケープ処理、export プレフィックス対応、コメント扱いの改善）。
- プロセス優先度設定や CPU affinity 設定における権限エラーや未実装 API の取り扱いを安全に（警告ログを出してスキップ）。
- position sizing のスケールダウンロジックを改善し、残余キャッシュを使った再配分を安定化。

Notes / Misc
- research/factor_research.py が追加され、モメンタム等のファクター計算の骨格（DuckDB を用いた計算設計）が含まれるが、一部実装（ファイル末尾付近）は未完了／切り出し途中です。
- 実行系（ExecutionEngine / BrokerClientFactory / OrderManager / RiskManager / Reconciler 等）は起動スクリプトから組み立てられる前提で実装されており、paper_trading 環境ではデータ分離（paper_sqlite_path）を徹底。

Deprecated
- （なし）

Removed
- （なし）

Security
- （なし）

---

参考:
- 主要ファイル: src/kabusys/{config.py,config_setup.py,validate_config.py,run_monitoring.py,run_execution.py,__init__.py}
- ユーティリティ: src/kabusys/utils/{logging_setup.py,process_priority.py}
- ポートフォリオ: src/kabusys/portfolio/*
- ツール: src/kabusys/tools/paper_verification_report.py

もし特定の変更点（例: ある関数の挙動や閾値の変更）について、より詳細な説明や差分ベースのリリースノートが必要であれば教えてください。コードのさらに細かい箇所を参照して注記を追加します。
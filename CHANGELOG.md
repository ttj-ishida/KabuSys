# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

注意: コードベースから推測して記載しています（実際のコミット履歴ではなく、現行ソースの機能・挙動を要約しています）。

## [0.1.0] - 2026-04-23

### Added
- 基本パッケージ初期実装
  - パッケージバージョン: `__version__ = "0.1.0"`。
- 実行エントリ / デーモン化支援
  - run_execution: 自動売買エンジン起動スクリプト（ExecutionEngine を起動、スレッドで run_session を実行）。停止フラグ（data/stop_requested.flag）監視、PID ファイル管理、paper_trading 環境では専用の paper DB を使用。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視処理は環境にかかわらず本番 sqlite_path を使用。
- 環境設定と検証 CLI
  - config_setup: 対話式ウィザードで `.env` を新規作成 / 更新する CLI を追加。複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など）を扱う。
  - validate_config: `.env` と `config/*.yaml` の事前検証ツール。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML がインストールされている場合）、`--strict` オプションで警告を FAIL 扱いにできる。
- 環境読み込みユーティリティ
  - 自動 `.env` 読み込み: プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を自動ロード（OS 環境変数を優先し、上書きが必要な場合は .env.local を使う仕組み）。
  - .env パーサ: export プレフィックス、クォートされた値（バックスラッシュエスケープ処理）、インラインコメントの取り扱い等に対応した堅牢なパーサを実装。
  - Settings クラス: 環境変数をラップして型変換・妥当性チェック（KABUSYS_ENV の有効値チェック、PAPER_FILL_MODE の検証、パスの Path 化など）を行う。
- ロギング / プロセス制御ユーティリティ
  - logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - process_priority: psutil を用いたプロセス優先度設定（Windows / POSIX の差分吸収）。`set_cpu_affinity` による CPU ピニング機能も提供（利用は任意）。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N を選択（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分の重み計算（スコア全0 の場合はフォールバックで等金額）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限をチェックして候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算、単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）でのスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した安全な割付ロジックを実装。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード SQLite DB を解析して検証レポートを出力する CLI を追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを算出し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）で PASS/FAIL 判定を行う。期間フィルタ（--from, --to）および DB パス指定（--db）をサポート。
- データ基盤との接続
  - DuckDB / SQLite の接続サポートを各起動スクリプトに組み込み（duckdb_path / sqlite_path を Settings で管理）。監視向けテーブル初期化用 init_monitoring_db が呼ばれる。
- Execution 側のリスク管理骨格
  - Execution 側で RiskManager / Reconciler / OrderManager / OrderRepository を組み立てるための呼び出しを用意。RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、initial_portfolio_value を broker.get_available_cash() から取得する設計。

### Changed
- ログ出力
  - コンソール出力は stdout に統一（cron/スケジューラとリダイレクトしやすくするため）。ファイル出力は日次ローテーション・30日保持。
- 環境読み込みの優先順位明確化
  - OS 環境変数 > .env.local > .env の優先順位でロード。OS 環境変数は保護され、.env/.env.local によって上書きされない。
- run_monitoring の挙動
  - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能。0 以下や不正な値は無効としてデフォルト 60 秒にフォールバックし、警告ログを出す。
- run_execution の DB 選択
  - paper_trading 環境では paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する挙動を明確に実装。

### Fixed / Robustness
- .env パーサの強化
  - export プレフィックスやシングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱い（クォート有無に応じた挙動）を実装し、実際の .env の多様なケースに耐えるようにしている。
- 設定検証の堅牢化
  - validate_config による起動前チェックで不足項目や設定ミスを早期検出できるようにした（必須環境変数、KABUSYS_ENV の不整合、YAML パースエラーの検出など）。
- 例外時のログ出力
  - run_monitoring のループ内で monitor.check_once() が例外を投げてもループを継続し、例外情報を logger.exception で記録する耐障害性を追加。
- プロセス優先度 / CPU アフィニティの失敗回避
  - psutil による設定でアクセス権限不足等の例外が発生した場合は警告ログを出してスキップする安全な実装。

### Documentation / UX
- config_setup の対話的な入力フローと .env 書き出しテンプレートを実装。シークレット項目はマスクして確認表示。
- validate_config の出力は INFO/WARNING/ERROR を分けて表示し、--strict オプションで警告をエラー扱いにできる。

### Notes / Known limitations
- research.factor_research モジュールはファクター計算の設計とモメンタム計算の骨組み（スケルトン）を含むが、完全実装は途上（ソースは途中で切れている）。DuckDB を用いた prices_daily / raw_financials 参照設計になっている。
- position_sizing では lot_size を銘柄共通と仮定している。将来的に銘柄別単元（lot_map）対応の拡張が必要という TODO コメントあり。
- apply_sector_cap のエクスポージャー計算で price が欠損（0.0）の場合に過少見積りになる可能性があり、将来的にフォールバック価格導入を検討。

---

（今後のリリースでは、より詳細な機能追加・バグ修正を個別に分けて記載してください。）
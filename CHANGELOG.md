# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」準拠です。  

- リリース方針: 重要な機能追加は "Added"、既存挙動の変更は "Changed"、バグ修正は "Fixed" に分類します。

## [0.1.0] - 2026-04-19

### Added
- 初回公開: KabuSys 基本モジュール群を追加。
  - パッケージメタ情報: kabusys/__init__.py にバージョン 0.1.0 を設定。

- 環境・設定管理
  - Settings クラス（src/kabusys/config.py）を追加。環境変数から各種設定を取得（J-Quants / kabu API / DB パス / ログ設定 / 監視閾値 など）。
  - .env 自動読み込み機能を実装:
    - プロジェクトルート (.git または pyproject.toml) を基準に .env/.env.local を自動読み込み。
    - OS 環境変数を保護する仕組みをサポート（優先度制御）。
  - .env パーサの堅牢化: export プレフィックス対応、クォート内エスケープ、インラインコメント処理などを実装。

- 設定用 CLI / ユーティリティ
  - 対話式設定ウィザード（src/kabusys/config_setup.py）を追加。初回 .env 作成／更新を支援。シークレット項目はマスク表示。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加:
    - 必須環境変数やパスの存在チェック、config/*.yaml の存在／パース検証（PyYAML がある場合）を行う。
    - --strict オプションで警告をエラー扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）へ分離し、MockBrokerClient を使用する仕組みを想定（BrokerClientFactory で抽象化）。
    - 起動時にプロセス優先度を高く設定（set_process_priority）。
    - PID ファイル / 停止フラグ利用による安全な起動・停止制御。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行ルーチンを用意。RiskConfig のデフォルト値（max_position_pct 等）を設定し、初期ポートフォリオ値を broker.get_available_cash() から取得して利用。

  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告を出しデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - 停止フラグファイル検知によるループ終了、例外はログに記録して次回ポーリングへ継続。

- DB / 分析連携
  - DuckDB 用パス設定（Settings.duckdb_path）と run_* スクリプトでの DuckDB 接続サポート。
  - 監視 DB 初期化ヘルパ（監視テーブルの冪等初期化）を呼び出す実装箇所を整備。

- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加:
    - stdout への StreamHandler と 日次ローテーション (TimedRotatingFileHandler) をルートロガーへ設定。
    - ログディレクトリ自動作成、作成エラー時はファイル出力をスキップしてコンソールのみ継続。
    - LOG_LEVEL / LOG_DIR の環境変数解決に対応。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加:
    - Windows / POSIX の差分を吸収して nice 値や PRIORITY_CLASS を設定。
    - set_cpu_affinity により最初 N コアへピンニング可能（権限不足時は警告でスキップ）。

- ポートフォリオ構築モジュール（src/kabusys/portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の実装（スコア全体が 0 の場合は等配分へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた資金乗数を返却（未知レジームは警告を出して 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算、単元株丸め、個別および集約のキャップ処理、available_cash 超過時のスケールダウンと端数処理（lot 単位での再配分）を実装。
    - cost_buffer による手数料・スリッページ見積りを考慮。

- 解析 / ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加:
    - 指定期間（--from / --to）または DB を指定して、稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）などを算出し、PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99% など）を定義。
    - P95 計算、日付フィルタ生成、欠損テーブルへの安全なフォールバックを実装。

- 研究モジュール（着手）
  - src/kabusys/research/factor_research.py を追加（モメンタム等のファクター計算を目的。DuckDB 接続を受け取り、prices_daily / raw_financials を参照する設計）。（注: ファイルは一部未完の箇所あり。続きを実装予定）

### Changed
- ログの標準出力は stderr ではなく stdout を採用（cron 等で stdout/stderr をまとめてリダイレクトする環境向け）。
- init_monitoring_db を各起動スクリプトで呼び出すことで監視テーブルの存在を保証（冪等）。

### Fixed
- （初回リリースのため該当なし）

### Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、現状は当該銘柄をスキップする実装。将来的に前日終値や取得原価をフォールバック価格として使用することを検討（コード内に TODO コメントあり）。
  - 単元株数（lot_size）は現在グローバル一律。将来的に銘柄別 lot_map を受け取る仕様へ拡張予定。
- risk_adjustment.apply_sector_cap:
  - sector_map に存在しない銘柄は "unknown" 扱いになり、セクター上限適用対象外となる。マスタデータの整備が推奨。
- research/factor_research.py は設計方針を記載しているが、一部実装が未完（今後の追加実装対象）。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用する設計：テスト環境で明示的に分離したい場合は sqlite_path を適切に設定してください。
- 設定ウィザードは .env を生成するが、セキュリティ上 .env をリポジトリにコミットしない旨をファイルヘッダに明記。
- process_priority.set_process_priority / set_cpu_affinity:
  - 権限不足や非対応 OS の場合は警告ログを出して処理をスキップする動作。運用環境での動作確認を推奨。

---

以上が初回リリース（0.1.0）の変更点です。今後は research モジュールの完成、ExecutionEngine の詳細実装・テスト、モニタリング指標の拡張などを予定しています。
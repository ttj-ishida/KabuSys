# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

次のバージョンはセマンティック バージョニングに従います。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-23
初回リリース。

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - src/kabusys/__init__.py にバージョン情報を追加。
- 環境・設定管理
  - .env 自動読み込み機能を実装（プロジェクトルート検出 .git / pyproject.toml ベース）。環境変数の読み込み順は OS 環境変数 > .env.local > .env。
  - .env パーサーを実装。export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に（JQUANTS、KABU、DB パス、Paper Trading 関連、監視閾値、ログ設定等）。
  - 環境変数未設定時にエラーを投げる _require ヘルパーを実装。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の Paper Trading 用設定を追加。
- 設定ユーティリティ / CLI
  - 対話式ウィザード: config_setup.py を実装し .env の初期作成／更新を支援（秘密項目はマスク表示）。
  - 設定検証ツール: validate_config.py を実装。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース検証（PyYAML がある場合）。--strict フラグで警告を FAIL 扱いにできる。
- 実行スクリプト
  - 実行エンジン起動スクリプト run_execution.py を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て。
    - 停止フラグ（data/stop_requested.flag）検知で安全にシャットダウン。実行 PID ファイル管理。
    - プロセス優先度を高 (high) に設定して起動。
  - 監視ループ起動スクリプト run_monitoring.py を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 環境にかかわらず監視は本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知でループ終了。
- 監視 DB 初期化用ユーティリティ（init_monitoring_db を参照する構成）を組み込み（監視テーブルの存在保証）。
- ロギング／プロセス制御ユーティリティ
  - logging_setup.py を実装。StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック。
  - process_priority.py を実装。psutil を使って Windows/Linux/macOS のプロセス優先度（nice）と CPU affinity を抽象化。権限不足や未サポート環境では警告ログを出してスキップ。
- ポートフォリオ構築モジュール（純粋関数群、DB 非依存）
  - portfolio_builder.py:
    - select_candidates: スコア降順で上位 N を選択、タイブレークは signal_rank。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分実装。全スコアが 0 の場合は等金額配分にフォールバック。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中を検出して新規候補の除外を行うロジック。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を決定。単元株丸め、1 銘柄上限、aggregate cap（利用可能現金）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）に対応。
- Paper Trading 検証レポートツール
  - tools/paper_verification_report.py を追加。paper_trading SQLite から稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し、PASS/FAIL 判定を行う CLI を提供。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- リサーチ用モジュール（骨子）
  - research/factor_research.py にモメンタム等ファクター計算の設計および calc_momentum の冒頭の実装を追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。（ファイル末尾は途中で切れているが、モジュールの骨子と定数が含まれる）

### Changed
- .env の扱いを慎重化:
  - OS 環境変数を保護しつつ .env/.env.local を読み込む実装（既存 OS 環境変数は上書きされないよう保護）。
  - .env のパースにおいてクォートやエスケープ、インラインコメントに対する挙動を明確化。
- ログ出力の挙動:
  - StreamHandler を stdout に固定して外部スケジューラ（cron 等）との連携を容易に。
  - ログディレクトリ作成失敗時はファイルハンドラを無効化しても起動継続するように。

### Fixed
- 環境変数の数値パースや閾値読み取り時に不正値が与えられた場合、適切にフォールバック・警告出力する処理を追加（例: MONITOR_POLL_INTERVAL の不正値でデフォルトにフォールバック）。
- process_priority の未サポート OS / 権限不足時の例外を捕捉して警告でスキップするようにし、起動失敗を防止。

### Notes
- 一部モジュール（例: research/factor_research.py）は実装途中でファイル末尾が切れている箇所があり、今後の拡張が予定されています。
- 本リリースは初期実装であり、多くの値（閾値、デフォルト値、lot_size 等）は将来のチューニング対象です。
- 本番運用時は .env の取り扱い（機密情報の管理）や KABUSYS_ENV の設定に十分注意してください（validate_config の live ガードも参照）。

---

（以降のリリースでは、セマンティックバージョニングに従い Breaking / Added / Changed / Fixed を記録してください。）
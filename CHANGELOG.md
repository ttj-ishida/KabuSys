# Keep a Changelog — 変更履歴

この CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートと完全に一致しない可能性がありますので、参考情報としてご利用ください。

全般的なルール: 重要度の高い変更は大分類（Added / Changed / Fixed / Deprecated / Removed / Security）にまとめています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-18

### Added
- 基本機能群の初期実装
  - 日本株自動売買システム「KabuSys」のモジュール群を追加。
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。

- 実行用起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて本番/ペーパートレード用 DB を切り替え（paper_trading では専用 SQLite を使用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / Reconciler / RiskManager を組み立てて ExecutionEngine を起動。
    - エンジンは別スレッドで実行し、 data/stop_requested.flag により安全に停止可能。
    - 実行時の pid ファイル管理（data/execution.pid を使用）。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を参照して監視テーブルを初期化。

- 設定管理 / 初期化 / 検証ツール
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml）。
    - .env 自動読み込み（.env → .env.local の順、OS 環境変数は保護）。
    - export 形式、クォートやエスケープ、インラインコメントに対応した .env パーサ。
    - Settings クラスで各種設定値（DB パス、KABUSYS_ENV, PAPER_FILL_MODE 等）をプロパティとして提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。

  - config_setup.py: .env 対話式ウィザードを追加。
    - 対話形式で .env を作成 / 更新。秘密項目はマスク表示。
    - .env ファイルのテンプレート書き出し機能。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live に対する追加ガードを実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder
    - buy シグナルから候補選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存保有を元に上限を超えるセクターの新規候補を除外）。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）を提供。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap のスケーリング、cost_buffer を考慮した保守的なコスト見積と残差処理を実装。

- リサーチ / ファクター計算（基盤）
  - research.factor_research の骨格実装（モメンタム・MA200・ATR 等の計算方針・定数を定義）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順をサポート。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice 値対応）と CPU affinity 設定関数を追加。
    - アクセス権限不足や未対応プラットフォームは警告でスキップ。

- モニタリング用 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出し、監視テーブルが存在することを保証する処理を追加（冪等）。

- Paper Trading 用ツール
  - tools/paper_verification_report.py
    - ペーパートレーディングの検証レポート生成ツールを追加。
    - システム稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計し PASS/FAIL 判定を行う。
    - デフォルトしきい値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - --from / --to / --db オプションをサポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- ロギング周りの堅牢化
  - ログディレクトリ作成に失敗した場合でもコンソールログは必ず利用するようにし、ファイルハンドラ生成エラーはワーニングでスキップするように設計。

- .env パースの堅牢化
  - export 形式、クォート内のバックスラッシュエスケープ、インラインコメント取り扱いなどを考慮。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 機密情報の扱い
  - config_setup の対話で秘密項目はマスク表示（出力時は ****）。
  - Settings._require により必須環境変数未設定時にエラーを投げるため、起動前に明示的に環境変数の管理が必要。

---

注記（推測）:
- ExecutionEngine / BrokerClientFactory / OrderManager 等の詳細な実装（発注ロジック、API 呼び出しの具体的挙動）は本 CHANGELOG のソースコード抜粋では確認できないため、ここには含めていません。
- validate_config では PyYAML 未インストール時に YAML 検証をスキップする挙動があり、環境によっては警告が出ます。
- run_monitoring/run_execution は stop フラグ（data/stop_requested.flag）を用いた外部停止制御を採用しており、運用上の Kill Switch／PID 管理を意識した設計になっています。

もし実際の変更履歴（コミットログなど）を提供いただければ、より正確で詳細な CHANGELOG を生成できます。
# CHANGELOG

すべての重要な変更点を記録します。このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: 修正（バグ修正や堅牢性向上）
- NOTE: 実装・設計上の重要メモ

## [0.1.0] - 2026-04-22

### Added
- 全体
  - 初期リリース。日本株自動売買システム "KabuSys" のコアユーティリティ・実行スクリプト・ポートフォリオ構築ロジック・検証ツール群を収録。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用する実装。
    - BrokerClientFactory によるブローカークライアント生成。
    - エンジンをスレッドで起動し、data/stop_requested.flag による停止検知と安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定し pid ファイル管理を行う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で上書き可能。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（監視は本番データを参照する方針）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt もハンドル。

- 設定管理 / ウィザード / 検証
  - config.py:
    - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml 基準）。
    - .env / .env.local の読み込み順序を実装（OS 環境変数を保護して上書き制御）。
    - .env 行パーサーは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントなどに対応。
    - Settings クラスで環境変数の取得・検証（必須キー、PAPER_FILL_MODE の検証、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、各種パスの Path 変換など）を提供。
  - config_setup.py:
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - デフォルト値、選択肢、シークレット入力、既存 .env 読み込みの再利用をサポート。
    - .env のテンプレート出力（コミット NG の注意書き等を含む）。
  - validate_config.py:
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML 未インストール時は警告）などを実施。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - 統一ログ設定ヘルパーを追加。
    - stdout への StreamHandler と 日次ローテートする TimedRotatingFileHandler（既定 logs/<app_name>.log）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみで継続する安全処理を実装。
  - utils/process_priority.py:
    - クロスプラットフォームでのプロセス優先度設定機能を追加（Windows の優先度クラス / POSIX の nice 値に対応）。
    - CPU affinity を設定する set_cpu_affinity() を追加（最初の N コアに固定する）。
    - 権限や未対応 OS、API の欠如に対する安全なフォールバックと警告ログを実装。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - 売買候補の選択（select_candidates）および等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア合計が 0 の場合は等配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py:
    - セクター集中制限適用（apply_sector_cap）実装。既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外。
    - レジーム（bull/neutral/bear）に応じた投下資金乗数 calc_regime_multiplier を実装（既知値以外は 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - 各銘柄の発注株数計算 calc_position_sizes を実装。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウンと残差処理）を実装。
    - cost_buffer（手数料・スリッページ推定）を導入して保守的見積りを行う。
    - 価格欠損や非正の価格に対するスキップ・ログ出力に対応。

- 解析 / 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（P95 を含む）などを算出し、基準値に基づく PASS/FAIL を出力。
    - P95 計算、日付フィルタ（ISO8601 UTC 文字列）、DB 存在チェックなどを実装。
    - 閾値（稼働率 99% 等）はファイル内に定義しているため容易に調整可能。

- 研究用モジュール（初期実装）
  - research/factor_research.py:
    - ファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity の設計記載）。
    - DuckDB 接続を受けて prices_daily / raw_financials を用いる方針を明記。
    - モメンタム計算関数の開始（calc_momentum の定義とドキュメント）を追加（実装は続く）。

### Changed
- 特になし（初期リリース）

### Fixed / Hardened
- .env ロードとパース
  - .env の行パーサーを強化し、export プレフィックス・クォート／エスケープ・インラインコメントなどの取り扱いを改善。
  - .env 自動ロードで OS 環境変数を保護する protected セットを導入し、意図しない上書きを防止。
- ロギング
  - ログディレクトリ作成に失敗した場合のフォールバック処理を追加（stdout のみで継続し、例外で起動が止まらないように）。
- プロセス制御
  - set_process_priority と set_cpu_affinity は権限不足や非対応プラットフォームで安全に失敗し、警告ログを出すように改良。

### NOTE
- 監視（monitoring）設計
  - run_monitoring は Monitoring 用 DB 初期化（init_monitoring_db）と duckdb 接続を行うが、監視は常に本番用 sqlite_path を参照するため、運用時は監視 DB のパス設定に注意すること（意図的な設計）。
- Paper Trading と本番 DB の分離
  - run_execution は paper_trading モード時に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全に分離する設計になっている。
- research/factor_research は今後の拡張予定
  - calc_momentum 等はいくつかの詳細実装が続く見込み（スキャンレンジや欠測値ハンドリング等の実装が必要）。

---

今後の予定（未実装 / 優先度の高い作業）
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity の実装とテスト）
- ExecutionEngine / RiskManager / Reconciler 等の統合テスト・エンドツーエンド検証
- ログやメトリクスの追加（Prometheus export 等）
- 銘柄ごとの単元株情報をデータベースに持たせ、position_sizing の lot_size を銘柄別に対応する拡張

（この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴と差異がある場合は、適宜修正してください。）
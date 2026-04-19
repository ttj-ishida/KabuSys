# Changelog

すべての重要な変更は「Keep a Changelog」規約に従って記載しています。  
フォーマット：### Added / Changed / Fixed / Removed / Security

## [0.1.0] - 2026-04-19

### Added
- 初回リリース。KabuSys の基礎機能群を追加。
- 実行エントリ / サービス
  - run_execution.py: 実行エンジン起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に MockBrokerClient を使い、Paper Trading 用 DB（デフォルト: data/paper_trading.db）を用いる仕組みを実装。
    - プロセス優先度を高く設定して起動（process_priority ユーティリティ利用）。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理をサポート。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きをサポート（デフォルト 60 秒）。
    - 監視用 DB の初期化（init_monitoring_db）と DuckDB 接続を行う。
    - 停止フラグ検知でループを安全に終了。
- 設定管理
  - config.py: 環境変数 / .env ファイルの自動読み込み・設定取得クラス（Settings）を追加。
    - プロジェクトルートを .git / pyproject.toml から探索して .env / .env.local を自動読み込み（無効化可）。
    - .env の行パースを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント取扱いなど）。
    - 各種設定プロパティ（DB パス、Paper Trading 用設定、監視しきい値、ログレベル、環境種別検証等）を提供。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
- 設定ユーティリティ CLI
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML 利用可）。
    - --strict モードで警告を失敗扱いにするオプションを提供。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: 銘柄選定 (select_candidates)、等分配/スコア重み (calc_equal_weights / calc_score_weights) を実装。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。
  - portfolio.position_sizing: position sizing（risk_based / equal / score）、lot 単位丸め、aggregate cap スケーリング等を実装。
  - portfolio パッケージのエクスポートを追加。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートされたファイルハンドラ（TimedRotatingFileHandler、既定 logs/）をルートロガーに設定。
    - 既存ハンドラのクリア、レベル解決（引数 > 環境変数 > デフォルト）やログディレクトリ作成のフォールバック処理を実装。
  - utils.process_priority: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定関数を追加。
    - 権限不足や未サポート環境時の安全なフォールバック（警告出力）を実装。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite を集計して検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（fill / send）、リスク却下数、レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定を行う。
    - デフォルト DB パスと --from/--to/--db オプションにより期間・DB を指定可能。
    - 一連の閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）を定義。
- 研究用ファクター計算基盤
  - research.factor_research: DuckDB 接続を受けるファクター計算モジュールの骨子を追加（モメンタム / MA200 / ATR / 流動性等の算出を想定）。 （現状一部実装中）

### Changed
- 起動スクリプト関連の設計決定
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する仕様を明記（監視 DB と実行 DB の分離に関する設計判断を反映）。
  - run_execution は paper_trading 環境時に DB を完全に分離して使用（settings.paper_sqlite_path）。
- .env 読み込みの優先度と保護
  - OS 環境変数を保護するため .env ロード時の protected set を導入（.env.local の override が OS 環境変数を上書きしない挙動）。
- ログ設定の堅牢化
  - ログディレクトリ作成に失敗した場合、ファイルハンドラ作成をスキップしてコンソールのみで継続する動作を導入。
- process_priority の安全化
  - サポート対象 OS の判定と例外ハンドリングを強化し、権限不足時に警告を出して処理を続行するように変更。

### Fixed
- .env パーサーの改善により以下の問題を回避
  - export プレフィックス付き行を正しく扱うよう修正。
  - クォート内のバックスラッシュエスケープやインラインコメント処理に対応（これまで誤読していたケースを修正）。
- 複数起動スクリプトでの DB 接続後クローズ処理を明示的に実行するようにしてリソースリークのリスクを低減。

### Notes / Misc
- パッケージバージョンは __version__ = "0.1.0"。
- 一部モジュール（research.factor_research）は実装中の箇所があり、今後のリリースで完成・最適化を予定。
- 今後の改善候補:
  - position_sizing の銘柄ごとの lot_size 対応（stocks マスタの導入）。
  - apply_sector_cap の price 欠損時のフォールバックロジック（前日終値等）。
  - validate_config での YAML パースをさらに厳密にする（スキーマ検証など）。

以上。必要であれば、各変更点についてより詳細な説明（該当ファイル・関数ごとの変更差分推定）を出力します。どのレベルの詳細が必要か教えてください。
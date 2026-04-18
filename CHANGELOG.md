# Changelog

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]
- 今後の作業予定:
  - research/factor_research.py の完全実装（モメンタム等ファクター計算の続き）
  - テスト・ドキュメントの整備、例外処理の追加強化
  - 実運用向けの監視アラート送信（LINE 等）の統合強化

## [0.1.0] - 2026-04-18

### Added
- 初期リリース: KabuSys 自動売買システムの基本コンポーネントを追加。
  - 実行関連
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory により実稼働／モックブローカーを切り替え可能。
      - ExecutionEngine の起動・停止制御（PID ファイル・停止フラグ対応）、スレッドでの実行監視を実装。
      - RiskManager（RiskConfig）と Reconciler、OrderManager、OrderRepository の組み立てと連携を実装。
  - 監視関連
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用し、監視 DB の初期化を行う。
      - stop_requested.flag による外部停止、KeyboardInterrupt の優雅な終了、例外発生時のログ捕捉を実装。
  - 設定管理
    - config.py: Settings クラスによる環境変数・設定値の集中管理を追加。  
      - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）、.env/.env.local のロード順制御。
      - 環境変数の必須チェック（_require）、各種デフォルト値・検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。
      - paper_trading 用の paper_sqlite_path、pid/kill フラグパス、しきい値設定（CPU/MEM/DISK）を提供。
    - config_setup.py: 対話式 .env 作成ウィザードを追加（.env の生成・更新、秘密値マスク表示、保存確認）。  
      - .env に対して「絶対に Git にコミットしないこと」を明示するテンプレート出力。
    - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプション対応。
      - 必須環境変数・KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在確認、PyYAML があれば YAML のパース検証を実施。
      - 本番環境 guard（LINE 未設定時や KILL_FLAG_CLEAR_ON_START の警告）を追加。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py:
      - select_candidates, calc_equal_weights, calc_score_weights を実装（スコア加重、同点タイブレーク等の仕様を明記）。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター集中を抑制するフィルタ実装（売却予定銘柄を考慮、"unknown" セクターは除外しない挙動）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバック。
    - portfolio/position_sizing.py:
      - calc_position_sizes: risk_based / equal / score の配分方法を実装。単元（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer を考慮したスケールダウン／再配分ロジックを実装。
  - ユーティリティ
    - utils/logging_setup.py:
      - 統一的なログ設定ユーティリティを提供。stdout StreamHandler と TimedRotatingFileHandler（日次・30日分保持）をルートロガーに設定。
      - LOG_DIR 作成失敗時のフォールバック（コンソールのみ）をサポート。
      - ログレベル解決順（引数→環境変数→デフォルト）とログディレクトリ解決順を定義。
    - utils/process_priority.py:
      - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice）、CPU affinity 設定を提供。権限不足等は警告でスキップ。
  - ツール
    - tools/paper_verification_report.py:
      - ペーパートレード DB を解析して検証レポートを生成する CLI を追加。稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を算出し PASS/FAIL を判定する。
      - デフォルトパスは data/paper_trading.db、期間フィルタ（--from/--to）対応。
  - リサーチ（骨組み）
    - research/factor_research.py（部分実装）:
      - DuckDB を用いたファクター計算の枠組み（モメンタム等）を用意。営業日ベースの窓長や ATR/VOLUME 等の定義を含む。実装は途中（ファイル末尾で切れているが設計方針と定数が整備済み）。

### Changed
- なし（初期バージョンのため新規追加中心）。

### Fixed
- 環境変数パーサの堅牢化（config.py）
  - .env パースで export プレフィックス・クォート文字列中のバックスラッシュエスケープ・インラインコメント処理などを適切に扱う実装により、より正確に .env をロード可能に。
  - _load_env_file で既存 OS 環境変数を保護する protected パラメータを導入（.env.local による上書きでも OS 環境変数は上書きされない）。
- ロギング周りの耐障害性向上（logging_setup.py）
  - ログディレクトリ作成失敗時にファイルハンドラをスキップしてコンソール出力のみで継続するフォールバックを実装。
- 実行・監視プロセスの安全終了制御
  - stop_requested.flag / kill.flag / PID ファイルを使った外部停止制御、KeyboardInterrupt ハンドリングを整備。
- position_sizing のスケールダウンロジック
  - aggregate cap により総コストが available_cash を超える場合のスケールと lot_size 単位での端数処理を実装し、残余キャッシュを用いた再配分を行うことで分配の安定性を改善。

### Security
- config_setup.py の .env テンプレートに「絶対に Git にコミットしないこと」を明記。
- Settings._require により必須のシークレット環境変数が未設定の場合は明示的に失敗させ、秘密情報の未設定を見落とさないように。

### Internal / Other
- DuckDB と SQLite の併用設計:
  - DuckDB を分析用（prices_daily / raw_financials 等）に、SQLite を監視・発注履歴用に使い分ける設計。
  - init_monitoring_db 呼び出しで監視テーブルの存在を冪等に保証。
- パッケージメタ情報:
  - __version__ = "0.1.0" を設定。
  - モジュール構成と __all__ によるエクスポートを整理（portfolio パッケージ等）。

---

※ 本 CHANGELOG はコードから推測して作成した初期の変更履歴です。実際のコミットログや設計文書が存在する場合はそれに基づき追記・修正してください。
# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングに従います。

## [Unreleased]
- （今後の変更記載用）

## [0.1.0] - 2026-04-25

### Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys、バージョン `0.1.0`（src/kabusys/__init__.py）
- 環境/設定管理
  - Settings クラスを実装（src/kabusys/config.py）
    - 環境変数の取得、型変換、妥当性チェックを提供
    - 各種パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH など）、API トークン、運用モード（KABUSYS_ENV）等をプロパティで取得可能
    - PAPER_FILL_MODE の検証や env 値の妥当性判定（KABUSYS_ENV / LOG_LEVEL の許容値チェック）
  - .env 自動読み込み機能を実装
    - プロジェクトルート（.git または pyproject.toml）を基準に自動で .env / .env.local を読み込む
    - OS 環境変数を保護（上書き不可）し、`.env.local` は `.env` を上書きする仕組み
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - .env パーサーの改善
    - export PREFIX、クォートされた値、エスケープシーケンス、インラインコメントの扱いに対応（_parse_env_line）
- 設定支援ツール / 検証ツール
  - 対話式環境設定ウィザード（python -m kabusys.config_setup）
    - .env の初期作成・更新を支援する CLI（項目定義、既存値の読み込み、シークレットのマスク表示）
  - 設定検証 CLI（python -m kabusys.validate_config）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 任意）
    - --strict オプションで警告をエラー扱いにできる
- 実行用スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動フロー（プロセス優先度設定、DB 接続、Broker の生成、依存コンポーネント組み立て、スレッド起動・停止管理）
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、本番 DB と分離
    - 停止フラグ（data/stop_requested.flag）と PID ファイルの扱い
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor をポーリング実行。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する設計
    - 停止フラグの検知と安全終了、例外発生時のログ出力を実装
- ロギング & プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定
    - LOG_DIR/LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバックを実装
    - 標準出力は stdout を利用（cron 等でのリダイレクト対応）
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応する簡易インターフェースを提供
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。権限不足時は警告でフォールバック
- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選定
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア合計が 0 の場合はフォールバック）
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションを基に同一セクター上限チェックと候補除外
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をマップ）
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method に対応
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウンおよび残余処理（remaining cash で lot 単位の追加配分）
    - cost_buffer（手数料・スリッページ見積り）を考慮
- 研究モジュール（ファクター計算）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）
    - Momentum/Value/Volatility/Liquidity 等の計算方針・定数を定義
    - calc_momentum の骨組み（DuckDB 経由で prices_daily を参照する方針）を追加（実装途中）
- ツール
  - ペーパートレーディング検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
    - SQLite（paper_trading）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計し PASS/FAIL 判定でレポート出力
    - 日付フィルタ、コマンドライン引数（--from / --to / --db）に対応

### Changed
- ログ出力の標準化
  - すべての起動スクリプト・ユーティリティで logging_setup.setup_logging を利用することでログ設定の一元化を実現
- DB 接続の扱い
  - 監視系は環境にかかわらず本番 sqlite_path を参照する仕様を明確化
  - 実行系は paper_trading の場合に専用 SQLite を使用する（paper_sqlite_path）

### Fixed
- 環境変数パースの堅牢化
  - quotes / escape / export / インラインコメントの扱いを改善して、.env の多様な記法に対応
- MONITOR_POLL_INTERVAL の不正値対策
  - 0以下や非整数を検出した場合は警告を出してデフォルト（60 秒）にフォールバックする仕様を追加

### Known issues / Notes
- src/kabusys/research/factor_research.py の calc_momentum はファイル末尾で未完の形跡（途中で切れている）。ファクター計算ロジックは引き続き実装・テストが必要。
- 一部の TODO コメント（例: price 欠損時のフォールバック価格、銘柄ごとの lot_size 拡張など）が残っているため、将来的な拡張ポイントあり。
- 実行時の BrokerClientFactory / ExecutionEngine など外部依存（kabuステーション API、モックブローカー）の振る舞いと単体テストは別途整備が必要。

---

参考:
- 主なエントリポイント:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report
  - 実行/監視スクリプト: src/kabusys/run_execution.py / src/kabusys/run_monitoring.py

（以上）
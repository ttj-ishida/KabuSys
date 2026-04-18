# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」準拠です。  

次の規約に従います:  
- すべての変更はセクション（Added / Changed / Fixed / Removed / Security）に分類しています。  
- バージョンはパッケージ内の __version__（0.1.0）に合わせています。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-18
初回リリース。KabuSys の基本的な自動売買・検証・運用補助ツール群を実装しました。

### Added
- 実行・監視用の起動スクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでのセッション実行、外部停止フラグ（data/stop_requested.flag）による安全停止をサポート。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループのエントリポイントを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はフォールバックして警告出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用するよう設計。
    - 停止フラグ検知によるループ終了、例外発生時のロギングと継続処理を実装。

- 環境設定・読み込みまわりを強化
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルートの検出 .git / pyproject.toml 基準）。
    - .env のパースロジックを実装（export プレフィックス、クォート内エスケープ、インラインコメントの扱い等に対応）。
    - Settings クラスでアプリケーション設定を統一的に提供（DB パス、PID/kill flag、閾値、環境判定、paper_trading 用パスなど）。
    - PAPER_FILL_MODE の値検証を追加（valid: instant|partial|never|reject）。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を実装。
    - シークレット値のマスク表示、選択肢／デフォルト表示、確認プロンプト、ファイル書き込み機能をサポート。

- 設定検証 CLI を追加
  - src/kabusys/validate_config.py
    - 必須環境変数チェック・KABUSYS_ENV 検証・LOG_LEVEL 検証・DB パスの親ディレクトリ存在チェック・config/*.yaml ファイル存在／パースチェック（PyYAML が存在する場合）・本番環境用の追加ガードを実装。
    - --strict オプションで警告も失敗扱いにするモードを追加。

- ログ/プロセスユーティリティを追加
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定する共通関数を追加。
    - LOG_DIR/LOG_LEVEL の解決順と、ファイルハンドラ作成失敗時のフォールバック処理を実装。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（high/normal/low）を追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足・未サポート環境でのフォールバック（警告ログ出力）に対応。

- ポートフォリオ構築・リスク調整・ポジション決定ロジックを追加
  - src/kabusys/portfolio/portfolio_builder.py
    - BUY シグナルの候補抽出 select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合はフォールバックで等配分）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター別時価計算、上限超過セクターの候補除外。'unknown' セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear、未知レジームは 1.0 でフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash）適用、cost_buffer を考慮した保守的見積り、スケールダウン時の端数処理（fractional remainder に基づく再配分）などを実装。

- 研究用ファクター計算の雛形を追加
  - src/kabusys/research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 指標の設計方針・定数を定義。（prices_daily / raw_financials を想定した DuckDB ベースの計算設計。）
    - モメンタム計算関数 calc_momentum の枠組みの追加（実装途中の箇所あり）。

- ペーパートレード検証レポート生成ツールを追加
  - src/kabusys/tools/paper_verification_report.py
    - SQLite（paper_trading DB）から稼働率・注文成功率・送信率・レイテンシなどを集計し、閾値（稼働率 99% 等）に基づいて PASS/FAIL 判定するレポート生成 CLI を実装。
    - P95 計算、日付フィルタ、各種 SQL 集計・欠損ハンドリング、出力フォーマットを実装。

- パッケージ初期化値を設定
  - src/kabusys/__init__.py: __version__ = "0.1.0" を追加。

### Changed
- ログの標準出力を stderr ではなく stdout に統一
  - Cron / Task Scheduler でのリダイレクト運用を想定し、StreamHandler を stdout に設定。

- .env の自動ロード仕様
  - OS 環境変数を保護する protected 機構を導入して .env.local を上書き可能にしつつ OS 既存値を上書きしないように実装。

### Fixed
- 環境変数の検証とフォールバックの堅牢化
  - MONITOR_POLL_INTERVAL の不正値（0 や負値、非整数）を検出して警告を出しデフォルトにフォールバック。
  - PAPER_FILL_MODE の不正値に対する早期エラー報告を追加。
  - process_priority の未対応 OS / 権限不足での例外を捕捉し、ログで警告して処理継続するように修正。

- DB 初期化の冪等性保証
  - init_monitoring_db() 呼び出しにより、monitoring 用テーブルの存在を保証。複数起動時でも安全に初期化できるように配慮。

### Removed
- 該当なし

### Security
- 該当なし

---

注:
- 各モジュール（特に research モジュールや ExecutionEngine の内部実装）は、本リリースで基盤的な設計と多くのユーティリティを導入しましたが、運用・テストに合わせた追加チューニングや細かなエラー処理、外部 API の実装（ブローカー接続等）が必要です。README / ドキュメントと運用手順は別途整備してください。
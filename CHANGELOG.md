# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※この CHANGELOG はコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回リリース。システムのコア機能（環境設定、起動スクリプト、ログ設定、プロセス優先度、ポートフォリオ構築、位置決め、リスク調整、ペーパートレード検証など）を含む。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys/__init__.py に __version__ = "0.1.0" を定義）。
  - DuckDB / SQLite を用いたデータ格納を前提とするアプリケーション構成を導入。

- 環境設定・検証
  - Settings クラス（src/kabusys/config.py）を追加。環境変数からアプリケーション設定を取得・検証するプロパティ（J-Quants トークン、kabu API パスワード、データベースパス、Paper Trading 用設定、監視しきい値など）を提供。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーションを実装。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - .env 自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml から検出）。.env → .env.local の優先順位と OS 環境変数保護をサポート。
    - 環境変数の読み込みで export KEY=val、クォートやエスケープを正しく処理するパーサを実装。

  - 設定ウィザード CLI（src/kabusys/config_setup.py）を追加。
    - 対話式で .env を生成・更新可能。
    - 秘密項目はマスク表示、デフォルトや選択肢の提示、保存前の確認プロンプトを実装。
    - デフォルトで .env を "絶対に Git にコミットしない" と明記。

  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パースチェック（PyYAML が無ければスキップ）を実装。
    - --strict オプションで警告を FAIL として扱える。

- 起動スクリプト / 実行制御
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite（data/paper_trading.db をデフォルト）に接続して本番 DB と分離。
    - BrokerClientFactory を利用して実ブローカー / MockBroker を切替。
    - OrderManager / OrderRepository / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。data/stop_requested.flag で停止制御、PID ファイル出力をサポート。
    - RiskConfig のデフォルト値（max_position_pct 等）を設定し、初期ポートフォリオ値は broker.get_available_cash() から取得。

  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視プロセスは環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化。
    - data/stop_requested.flag を検知してループを終了。SystemMonitor.check_once() の例外はログに記録して次回ポーリングへ継続。

- ロギング・プロセス制御ユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保管）を設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
    - ログレベル決定ルール（引数 > 環境変数 > デフォルト）およびログディレクトリ解決ルールを実装。

  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を考慮した set_process_priority(level) を提供（high/normal/low）。権限不足や未対応 OS は警告してスキップ。
    - set_cpu_affinity(cpu_count) を提供（指定が None の場合は何もしない）。権限不足時は警告してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）を追加。
    - select_candidates: スコア降順で候補を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア重み配分（全スコアが0なら等配分にフォールバック）。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）を追加。
    - apply_sector_cap: 既存保有に基づくセクター集中上限（max_sector_pct）を評価し、上限超過セクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告して 1.0 にフォールバック）。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）を追加。
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて各銘柄の発注株数を計算。単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を用いた保守的なコスト見積り、余剰配分ロジックを実装。

  - portfolio パッケージのエクスポート（src/kabusys/portfolio/__init__.py）で主要関数を再公開。

- 研究／ファクター計算
  - factor_research（src/kabusys/research/factor_research.py）スケルトンを追加（モメンタム、ボラティリティ、バリュー等のファクター計算を想定）。
    - calc_momentum が定義され始めており、各種期間 (1M/3M/6M、MA200) を計算する仕様をコメントで明記（実装途中の可能性あり）。

- ツール
  - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）を追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH で指定可）を読み、稼働率、注文成功率、送信率、P95 レイテンシなどを集計してレポートを標準出力に出力。
    - パス/フェイル閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - P95 計算、期間フィルタ、データ存在チェック、例外時のフォールバック処理を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details（補足）
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされる設計のため、パッケージ配布後も安全に動作することを意図している。
- run_monitoring は監視用 DB テーブルの初期化を保証するため init_monitoring_db を呼び出す実装がある（冪等）。
- run_execution は paper_trading モード時に本番 DB と完全分離されることを明示している（データ汚染回避）。
- ログ出力は stdout を起点にしているため、cron やシェル起動時に stdout/stderr を一本化する運用に配慮している。
- process_priority の設定は権限や OS に依存する操作のため失敗時に安全にスキップする実装になっている。

---

今後のリリースノートでは、個々のモジュール（ExecutionEngine / SystemMonitor / BrokerClient 等）の詳細な変更・バグ修正や、factor_research の完全実装、テストカバレッジの追加、設定検証の強化などを追記してください。
# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載します。  
日付はコードベースから推測した作成日として 2026-04-19 を使用しています。

フォーマット:
- Unreleased: 今後の変更予定（コードから推測）
- [0.1.0] - 2026-04-19: 初期リリース（コードベースの現状を反映）

## [Unreleased]

### Added
- 監視・実行の運用面での改善予定
  - 監視ループのポーリング間隔を環境変数で動的に変更できる機能（MONITOR_POLL_INTERVAL）の拡張検討
  - ログ出力先・ログローテーションの設定の強化（例: リモートロギング対応）
- テスト補助のための設定ロード制御のドキュメント強化（KABUSYS_DISABLE_AUTO_ENV_LOAD の利用法の明示化）
- research/factor_research の完成（現在は途中まで実装。Momentum 等ファクター計算の残り実装と単体テスト追加予定）

### Changed
- process_priority のロバスト化（現在は psutil を用いているが、より細かい OS/権限ハンドリングの改善を検討）
- paper trading と本番 DB の扱いに関するドキュメント整備

### Fixed
- なし（今後の不具合レポートに対処予定）

---

## [0.1.0] - 2026-04-19

初回公開リリース。以下はコードベースから推測できる主要な機能と実装内容です。

### Added
- 実行・監視エントリポイント
  - run_execution.py
    - ExecutionEngine を起動する CLI ランチャー。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動・監視。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) による制御処理を実装。
    - プロセス優先度を High に設定して起動（set_process_priority を使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用している点に注意。
    - 停止フラグ (data/stop_requested.flag) による終了判定を実装。
    - duckdb 接続を併用。

- 設定管理・支援ツール
  - config.py
    - .env の自動読込（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env のパースは quote やエスケープ、インラインコメントを考慮した堅牢な実装。
    - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants / kabu API / DB パス / Paper Trading のモード検証など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject のみ許容）。
    - KABUSYS_ENV, LOG_LEVEL 等の検証ロジックを含む。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。
    - 秘匿値のマスク表示やデフォルトのサポート、確認プロンプトを実装。
  - validate_config.py
    - .env と config/*.yaml の整合性・必須環境変数を起動前に検証する CLI。
    - --strict オプションで警告を失敗扱いにできる。
    - PyYAML 未インストール時の graceful な扱い（YAML 内容検証をスキップ、警告を出力）。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティ。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - ログレベルおよびログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定（Windows の priority class / POSIX の nice）。
    - CPU affinity を指定コア数に固定する機能も提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合のフォールバック（等配分）を警告付きで実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。
    - calc_regime_multiplier は既知のレジーム（bull/neutral/bear）に対応、未知レジームは 1.0 でフォールバックして警告を出力。
    - apply_sector_cap は既存保有のセクター別エクスポージャを計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは制約対象外）。
  - portfolio/position_sizing.py
    - allocation_method に応じた株数決定（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、集計上限（available_cash）に基づくスケーリング（スケールダウン & 端数の再配分）を実装。
    - cost_buffer を用いた保守的なコスト見積りを考慮。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading の SQLite DB（デフォルト: data/paper_trading.db）から各種指標を集計し、検証レポートを標準出力に生成。
    - 指標: 稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（avg/max/P95）。
    - 判定基準（しきい値）を定義して PASS/FAIL を出力。
    - --from/--to/--db オプションに対応。

- research/factor_research.py
  - ファクター計算のための下地を実装（Momentum/MA/ATR/VOLUME 等の定数と関数骨格）。
  - DuckDB 接続を想定した設計。prices_daily / raw_financials テーブルを参照する仕様。
  - （ファイル末尾で実装が切れている箇所あり — 継続実装が必要）

### Changed
- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

### Fixed
- .env 読み込み時のエッジケース対応
  - export で始まる行、クォート内のエスケープ、インラインコメント処理などに対応。

### Deprecated
- なし

### Removed
- なし

### Security
- 秘匿値（トークン/パスワード）を .env に保存する運用を前提としているため、.env の Git へのコミット禁止を README コメントで明記（config_setup.py に注意書きあり）。

### Known issues / 注意事項
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」と説明コメントにあり、paper_trading 環境でも本番監視 DB を参照する設計になっているため、意図しないデータ書き込みや参照が生じる恐れがあります。運用時は設定を十分確認してください。
- portfolio/risk_adjustment.apply_sector_cap 内で price_map に価格が無い場合に 0.0 を使用することでエクスポージャが過少に見積もられる可能性がある旨の TODO コメントが残っています（将来的な前日終値などのフォールバック実装が推奨）。
- research/factor_research.py は途中で実装が切れているため、ファクター計算の完全実装およびユニットテストが必要です。
- process_priority/set_process_priority・set_cpu_affinity は権限や OS に依存するため、実行環境で権限不足により設定がスキップされる可能性があります（ログで警告される）。

---

Contributors: 推測に基づくため省略。実際の貢献者情報は Git のコミット履歴等から取得してください。
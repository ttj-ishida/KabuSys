# CHANGELOG

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
通常のセクション: Added, Changed, Fixed, Removed, Security。

※ 以下は提供されたコードベースから推測してまとめた変更履歴です（実装コメント・振る舞いに基づく要約）。

## [Unreleased]
- -  (なし)

## [0.1.0] - 2026-04-19
### Added
- 基本機能の初期実装（KabuSys v0.1.0）
  - 実行エントリスクリプト
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
      - KABUSYS_ENV に応じて paper_trading 用に専用の SQLite（data/paper_trading.db）を使用。
      - 起動前にプロセス優先度を "high" に設定。
      - BrokerClientFactory によりブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。停止フラグ（data/stop_requested.flag）検出時に安全に停止。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
      - 監視は環境に依らず本番用 sqlite_path を使用して監視テーブルを初期化。
      - stop フラグ検出でループ終了、例外はログに記録して次ポーリングへ継続。
  - 設定管理
    - config.py: .env の自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
      - export 形式・クォート/エスケープ・インラインコメント等に対応する堅牢な .env パーサを実装。
      - OS 環境変数を保護して上書き制御できる仕組みを導入。
      - Settings クラスを提供し、各種設定値・検証ロジック（env 値や PAPER_FILL_MODE の検証等）を実装。
    - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を実装。
      - デフォルト値、選択肢、シークレット入力の扱い、保存確認などを含む。
  - 設定検証
    - validate_config.py: .env と config/*.yaml を起動前に検証する CLI を実装。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML のパース検査（PyYAML 未インストール時は警告）等。
      - --strict オプションで警告も FAIL 扱いにできる。
  - ロギング・プロセス管理ユーティリティ
    - utils/logging_setup.py: 統一的ロギング設定を提供。
      - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。
      - 既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック（ファイル出力スキップ）を考慮。
    - utils/process_priority.py: クロスプラットフォームでプロセス優先度（および CPU affinity）を設定するユーティリティを追加。
      - Windows/Linux/macOS 等を吸収し、アクセス拒否や未実装 API に対するフォールバック処理を実装。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順、同点時は signal_rank の昇順でタイブレークして上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を提供。スコア合計が 0 の場合は等金額にフォールバックして warning を出力。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に新規候補を除外するロジック実装（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear）を提供。未知のレジームは warning を出して 1.0 にフォールバック。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
      - 単元（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に対するスケールダウン）、cost_buffer による保守的見積りなどのロジックを含む。
      - risk_based 方式では損切り幅と risk_pct を用いてポジションサイズを算出。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py: SQLite（paper_trading.db）から集計して検証レポートを生成する CLI を追加。
      - 稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（avg/max/P95）などの指標を算出。
      - 日付フィルタ（--from / --to）対応、閾値による PASS/FAIL 判定を行う。
  - リサーチモジュール（ファクター計算）
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム等の計算方針と定数を実装）。
      - prices_daily / raw_financials テーブルのみ参照してファクターを計算する設計。

### Changed
- 初期設計段階での堅牢性向上・安全策の導入
  - run_monitoring / run_execution で stop フラグを使った安全停止や例外ハンドリングを明示。
  - run_execution で paper_trading 環境を本番 DB と完全分離する仕様を明示。
  - logging_setup で既存ハンドラの二重追加を防止するためハンドラのクリアを実装。
  - config の自動読み込みで OS 側環境変数を保護する仕組み（protected set）を導入。

### Fixed
- 環境変数や設定読み込みに関する堅牢化
  - .env パーサでクォート内のバックスラッシュエスケープや inline コメントの扱いを改善。
  - MONITOR_POLL_INTERVAL の不正値（0 や負数、数字以外）に対するフォールバック処理を追加して time.sleep の例外を回避。

### Documentation
- 各モジュールに実装方針や使用例、引数説明を含む docstring を充実させた（config_setup, validate_config, logging_setup, portfolio.*, tools.* 等）。
- README 相当の使用法が各スクリプトのモジュール docstring と CLI ヘルプに追加されている。

### Known limitations / Notes
- research/factor_research.py はファクター計算の骨格と定数を実装しているが、ファイル末尾で関数定義が途中で切れている（実装継続の余地あり）。
- 一部の外部依存（例: PyYAML, psutil, duckdb）が環境にない場合はフォールバックや警告で動作するが、フル機能利用にはインストールが必要。
- position_sizing の将来的な拡張として銘柄別 lot_size（単元）対応を想定した TODO がある。

---

(注) 実際のリリースノート作成時は、コミット履歴やリリース日、影響範囲の詳細（データベーススキーマ変更、互換性ブレイク等）に基づいて更新してください。今回の CHANGELOG はコード内容からの推測に基づく要約です。
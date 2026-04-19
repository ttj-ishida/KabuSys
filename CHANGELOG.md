CHANGELOG
=========

すべての注目すべき変更をここに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）で記載
- 可能な限り実装の振る舞いや環境変数名等を明記

現在の最新バージョン
-------------------

## [Unreleased]

リリース前の変更や未確定の改善点をここに記載します。

リリース履歴
-----------

## [0.1.0] - 2026-04-19
初回公開リリース。本バージョンは自動売買システムのコアユーティリティ群、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール等の基盤実装を含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョン設定: kabusys.__version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルにより行う。
    - Monitoring は KABUSYS_ENV に依らず本番用 sqlite_path を使用する実装（監視データは分離しない設計）。
    - DuckDB と SQLite 両方の接続を確立し、監視 DB の初期化を行う。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て。
    - デフォルトの RiskConfig を設定し、ExecutionEngine をバックグラウンドスレッドで実行。停止フラグで安全に停止可能。
    - PID ファイル管理（data/execution.pid）に対応。

- 環境・設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env の自動ロード順: OS 環境 > .env > .env.local（.env.local は .env を上書き、ただし OS 環境は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - .env 行パーサが強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理に対応）。
    - Settings クラスを導入し、主要設定（DB パス、API トークン、PAPER_FILL_MODE、閾値、環境判定等）をプロパティ経由で取得できるようにした。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）とエラー処理を実装。
    - 環境値の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）およびフラグ判定ヘルパーを追加（is_live/is_paper/is_dev）。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - デフォルト値・選択肢・マスク入力（シークレット）に対応。
    - .env の読み書きロジック（既存値の再利用、ファイルにヘッダ付きで出力）を実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース確認（PyYAML 利用）等を行う。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - 共通ロギング初期化ユーティリティを追加。
    - stdout 出力の StreamHandler と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30 日保持）をルートロガーに設定。
    - LOG_DIR 環境変数や引数でログディレクトリを解決。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラの二重登録防止（再設定時に既存ハンドラを閉じて削除）。

  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加。
    - Windows / POSIX の両方に対応（Windows は psutil の優先度定数、POSIX は nice 値を使用）。失敗時は警告ログを出してスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装（権限不足や未サポート時はスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates) と重み計算 (calc_equal_weights, calc_score_weights) を実装。
    - スコア全0 の場合は等金額配分にフォールバックして警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクター別時価に基づき候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知値は 1.0 フォールバック）。

  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。
    - allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリング、コストバッファ考慮、残差配分ロジックを実装。
    - 価格欠損時のスキップやログ出力を含む堅牢化。

  - portfolio/__init__.py
    - 上記関数群をまとめてエクスポート。

- 解析/研究ユーティリティ（骨組み）
  - research/factor_research.py
    - ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。
    - DuckDB 接続を受け prices_daily / raw_financials を基に計算する設計。
    - モメンタム計算関数 calc_momentum の骨格を追加（実装途中の箇所あり）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、PASS/FAIL 判定を行うしきい値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - SQL クエリの例外捕捉（テーブル欠如時のフォールバック）を実装。

### Changed
- ログ出力の挙動を統一
  - すべての起動スクリプトは setup_logging を呼び出すように設計。
  - stdout に出力することで cron 等からのログリダイレクトに対応。

- .env 読み込みの保護
  - OS 環境変数は protected として .env/.env.local による上書きを防止。

### Fixed
- （設計上の改善）.env のパースにおける引用符とエスケープ処理を改善し、より堅牢に。

### Known issues / Notes
- research/factor_research.calc_momentum の実装は途中で切れている（ファイル末尾で未完成）。将来的にファクター計算の完全実装が必要。
- apply_sector_cap の価格欠損（price_map に値がない場合）は現状 0.0 として扱い、エクスポージャが過少見積りされる可能性がある旨を TODO コメントで残している。
- process_priority/set_cpu_affinity は権限不足やプラットフォーム未対応時にスキップする設計。運用環境で事前に権限・互換性を確認のこと。

ライセンスや貢献方法等はプロジェクトルートの別ファイル（README 等）を参照してください。

----- 
（注）本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のコミット履歴や過去バージョンとの差分が必要な場合は、Git のログやタグ情報を基に正確な CHANGELOG を生成してください。
# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

概要:
- 本リポジトリは日本株自動売買システム「KabuSys」の初期実装です。
- 主要コンポーネント: 実行エンジン、監視デーモン、設定管理・ウィザード、ポートフォリオ構築ユーティリティ、調査（ファクター）モジュール、ユーティリティ群、検証ツール等を含みます。

## [Unreleased]
- 開発中の変更はここに記載します。

## [0.1.0] - 2026-04-20
初回リリース。主要機能やユーティリティを実装しました。

### Added
- 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
  - ExecutionEngine をスレッドで起動し、停止フラグ（data/stop_requested.flag）で安全に停止可能。
  - 環境に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用する分離設計。
  - BrokerClientFactory によるブローカークライアント生成フローを導入。
  - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動ロジックを実装。
  - プロセス優先度を起動時に "high" に設定するフックを追加。

- 監視デーモン起動スクリプト (src/kabusys/run_monitoring.py)
  - SystemMonitor をポーリングループで定期実行（デフォルト 60 秒）。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。
  - 監視用 DB は環境に関わらず本番 sqlite_path を参照する設計（監視データは単一 DB に集約）。
  - 停止フラグファイル検出による安全終了、check_once() 内例外をログに記録してループ継続。

- 設定管理 (src/kabusys/config.py)
  - Settings クラスを実装し、環境変数から各種設定を取得。
  - .env / .env.local の自動読み込み（ルート探索: .git または pyproject.toml を基準）。OS 環境変数を保護するための上書き制御あり。
  - PAPER_FILL_MODE のバリデーション、有効値制限（instant/partial/never/reject）。
  - paper_trading 用 SQLite パス、PID / kill flag 等の各種パス、しきい値（CPU/MEM/DISK）などを管理。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを抑止可能。

- 設定検証 CLI (src/kabusys/validate_config.py)
  - .env と config/*.yaml の整合性チェック、必須環境変数チェック、パス存在チェック、Log Level の検証。
  - --strict オプションで警告を FAIL 扱いにする機能。
  - PyYAML 未インストール時に YAML チェックをスキップする柔軟性と警告出力。
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。

- 環境設定ウィザード CLI (src/kabusys/config_setup.py)
  - 対話式で .env の初期作成・更新を支援。シークレット項目はマスク表示して入力。
  - 標準的な設定項目群（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を用意。
  - .env の読み書きロジック（既存値の再利用、export 形式対応、ファイルヘッダ付き出力）。

- ポートフォリオ構築ライブラリ (src/kabusys/portfolio/)
  - portfolio_builder: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
  - risk_adjustment: セクター上限適用 (apply_sector_cap)、レジーム乗数 calc_regime_multiplier を実装。未知レジームに対するフォールバックと警告を含む。
  - position_sizing: position 数量算出 (calc_position_sizes)
    - risk_based / equal / score の割当方式に対応
    - 単元株（lot_size）での丸め、单銘柄上限・総投資上限（aggregate cap）のスケーリング、cost_buffer を考慮した保守的見積り
    - 価格欠損時のスキップやログ出力、残差に基づく追加配分ロジックを実装

- 研究用ファクター計算モジュール (src/kabusys/research/factor_research.py)
  - Momentum / Value / Volatility / Liquidity 等の計算方針と定数を定義。
  - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計（外部 API に依存しない）。
  - モメンタム計算関数の雛形（calc_momentum）などを導入（実装途中の関数あり）。

- ツール: Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
  - paper_trading の SQLite DB を解析してレポートを標準出力に生成。
  - 指標: 稼働率 (uptime)、注文成功率（fill率）、送信率、P95 レイテンシ、リスク却下数等を算出、閾値に基づく PASS/FAIL 判定。
  - 日付フィルタ、DB パス引数、空データやテーブル存在なしの堅牢な取り扱い。

- ロギング設定ユーティリティ (src/kabusys/utils/logging_setup.py)
  - setup_logging 関数を提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
  - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - stdout を使用することで cron 等の出力リダイレクトと親和性を高める。

- プロセス優先度・CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
  - Windows / POSIX の差を吸収してプロセス優先度設定を提供（set_process_priority）。
  - CPU ピン固定機能（set_cpu_affinity）を実装。
  - 権限不足や非対応環境では警告を出して安全にフォールバック。

- パッケージ情報 (src/kabusys/__init__.py)
  - バージョン __version__ = "0.1.0" を追加。

### Changed
- ログ出力の標準化:
  - すべての起動スクリプトは setup_logging を呼び出して統一したログ管理を行うように構成。
  - StreamHandler は stderr ではなく stdout を使用（cron/Task Scheduler 等でのリダイレクトを想定）。

- DB ハンドリング:
  - 監視プロセスは環境に関わらず監視用 sqlite_path を使用する設計（監視データは本番側 DB を想定）。

### Fixed
- 安全起動 / 停止振る舞い:
  - 実行エンジン・監視プロセス共に stop flag の検知で安全に終了するロジックを追加。
  - 監視ループ内で check_once() が例外を投げてもループを止めず、例外情報をログに残して次ポーリングに備える実装。

- 設定ファイルパーシングの堅牢化 (.env パーサー)
  - export プレフィックス対応、クォート内のエスケープ処理、行末コメントの取り扱いを改善。
  - 自動読み込み時に OS 環境変数を保護（.env.local の上書き制御を含む）。

- 設定検証の堅牢化:
  - config/*.yaml の存在チェックと PyYAML 未インストール時のフォールバック（警告出力）。
  - KABUSYS_ENV や LOG_LEVEL の不正値を検出してエラー/警告を出力。

- position_sizing の丸め・スケーリングロジック
  - lot_size 単位での丸め、aggregate cap 超過時のスケールダウンおよび残差を用いた追加割当の安定化。

### Security
- config_setup にてシークレット値（J-Quants トークン、kabuAPI パスワード）をマスク表示し、.env ファイルを Git にコミットしないよう明示。
- Settings._require による必須環境変数未設定時の早期検出（ValueError）を実装。

### Notes / Known limitations
- research.factor_research の一部関数は実装途中（例えば calc_momentum の途中でファイルが切れています）。実データ適用前に追加実装とバリデーションが必要です。
- position_sizing は現状 lot_size を全銘柄共通と仮定。将来的に銘柄別 lot_size を導入する設計を想定（TODO コメントあり）。
- process_priority / cpu_affinity は実行環境の権限や OS に依存するため、失敗時はログに警告を出してスキップするフォールバックを行います。
- monitor は常に本番 sqlite_path を使う設計だが、必要に応じて設定で分離できるよう拡張を検討してください。

---

この CHANGELOG はソースコードから仕様・挙動を推測して作成しています。実際の変更履歴（コミット履歴）に基づくものではありません。必要であれば差分や追加情報に合わせて更新してください。
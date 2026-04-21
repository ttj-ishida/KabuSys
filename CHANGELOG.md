# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルにはコードベース（src/kabusys 以下）から推測される主要な変更点・機能追加を記載しています。

## [Unreleased]

### Added
- なし（次回リリースへ向けての差分はここに記載されます）。

---

## [0.1.0] - 2026-04-21

初回リリース。自動売買システム KabuSys の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 Mock を利用し、データは paper_trading.db に分離。
    - スレッドで ExecutionEngine をデーモン実行し、data/stop_requested.flag による外部停止に対応。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグの検知、例外時のログ出力、DB 接続のクローズ処理を実装。

- 設定管理およびウィザード
  - Settings クラス（src/kabusys/config.py）を実装。
    - .env 自動ロード（プロジェクトルートを .git / pyproject.toml から検出）と、OS 環境変数保護の仕組みを実装。
    - 各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DB パス等）の取得・検証ロジックを提供。
    - PAPER_FILL_MODE（ペーパートレードの約定モード）のバリデーション。
  - 対話式 .env 作成/更新ウィザードを追加（src/kabusys/config_setup.py）。
    - 秘匿項目はマスク表示、既存 .env の読込・既存値再利用、最終確認後に .env を作成。

- 設定検証ツール
  - validate_config CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認、config/*.yaml の存在チェックと（PyYAML があれば）パース検証。
    - --strict オプションで警告もエラー扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 環境変数、LOG_LEVEL に対応。ファイル出力の失敗時はコンソール出力にフォールバック。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収し psutil を使って優先度設定。アクセス権限や未対応 OS の場合は安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - 候補のスコア順ソート（タイブレーク: signal_rank）select_candidates
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（スコア全零時は等配分にフォールバック）
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは 1.0 にフォールバック。
  - シェア数決定・制約処理（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method に対応。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap、手数料/スリッページ考慮の cost_buffer、スケーリングによる再配分アルゴリズムを実装。

- 解析・レポートツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・API レイテンシ（平均・最大・P95）を計測。
    - 基準値（稼働率99%、成功率90% 等）に基づく PASS/FAIL 判定を出力。
    - DB が存在しない場合やテーブル欠損時に穏健に動作（該当指標を N/A として続行）。
  - tools パッケージ初期化ファイルを追加。

- リサーチ基盤（ファクター計算）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - モメンタム / ボラティリティ / 流動性 / ファンダメンタル指標を計算する設計（DuckDB 接続を受けて prices_daily / raw_financials を参照）。
    - メソッド群・定数を定義（計算窓、スキャン幅など）。（注: 一部関数実装が途中の痕跡あり）

- DB 初期化連携
  - 監視用 DB の初期化呼び出し（init_monitoring_db）を run_execution, run_monitoring で実行してテーブル存在を保証（冪等）。

### Changed
- なし（初回リリースのため変更履歴はなし）。

### Fixed
- 不正な環境変数値や不足データに対するフォールバックや警告を多くの箇所で実装
  - MONITOR_POLL_INTERVAL が無効な場合にデフォルトへフォールバック（ログ出力あり）。
  - PAPER_FILL_MODE の不正値検出と ValueError。
  - validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告。
  - logging_setup でログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続。

### Security
- なし（このリリースで特記事項なし）。

### Notes / Known issues
- research/factor_research.py の一部関数は実装途中のように見えるため（コード断片の終端）、将来的な追加実装が必要。
- position_sizing の価格欠損時の挙動（price が 0 の場合の扱い）に注記があり、将来的にフォールバック価格の導入が検討される。
- process_priority や CPU affinity の設定は psutil の権限に依存し、失敗時は警告ログでスキップするようになっています（権限要件に注意）。

---

追記:
- 主な CLI:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証:  python -m kabusys.validate_config [--strict]
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 実行・監視スクリプト: python -m kabusys.run_execution / python -m kabusys.run_monitoring

（この CHANGELOG はコードから推測して作成しています。実際の変更履歴と差異がある場合は調整してください。）
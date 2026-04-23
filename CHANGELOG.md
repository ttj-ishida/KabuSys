# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従っています。

なお、コードから推測可能な変更点・追加点を基に記載しています（実際のコミット履歴ではありません）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

### Added
- 基本的なアプリケーション構成と複数の起動/ユーティリティスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - エンジンはスレッドで実行し、 data/stop_requested.flag による停止フラグ検知で安全停止。
    - 起動時に実行 PID を保存する pid_file の指定に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - Monitoring は環境に関わらず本番用 `sqlite_path` を使用する設計（コード内で明記）。
    - stop フラグファイルによりループ終了。KeyboardInterrupt のハンドリングあり。
  - config.py
    - 環境変数/.env の読み込み管理と Settings クラスを実装。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env 自動ロード。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env の読み込みは保護された OS 環境変数を上書きしない設計（protected set を利用）。
    - 多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム設定 等）。
    - Paper Trading の挙動設定: `paper_fill_mode` の検証（有効値チェック）や `paper_sqlite_path` を提供。
    - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL など）を組み込む。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml を検証する CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB path の親ディレクトリ確認、config YAML の存在とパースチェック（PyYAML 利用可の場合）。
    - `--strict` フラグで警告を FAIL 扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）。
  - config_setup.py
    - 対話式 .env ウィザードを追加。
    - 各項目の説明表示、既存 .env の読み込みと Enter による再利用、シークレット項目のマスク表示をサポート。
    - .env の書き出しテンプレートを提供（Git にコミットしない旨の注記付き）。
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler（cron 等で stdout/stderr を一元化するため stderr ではなく stdout を使用）と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はフォールバックしてコンソール出力のみを有効化。
    - ログレベルおよびログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収。アクセス権限不足などの例外は警告を出してスキップ。
    - CPU アフィニティ固定用の set_cpu_affinity を実装（利用コア数の上限チェック・例外ハンドリングあり）。
  - portfolio パッケージ（選定・配分・リスク・サイズ決定）
    - portfolio_builder.py
      - select_candidates: スコア降順＋タイブレーク処理で候補選定。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバックし警告。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価ベースで計算）、上限を超えるセクターの新規候補を除外（unknown セクターは除外しない）。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告のうえ 1.0 にフォールバック）。
    - position_sizing.py
      - calc_position_sizes: risk_based / equal / score の allocation_method に対応した発注株数計算。単元株（lot_size）で丸め、1銘柄上限や aggregate cap（available_cash）を考慮してスケーリング。cost_buffer を考慮した保守的見積り、残差処理（lot 単位での追加配分）を実装。
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（P95）などを算出し PASS/FAIL 判定を行う。
    - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - --from / --to / --db オプションに対応。
  - research/factor_research.py
    - ファクター計算モジュールの初期実装（モメンタム等の設計・定数定義、calc_momentum の実装開始）。

### Changed
- ロギング方針の統一
  - 全起動スクリプトで setup_logging を呼び出して一貫したログ管理を行う設計。
  - ファイルハンドラ作成に失敗してもプロセスが続行できる堅牢性を向上。
- DB パスの扱い
  - Execution は paper_trading モードで専用 SQLite を使い本番 DB と分離。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様を明示。

### Fixed
- .env 読み込みの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行内コメントの取り扱いなどを実装して .env パース精度を向上。
  - .env の上書き動作に protected set（OS 環境変数保護）を導入。

### Notes / Behavioral details
- Settings.env のバリデーションにより、無効な KABUSYS_ENV / LOG_LEVEL は ValueError を発生させる。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値時に警告を出してデフォルト 60 秒にフォールバックする。
- process_priority の設定はプラットフォームや権限に依存するため、実行環境によっては警告が出てスキップされることがある。
- tools/paper_verification_report の P95 計算はデータ件数に応じたパーセンタイルの実装（空リストは N/A）を行う。
- research/factor_research.py はファクター計算の実装方針およびモメンタム計算ルーチンの実装が含まれているが、ファイルの末尾が途中で切れている（今後の追加実装が想定される）。

### Security
- .env / 秘密情報の取り扱いに関する注意書きを config_setup のテンプレートに記載（.env を絶対に Git にコミットしないこと）。

---

以上がコードベースから推測できる本リリース相当の変更点です。追加で注記や別バージョン分割（例: 初期ベース機能を 0.1.0、ユーティリティ群を 0.1.1 など）を希望される場合は指示ください。
# Changelog

すべての変更は「Keep a Changelog」の形式に準拠して記載しています。日付・分類はコードベースの内容から推測して作成しています。

全般的な注記
- リポジトリは日本株自動売買システム "KabuSys" の初期リリース相当の機能群を含みます。
- 環境変数の自動ロード、CLI ツール、実行/監視用スクリプト、ポートフォリオ構築ロジック、ユーティリティ群（ログ設定・プロセス優先度設定）などを実装しています。
- .env にシークレットを含めない（コミットしない）旨の注意が含まれています。

## [0.1.0] - 2026-04-24
初回公開（コードベースから推測）

### Added
- 基本アプリケーション情報
  - パッケージ初期化とバージョン管理を追加（src/kabusys/__init__.py に __version__ = "0.1.0" を定義）。

- 実行・監視エントリポイント
  - Monitoring 用起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する実行方針を明示。
    - 停止は data/stop_requested.flag ファイル検出で行う。
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使い、本番 DB と分離。
    - 停止フラグおよび PID ファイル管理、デーモンスレッドでのエンジン実行を実装。

- 設定管理・補助ツール
  - Settings クラスによる環境変数ラッパーを実装（src/kabusys/config.py）。
    - .env/.env.local の自動読み込み（プロジェクトルート検出に基づく）。
    - 各種設定プロパティ（DB パス、API トークン、閾値、環境種別判定等）を提供。
    - PAPER_FILL_MODE 等の入力検証と意味的チェックを実装。
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の読み書き、既存値の再利用、シークレットマスク表示などを実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パス/設定 YAML の存在およびパース検証、ライブ環境時の追加ガードを実装。
    - --strict モードをサポート（警告を FAIL 扱いにできる）。

- ロギング・プロセス制御ユーティリティ
  - 統一的なログ初期化ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソールは stdout、ファイルは日次ローテーション（TimedRotatingFileHandler）で 30 日保持。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル/ログディレクトリの解決順を定義。
  - クロスプラットフォームなプロセス優先度／CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS 等の差分を吸収し、psutil を利用して優先度（high/normal/low）設定を行う。
    - CPU affinity 設定関数（set_cpu_affinity）を提供。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
    - スコアが全てゼロの際に等分配へフォールバック。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター比率に基づく候補除外。
    - calc_regime_multiplier: market regime ("bull"/"neutral"/"bear") に応じた資金乗数を提供（未知レジームは警告の上 1.0 にフォールバック）。
  - 位置サイズ計算・リスク制御（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）で丸め、ポジション上限、aggregate cap、手数料・スリッページ緩衝（cost_buffer）を考慮したスケーリングロジックを実装。

- Paper Trading 検証レポートツール
  - paper_verification_report ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）を集計してレポート出力。
    - Pass/Fail 判定基準（稼働率 99%、成立率 90% 等）を定義。
    - DB パスの引数/環境変数対応（--db / PAPER_TRADING_SQLITE_PATH）。

- 研究用ファクター計算基盤（着手）
  - research/factor_research.py を追加（DuckDB 接続を受け、Momentum/Value/Volatility/Liquidity 等を計算する仕様を記載）。（ファイル末尾は未完の状態で計算関数の実装が続く想定）

- データベース・監視初期化
  - init_monitoring_db を呼び出すことで monitoring 用テーブルの存在を担保（冪等に初期化）。

### Changed
- .env 読み込みロジックの強化（src/kabusys/config.py）
  - export プレフィックス、クォート文字列内のバックスラッシュエスケープ、インラインコメント処理、コメントの解釈ルールなどをサポートする堅牢なパーサを実装。
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を検出できた場合のみ行われ、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- ログ出力の挙動変更（src/kabusys/utils/logging_setup.py）
  - コンソール出力を stdout に統一（cron 等で stdout/stderr 一元化を想定）。
  - 既にハンドラが設定されている場合は一旦クリアして再設定することで二重出力を防止。

- 実行/監視スクリプトの挙動
  - 起動時にプロセス優先度を "high" に設定する処理を追加（set_process_priority を使用）。
  - Monitoring は環境変数に関係なく production 用 sqlite_path を使用する方針を明記。
  - Execution は paper_trading モード時に paper_sqlite_path を使用し DB を分離。

### Fixed
- 環境変数の不正値に対するフォールバック
  - MONITOR_POLL_INTERVAL が不正（非数値や 0 以下）だった場合にデフォルト 60 秒へフォールバックし、警告を出すよう修正（src/kabusys/run_monitoring.py）。
  - Settings の PAPER_FILL_MODE が不正な値だった場合に ValueError を送出して早期検出するように実装（src/kabusys/config.py）。

- ファイル/ディレクトリ作成失敗への耐性
  - ログディレクトリの作成失敗やファイルハンドラ生成失敗をハンドルし、コンソール出力のみで継続するように修正（src/kabusys/utils/logging_setup.py）。
  - .env 読み込みでファイルオープン失敗時に warnings.warn を出して処理を継続（src/kabusys/config.py）。

- プロセス優先度設定の例外ハンドリング
  - 権限不足や未対応プラットフォームでの例外（psutil.AccessDenied 等）を捕捉してワーニングを出力し処理をスキップするように実装（src/kabusys/utils/process_priority.py）。

### Security
- .env に関する注意喚起を追加（src/kabusys/config_setup.py）
  - .env は絶対に Git にコミットしない旨を明記。
- config_setup ウィザードではシークレット項目はマスク表示して確認できるように実装。

### Documentation / Developer experience
- CLI ツールにヘルプや使用例（引数説明）を追加（config_setup, validate_config, paper_verification_report）。
- 出力メッセージ・ログメッセージを日本語で統一（ユーザ向けのガイドラインや実行時ログの可読性向上）。

---

注: 上記の CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴・差分がある場合はそちらを基に正確な変更履歴（各コミットの要約・著者・変更点）を作成することを推奨します。必要なら、ファイルごとの詳細な変更要約や、今後の TODO / 既知の制限点を CHANGELOG に追記する文言も作成できます。どのように進めますか？
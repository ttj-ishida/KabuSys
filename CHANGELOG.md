# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

フォーマット:
- 重大な変更は Breaking changes として明記します。
- 日付はリリース日を示します。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて paper_trading モードでは MockBrokerClient を使用し、paper_trading 用の SQLite（data/paper_trading.db をデフォルト）にデータを記録して本番 DB と分離する動作を実装。
    - 起動時にプロセス優先度を High に設定。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）による起動／停止制御を実装。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててデーモンスレッドで実行。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 監視処理は常に（KABUSYS_ENV にかかわらず）本番用 sqlite_path を使用。
    - 停止フラグ検知で安全にループを終了。

- 環境設定・検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成／更新。複数の設定項目（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DB パス等）をサポート。
    - 既存の .env を読み込み、Enter で既存値を維持可能。保存前の確認プロンプトあり。
  - validate_config.py
    - .env と config/*.yaml の事前チェックツール。必須環境変数の未設定検出、パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML が存在する場合）、本番環境用のガード（LINE トークン未設定等）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- 設定管理
  - config.py
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）に基づく .env 自動ロード機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の独自パーサ実装: export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
    - Settings クラスを提供し、各種環境変数への安全なアクセサ（duckdb/sqlite パス、KABUSYS_ENV のバリデーション、paper_trading 固有のパスや fill モード等）を実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補を選出（タイブレーク時は signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとのエクスポージャーが上限を超えた場合に新規候補を除外するロジック（"unknown" セクターは上限除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームは警告後フォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。
    - 単元株（lot_size）で丸め、ポジション上限、利用可能現金に基づく aggregate cap と縮小ロジック、cost_buffer を用いた保守的見積り、余りキャッシュを用いたロット単位での再配分（残差ソート）を実装。

- リサーチ／ツール
  - research.factor_research（ファクター計算基盤）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を基にモメンタムや MA200 乖離等を計算する設計（関数 calc_momentum 等の導入。ファイルは途中まで実装）。
  - tools.paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率 / 注文成功率 / 送信率 / レイテンシ（AVG, MAX, P95）を集計して PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）。

- ユーティリティ
  - utils.logging_setup
    - 一貫したログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - LOG_DIR 作成失敗時にファイル出力をスキップしてコンソールログのみで継続するフォールバック実装。
    - 既存ハンドラをクリアして二重出力を防止。
  - utils.process_priority
    - Windows / POSIX(Linux, Darwin, FreeBSD) を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity 設定関数（set_cpu_affinity）を提供。権限不足や未実装 API には警告を出してスキップ。

- DB 関連
  - duckdb 接続を多くのコンポーネントが受け取る設計を採用（分析と運用 DB を分離）。

### 変更 (Changed)
- ログ出力の標準化
  - すべての起動スクリプトから utils.logging_setup.setup_logging を呼ぶことでログ設定を統一。

- 環境変数の取り扱い
  - .env 読み込みにおいて OS 環境変数は保護され、.env.local は .env を上書きする優先度で読み込む設計に。

- Execution エンジン周り
  - paper_trading モードでは paper_sqlite_path を使用するようにして、本番 DB と完全に分離。

### 修正 (Fixed)
- 無効な MONITOR_POLL_INTERVAL の扱い
  - 0 以下や非整数値が与えられた場合に警告を出しデフォルト値へフォールバックする保護を追加（time.sleep に渡す値での例外を防止）。

- ログディレクトリ作成失敗時の扱い
  - ファイルハンドラの作成に失敗した場合にコンソール出力のみで継続するようフォールバックを実装し、起動失敗を回避。

### 既知の問題 / 注意点 (Known issues / Notes)
- research.factor_research.calc_momentum の実装はファイル末尾で途切れており、完全実装が必要（本リリースでは基盤と設計のみ提供）。
- position_sizing.apply_sector_cap 内で price の欠損（0.0）の扱いに関する注記（TODO）が残っている。将来的には前日終値や取得原価のフォールバックが望ましい。
- 一部の関数は外部依存（psutil、duckdb、PyYAML など）により環境にそれらが存在しないと機能限定またはスキップ動作となる点に注意。
- 実際の発注処理やブローカークライアントの実装に関しては、paper_trading と live の動作差分のテストが必要。

### セキュリティ (Security)
- .env ファイルに秘密情報を含む設計のため、README に記載の通り .env は絶対に Git にコミットしないことを強く推奨。

---

（今後のリリースでは、factor_research の完成、テストカバレッジ拡充、銘柄別 lot_size 対応、追加の運用監視（アラート送信等）などを予定しています。）
# CHANGELOG

すべての重要な変更点は Keep a Changelog のフォーマットに準拠して記載します。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-25
初回リリース。本リリースでは自動売買システムのコアユーティリティ、起動スクリプト、設定管理、ポートフォリオ構築ロジック、ペーパートレード検証ツール、ロギング／プロセス制御ユーティリティなどを提供します。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper-trading SQLite（data/paper_trading.db をデフォルト）を使用することで本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）に基づく安全な起動／停止制御を実装。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - ブローカークライアントの抽象化（BrokerClientFactory）と、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き対応（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境に関わらず本番用 sqlite_path を使用する仕様（監視 DB の分離ポリシー）。
    - 停止フラグ検知でループを終了し、例外発生時もログに記録して次ポーリングへ継続。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env, .env.local の読み込み順と上書きルール（OS 環境 > .env.local > .env）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加。
    - .env パース処理は引用符、エスケープ、およびインラインコメントに対応。
    - Settings クラスを実装して環境変数をプロパティ経由で安全に取得（必須項目は _require() でチェック）。
    - Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）をサポート。
    - 監視／システム関連設定（PID ファイルパス、Kill フラグ、閾値設定、実行環境検証等）を追加。

- 設定支援・検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - デフォルト値・選択肢・シークレット入力・既存 .env の読み込みをサポートし、最終的に .env を書き出す機能を提供。
  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数の未設定検出、KABUSYS_ENV の妥当性、LOG_LEVEL の検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を行う。
    - --strict モードにより警告をエラー扱いにできる。

- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化関数 setup_logging を追加。コンソール出力（stdout）と日次ローテートファイルハンドラ（TimedRotatingFileHandler）をセットアップ。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作する耐障害性を実装。
    - LOG_LEVEL／LOG_DIR の環境変数および引数による設定をサポート。
  - utils/process_priority.py
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収したプロセス優先度設定（set_process_priority）を追加。psutil の可用性に応じて安全にフォールバックする。
    - CPU affinity 設定ユーティリティ set_cpu_affinity を追加（指定コア数に固定する機能）。

- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全体が 0 の場合のフォールバックロジック（等金額）と警告ログを実装。
  - portfolio/risk_adjustment.py
    - セクター別上限適用ロジック apply_sector_cap を実装（売却予定銘柄の除外、unknown セクターの扱い等）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知レジームはフォールバックと警告）。
  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装。allocation_method ("risk_based", "equal", "score") をサポート。
    - リスクベース（risk_pct, stop_loss_pct）と単元株（lot_size）、max_position_pct、max_utilization、cost_buffer（手数料/スリッページ見積り） を考慮したスケーリング、aggregate cap のスケールダウンロジックを実装。
    - 端数調整（lot_size 単位で切り捨て・残余キャッシュでの再配分）を実装。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - P95 計算、期間フィルタ（--from/--to）、閾値による PASS/FAIL 判定を実装。
    - DB が存在しない場合やテーブル未作成の場合の耐障害処理（N/A扱いや例外キャッチ）を実装。

- データリサーチ基盤（部分実装）
  - research/factor_research.py（設計とファクター計算ロジックの雛形）
    - DuckDB を用いたファクター計算設計を追加（Momentum / Value / Volatility / Liquidity の方針、計算期間定義等）。
    - calc_momentum 等の関数スケルトンと定数を定義（ファイル末尾が途中で切れているが、設計は含まれる）。

### Changed
- ログ出力の標準出力先を stderr ではなく stdout に変更（setup_logging）:
  - cron やタスクスケジューラからのリダイレクト運用を考慮して stdout を利用する設計とした。

- .env ファイルの読み込みポリシーを明文化:
  - OS 環境変数を保護しつつ .env.local での上書きを可能にする動作。

### Fixed
- 環境変数パースの堅牢化（config._parse_env_line）:
  - シングル／ダブルクォート内のエスケープ、インラインコメント処理、export プレフィックス対応などを実装して .env の柔軟な記述に対応。

- 起動時の例外安全化:
  - run_monitoring と run_execution の両方で DB コネクションやスレッド終了処理を finally ブロックで確実にクローズするようにした。

### Security
- .env の取り扱いに関する注意喚起を config_setup.py に記載:
  - .env を絶対に Git にコミットしない旨を明示（機密情報保護のベストプラクティス）。

## 将来の改善アイデア（コードコメントより）
- position_sizing の price 欠損時のフォールバックロジック（前日終値や取得原価など）を追加予定。
- stocks マスタに lot_size を持たせ、銘柄別単元対応を行う設計への拡張予定。
- factor_research の完全実装（複数ファクターの計算・正規化・結合処理）。
- run_monitoring の監視データ永続化・集計ロジックの追加強化。

---

（注）本 CHANGELOG は提示いただいたコードの実装内容から推測して作成したものであり、別途ドキュメントやコミット履歴がある場合はそちらに合わせて更新してください。
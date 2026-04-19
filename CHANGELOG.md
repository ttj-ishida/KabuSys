# CHANGELOG

すべての目立つ変更点をまとめます。フォーマットは「Keep a Changelog」に準拠しています。

全般:
- このプロジェクトは日本株自動売買システム「KabuSys」の初期リリースです。
- バージョン情報はパッケージルートの `__version__ = "0.1.0"` に合わせています。

## [Unreleased]
- 今後の変更予定や進行中の作業はここに記載します。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成
  - パッケージ初期構成を追加（kabusys パッケージ、サブパッケージ群）。
  - __version__ を "0.1.0" に設定。

- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を高く設定。
    - 環境に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用する分離設計。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知で安全終了。
    - PID ファイルを書き込む仕組みをサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 監視は本番 sqlite_path を使用（環境に依存せず監視 DB を統一）。
    - 停止フラグ検知でループ終了。

- 設定・環境管理
  - config.py: 環境変数読み込み・Settings クラスを追加。
    - .env の自動読み込み（プロジェクトルートを探索して .env/.env.local を読み込む）。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサーは export 形式、クォート／エスケープ、インラインコメント取り扱いに対応。
    - 各種設定プロパティ（DB パス、API トークン、Paper Trading 設定、しきい値、環境種別チェック等）を提供。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - シークレット項目のマスク表示、選択肢・デフォルトサポート。
    - .env の読み書きロジックを提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DB パスや config/*.yaml の存在チェック（PyYAML がない場合はパース検証をスキップして警告）。
    - --strict オプションで警告を失敗とみなすモードをサポート。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみで継続）。
    - 既存ハンドラのクリア処理を行い二重設定を回避。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, macOS 等）差分を吸収して優先度を設定。
    - CPU affinity を N コアに固定する機能を提供（機能がない環境では安全にスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み (calc_score_weights) を追加。
    - スコアが全て 0 の場合のフォールバックロジックを備える。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。
    - セクター未登録銘柄は "unknown" 扱いで上限判定をスキップする設計。
    - レジームに応じた乗数マップ（bull/neutral/bear）を提供。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック（risk_based / equal / score）を実装。
    - lot_size 単位の丸め、per-stock 上限、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りをサポート。
    - スケーリング時の残差配分アルゴリズム（fractional remainder を使って安定的に lot 単位を追加）を実装。

- リサーチ（ファクター計算）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity に対応する設計）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算関数 calc_momentum の骨組みと各種定数を導入（計算ロジックの実装途中を含む）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ等を集計してレポート出力。
    - P95 レイテンシ計算、閾値判定（PASS/FAIL）ロジックを追加。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- DB / 分析
  - 全体で DuckDB 接続（duckdb_conn）を受け取る設計を採用。実行/監視の両スクリプトで DuckDB を利用。

### Changed
- 監視／実行の挙動
  - 監視（run_monitoring）では MONITOR_POLL_INTERVAL を使ったポーリング間隔上書きをサポート。0 以下や不正値はデフォルト 60 秒にフォールバックする安全化を実装。
  - 実行（run_execution）では paper_trading 環境時に専用 SQLite を使い、本番 DB と完全分離するように明確化。
  - 監視と実行の両方で init_monitoring_db() を呼び出し、監視用テーブルが存在することを冪等に保証。

- ロギング
  - ログは stdout に出力されるようデフォルト設計（cron / Task Scheduler 等での取り扱いを考慮）。
  - ログファイルは日次ローテート・30 日保持をデフォルトに設定。

- 環境読み込み順
  - OS 環境変数 > .env.local > .env の順で読み込む（.env.local は既存キーを上書き。ただし OS 環境変数は保護）。

### Fixed
- .env 読み込みの堅牢化
  - export プレフィックス・クォートされた値・エスケープシーケンス・インラインコメントの取り扱いを改善。
  - .env ファイル読み込み失敗時は警告を出して処理を継続（例: 権限エラー等）。

- 起動時の安全措置
  - run_execution では起動前に停止フラグが既に立っている場合に起動を中止するチェックを追加。
  - run_monitoring/run_execution の finally ブロックで DB 接続を確実に close するように整理。

### Known issues / Notes
- research/factor_research.py の calc_momentum 関数は骨組みがあり、多くの補助定数が定義されていますが、ファイル末尾で処理が途中で切れている箇所が見受けられます（今後実装を完了する必要あり）。
- position_sizing の価格欠損時の挙動について注釈があり（price が 0 の場合の取り扱い）。将来的に前日終値や取得原価でのフォールバックを検討中。
- config/*.yaml の内容検証には PyYAML が必要。未インストール時はパース検証はスキップされ、警告が出力されます。

### Security
- 環境変数（シークレット）は .env に平文で保存する設計のため、.env を Git にコミットしない旨が config_setup.py に明記されています。運用時は適切なシークレット管理を推奨。

---

参考: 各ファイルの主要機能はソースコメント・ドキュメント文字列内に記載されています。必要であれば各モジュールごとの詳細な変更点や実装方針（例えばポジションサイズ算出アルゴリズムのフローやスケールダウン処理の詳細）を別途まとめます。
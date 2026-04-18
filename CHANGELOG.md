# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

なお本CHANGELOGは、与えられたコードベースの内容から推測して作成しています。

## [Unreleased]
- （今後の変更点をここに記載）

## [0.1.0] - 2026-04-18
初回リリース。システム全体のコア機能・ユーティリティ・CLI を追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定管理
  - `kabusys.config.Settings` クラスを導入し、環境変数から設定値を取得する統一インターフェイスを提供。
  - 自動 .env ロード機能を追加（プロジェクトルートの検出：.git または pyproject.toml を基準）。
  - `.env` / `.env.local` の読み込み順・上書きポリシーを実装（OS 環境変数は保護）。
  - .env パース処理を強化（export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理など）。
  - 設定プロパティ（DB パス、API トークン、LINE 設定、監視しきい値、環境種別判定など）を実装。
  - `KILL_FLAG_CLEAR_ON_START` 等の運用向けフラグをサポート。

- 起動スクリプト / デーモン系
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV による paper_trading の DB 分離（paper_trading 用 SQLite を使用）。
    - Broker クライアントファクトリを利用してブローカー依存性を注入。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立てと ExecutionEngine の起動ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組みを追加。
    - 実行時 PID ファイル管理（data/execution.pid）に対応。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔の上書き（デフォルト 60 秒、無効値はフォールバック）。
    - 監視 DB の初期化（監視は本番 sqlite_path を参照する実装）。
    - 停止フラグ検知によるループ終了、例外ログと継続動作の実装。

- 監視・運用データベース
  - `monitoring_db.init_monitoring_db`（呼び出し）により監視用テーブルの冪等的初期化を保証。

- ロギング / 優先度ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテーションの FileHandler (TimedRotatingFileHandler) をルートロガーに設定。
    - ログディレクトリ自動作成、環境変数 / 引数によるレベル・ディレクトリ指定。
    - ログ重複防止のため既存ハンドラのクリーンアップを実施。
  - `kabusys.utils.process_priority.set_process_priority` と `set_cpu_affinity` を追加。
    - Windows / POSIX の差分吸収（psutil を利用）、アクセス権限不足時は警告を出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順・タイブレークルール）
    - 重み計算 `calc_equal_weights`, `calc_score_weights`（スコア全0 のフォールバックを含む）
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中抑制 `apply_sector_cap`（既存保有のセクター比率を計算し新規候補を除外）
    - レジーム乗数 `calc_regime_multiplier`（bull/neutral/bear に基づく乗数）
  - `kabusys.portfolio.position_sizing`
    - 株数決定 `calc_position_sizes`（risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケーリング、cost_buffer を考慮）

- 研究 / ファクター計算
  - `kabusys.research.factor_research`（ファクター計算モジュール、DuckDB 接続を受け取る設計）
    - モメンタム、MA200 乖離、ATR、流動性等の計算方針を実装するための定数と骨子を追加（DuckDB 経由で prices_daily / raw_financials を参照）。

- ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading の検証レポート生成スクリプト（期間指定オプションあり）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出、閾値判定（PASS/FAIL）を出力。
    - P95 の算出、データ不足時の N/A 扱い、DB ファイル存在チェックを実装。

- 設定支援 CLI
  - `kabusys.config_setup`：対話式ウィザードで .env ファイルを初期作成・更新するツールを追加。
    - シークレット項目は入力時にマスク、生成される .env はコメント付で書き出し。
    - 既存 .env 読み込み、Enter で既存値継承、保存確認を実装。
  - `kabusys.validate_config`：設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値検証、DB パス親ディレクトリチェック、config/*.yaml の存在・パース確認（PyYAML があれば内容検証）。
    - `--strict` オプションで警告も失敗扱いにできるように実装。
    - 本番環境（live）向けの追加ガード（LINE 未設定、KILL_FLAG_CLEAR_ON_START の危険性警告など）。

### Changed
- （初回リリースのため特になし）

### Fixed
- （初回リリースのため特になし）

### Security
- シークレット系（J-Quants トークン、kabu API パスワード、LINE トークン）は .env で管理する前提とし、config_setup にて .env を明示的に生成するよう案内。

---

その他の設計上の注意点（ドキュメント的注釈）
- 多くのポートフォリオ / position sizing 関数は「純粋関数」であり、DB 参照は行わないことを明記（テスト容易性を考慮）。
- Paper Trading と本番データベースは分離（paper_trading モードでは専用 SQLite を使用）。
- ロギング・プロセス優先度設定は起動時に最初に行うことを想定（run_execution/run_monitoring でそれを実施）。
- いくつかの箇所で将来的な拡張用の TODO コメント（例: 銘柄別 lot_size のサポート、価格フォールバック）を残している。

もし CHANGELOG に追記したい差分（例えばバグ修正やリファクタ履歴、さらに詳細なリリースノート）があれば、実際のコミット履歴や追加のソースコード変更点を教えてください。これに基づいてバージョンごとの詳しい変更履歴を作成します。
# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
このファイルはコードベース（src/kabusys 以下）の現状から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]
（無し）

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 環境・設定管理
  - `kabusys.config`:
    - .env ファイルの自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env の行パーサ（export 形式、クォート、インラインコメント、エスケープに対応）。
    - 環境変数保護（OS 環境変数を上書きしない挙動）と上書きオプション。
    - `Settings` クラスを提供し、J-Quants / kabuステーション / DB /監視 /システム設定等のプロパティを型付で取得。入力値の検証（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の妥当性チェック）を実装。
    - デフォルトパス（DuckDB / SQLite 等）や Paper Trading 専用 DB パスの管理。

- 設定ウィザードと検証 CLI
  - `kabusys.config_setup`:
    - 対話式ウィザードで .env を初期作成・更新するユーティリティを実装。
    - 秘匿値（トークン/パスワード）のマスク表示、選択肢・デフォルト対応、保存確認機能を提供。
  - `kabusys.validate_config`:
    - 起動前に必須環境変数や config/*.yaml、DB パス、KABUSYS_ENV 等を検証する CLI を追加。
    - PyYAML がない場合は YAML 検証をスキップする旨の警告表示。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行系 / 監視系起動スクリプト
  - `kabusys.run_execution`:
    - ExecutionEngine 起動スクリプト。プロセス優先度設定、DB 接続、ブローカークライアント生成、依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）組立て、スレッドでエンジン実行、停止フラグ監視による安全停止を実装。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient 等のペーパートレード用クライアントを使用し、Paper Trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）にデータを分離して記録。
    - 起動前に停止フラグ（data/stop_requested.flag）を検出すると起動を中止するガードを追加。
  - `kabusys.run_monitoring`:
    - SystemMonitor のポーリングループ起動スクリプトを追加。プロセス優先度設定、SQLite（監視用）と DuckDB への接続、1 回チェックの実行、停止フラグ監視、例外捕捉・ログ出力を実装。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値（0以下や非整数）の場合はデフォルトにフォールバックして警告を出す。
    - Monitoring は環境にかかわらず本番 `sqlite_path` を使用する旨の挙動を明記。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup`:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代保持）を設定するユーティリティを実装。既存ハンドラをクリアして二重設定を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化し、コンソール出力のみで継続する堅牢性を実装。
  - `kabusys.utils.process_priority`:
    - クロスプラットフォームでプロセス優先度設定（Windows の優先度クラス、POSIX の nice 値）を行うユーティリティを実装。
    - CPU affinity 設定ユーティリティ（指定コア数にプロセスを固定）を追加。
    - 権限不足などで設定に失敗しても警告を出してスキップする安全設計。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定（スコア降順・タイブレークルール）、等配分・スコア重み配分ロジックを実装。
    - スコアが全てゼロの場合のフォールバック（等配分）を警告とともに提供。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限（既存保有からセクターごとのエクスポージャーを算出し、上限を超えたセクターの候補を除外）を実装。
    - マーケットレジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは 1.0 でフォールバック。
    - 一部の設計上の注意（価格欠損時の誤査定リスク等）をコメントで明示。
  - `kabusys.portfolio.position_sizing`:
    - 各配分方法（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を加味した保守的見積り、残差処理（fractional remainder による追加配分）などを実装。
  - `kabusys.portfolio.__init__` で主要関数を公開。

- リサーチ（ファクター計算）基盤
  - `kabusys.research.factor_research`:
    - Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計を追加（DuckDB 接続を受け prices_daily / raw_financials を参照する想定）。
    - モメンタム計算（1M/3M/6M、MA200乖離）などの定義、スキャン期間等の定数を定義。
    - （ファイル末尾で実装途中の箇所あり。以降の実装は別途進行予定。）

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 向けの検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）等を集計し、閾値（稼働率99%、注文成功率90%、送信率95%、P95<=200ms）に基づく PASS/FAIL 判定を行う。
    - CLI オプション（--from, --to, --db）で期間や DB を指定可能。DB が存在しない場合はエラーメッセージを表示。

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db`（参照されているが本差分に含まれる実装想定）を起動時に呼び出して監視用テーブルの存在を保証（冪等な初期化）。

### Changed
- （初回リリースのため該当無し）

### Fixed
- 環境変数やファイル IO 周りで想定される落とし穴に対する改善（安全なフォールバック・警告出力など）を多数導入:
  - MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバック。
  - ログディレクトリ作成失敗時にファイルハンドラ作成を回避してコンソールログのみ継続。
  - プロセス優先度・CPU affinity の権限エラーを捕捉して警告を出す。

### Removed
- （初回リリースのため該当無し）

### Security
- .env を生成する際のヘッダに「.env を絶対に Git にコミットしないこと」を明記。
- 機密情報はウィザードでマスク表示され、.env の扱いに注意喚起を追加。

### Notes / Known limitations
- research/factor_research の一部は実装が途中（ファイル末尾で計算ロジックが切れている）。今後のリリースで完成予定。
- 一部 TODO コメント（例: price 欠損時のフォールバック価格、銘柄別 lot_size のサポートなど）が残っている。
- YAML 検証は PyYAML インストールの有無に依存する（未インストール時は検証をスキップし警告を出す）。
- Monitoring が常に「本番 sqlite_path」を使う設計は意図的だが、運用時は注意が必要。

---

開発/運用に関する注記や追加の変更履歴を希望する場合は、対象のファイルや最近行ったコミット情報を提供してください。差分に基づいてより詳細な CHANGELOG の分割（Fixes / Performance / Documentation 等）を作成できます。
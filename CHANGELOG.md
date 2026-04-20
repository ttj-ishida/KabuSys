# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはコードベースの内容から推測して作成したもので、実際のコミット履歴と完全に一致しない場合があります。

フォーマット:
- Unreleased: 今後の変更予定
- 各バージョン: 追加（Added） / 変更（Changed） / 修正（Fixed）などのカテゴリで記載

---

## [Unreleased]

- （現時点では未リリースの変更はありません。必要に応じてここに追記してください）

---

## [0.1.0] - 2026-04-20

初回公開（推定）。自動売買システム KabuSys の基本機能群を実装したスナップショット。

### Added
- 基本設定・環境変数管理
  - Settings クラスを実装（`kabusys.config`）。
    - 多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境等）。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証を実装。
    - paper trading 用の専用 SQLite パス設定（PAPER_TRADING_SQLITE_PATH）と PAPER_FILL_MODE 検証を追加。
  - .env 自動ロード機能を実装（プロジェクトルート検出、.env / .env.local の読み込み、OS 環境変数保護）。
  - .env ファイルパーサーの強化: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。

- 設定支援ツール
  - 対話式ウィザードで .env を作成/更新する CLI（`kabusys.config_setup`）。
  - 設定検証 CLI（`kabusys.validate_config`）を追加。必須環境変数のチェック、KABUSYS_ENV のガード、DB パスの存在確認、YAML 設定ファイルの存在/パース検証（PyYAML があればパースも実行）を提供。`--strict` オプションで警告を失敗扱いにできる。

- 実行・監視の起動スクリプト
  - 実行エンジン起動スクリプト（`run_execution.py`）
    - プロセス優先度を高く設定して起動（`set_process_priority("high")`）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで起動。停止フラグの検知で安全に停止。
    - 監視テーブルの初期化（冪等に保証）と DuckDB 接続。
  - 監視ループ起動スクリプト（`run_monitoring.py`）
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は環境にかかわらず「本番」sqlite_path を参照する設計。
    - SystemMonitor の単一チェック呼び出し（check_once）をループ実行し例外を捕捉して次回ポーリングへ継続。停止フラグファイルでループ終了。

- ロギング周り
  - 統一的ログ設定ユーティリティ（`kabusys.utils.logging_setup`）
    - stdout 出力用 StreamHandler（stdout 使用）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリの解決順（引数 > LOG_DIR 環境変数 > デフォルト logs/）とログレベルの解決順（引数 > LOG_LEVEL > INFO）。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして二重設定を防止。

- プロセス優先度 / CPU 固定ユーティリティ
  - `kabusys.utils.process_priority` を追加
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収した優先度設定（high/normal/low）。
    - CPU affinity 設定（最初の N コアへピン留め）、例外時は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 select_candidates（スコア降順、同点時 tie-break）。
    - 重み計算 calc_equal_weights, calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を超える場合に当該セクターの追加候補を除外、"unknown" セクターは適用除外）。
    - レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear のマップ、未知レジームはフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - ポジションサイズ計算 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、端数配分ロジックを実装。cost_buffer による保守的コスト見積り対応。

- リサーチ / ファクター計算（骨組み）
  - `kabusys.research.factor_research` にモメンタム等のファクター計算関数の実装方針と一部実装（mom など、DuckDB 接続前提）。
  - DuckDB を利用した prices_daily / raw_financials ベースの計算設計。

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading DB（デフォルト data/paper_trading.db）から稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）等を集計し PASS/FAIL 判定を行うレポート機能を追加。
    - P95 計算、期間フィルタ（ISO8601 UTC 変換）、テーブル欠如時のフォールバック（OperationalError を捕捉）を備える。
    - デフォルトの閾値を定義（稼働率 99% 等）。

- パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（`kabusys.__init__`）。

### Changed
- なし（初回リリース想定のため特別な変更履歴は無し）。

### Fixed / Robustness improvements
- .env 読み込みの耐障害性を向上
  - ファイル読み込み失敗時に warning を出して継続。
  - OS 環境変数を保護する protected パラメータ機構を導入し誤って上書きしないようにした。
- ロギング設定のフォールバック強化
  - ログディレクトリ作成やファイルハンドラ生成に失敗しても stdout の StreamHandler は必ず動作するようにしている。
- プロセス優先度設定のフォールバック
  - 権限不足や未サポート OS の場合はワーニングを出し処理をスキップして安全に動作するように実装。
- run_monitoring / run_execution の安全停止
  - stop flag / kill flag の検知と例外捕捉によりループを安全に終了する仕組みを強化。
- DB 初期化の冪等化
  - 監視テーブル初期化関数 init_monitoring_db を呼び出してテーブル存在を保証（何度呼んでも安全）。

### Potential limitations / TODO（コードから推測）
- position_sizing で price が欠損（0.0）の場合にエクスポージャー低めに評価される可能性がある旨の TODO コメントあり（前日終値等のフォールバック検討）。
- factor_research の実装が途中で切れている（ファイル末尾が未完の可能性あり）。
- 銘柄ごとの lot_size を将来サポートする旨の TODO がある（現状は共通単元数を想定）。

---

参照:
- 本CHANGELOGはソースコード（src/kabusys 以下のモジュール）から実装状況を推測して作成しています。実際のコミットメッセージやリリースノートが存在する場合はそちらを優先してください。
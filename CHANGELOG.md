# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルは、与えられたコードベースの内容から推測して作成した変更履歴（要約）です。

全般的な前提:
- バージョンはパッケージ定義（src/kabusys/__init__.py の __version__）に合わせて 0.1.0 を初期リリースとしています。
- 記載内容はソースコード（CLI、ユーティリティ、ポートフォリオ構築ロジック、モニタリング/実行スクリプト、ツール等）から推測した機能と設計意図に基づきます。

## [Unreleased]
- （現状なし）

## [0.1.0] - 2026-04-25
### Added
- 初期リリース: KabuSys — 日本株自動売買システム（ベーシック実装）
  - パッケージバージョンを 0.1.0 に設定。
- 環境設定・読み込み
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数から各種設定を取得：J-Quants / kabu API / DB パス / ログレベル / 環境（development/paper_trading/live）など。
    - PAPER_FILL_MODE に対する検証と有効値制約（instant/partial/never/reject）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）と通常 sqlite_path の区別。
    - 各種しきい値（CPU/MEM/MEM/DISK）や kill/ pid ファイルパスもプロパティで管理。
  - .env 自動ロード機能を導入
    - プロジェクトルート（.git または pyproject.toml）を自動検出して .env / .env.local を読み込み。
    - export プレフィックスやクォート、インラインコメントなどに対応するカスタムパーサを実装。
    - OS 環境変数を保護するための「protected」扱い（既存 OS 環境変数は上書きされない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
- 設定関連 CLI
  - 対話式ウィザード: config_setup.py（.env の作成・更新を支援）
    - 対話的に .env を作成し、ファイル書き込み（テンプレートヘッダ付）を行う。
    - シークレット値は入力時にマスク表示、既存値を再利用可能。
  - 設定検証ツール: validate_config.py
    - 必須環境変数チェック、KABUSYS_ENV 値検査、ログレベル・DB パスの存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - --strict オプションで警告を FAIL 扱いにするモードを提供。
    - 本番環境（live）時の追加ガード（LINE 未設定や Kill Switch の自動クリア設定の警告）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor を初期化してポーリングループを実行（デフォルト間隔 60 秒）。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（不正値時にはデフォルトを使用）。
    - 停止フラグファイル data/stop_requested.flag を検知して優雅に終了。
    - 監視用 DB（monitoring）は環境に関わらず本番 sqlite_path を使用する実装。
    - SQLite / DuckDB 接続の初期化とクローズを適切に管理。
  - run_execution.py
    - ExecutionEngine 起動スクリプト（ExecutionEngine を別スレッドで実行）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（本番/モックの切替）。
    - 停止フラグを監視し、検出時にエンジン停止をトリガー。
    - 起動時に既に停止フラグがある場合は起動を中止。
- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
- ロギング・ユーティリティ
  - setup_logging（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定。
    - LOG_LEVEL / LOG_DIR の解決順を定義し、既存ハンドラのクリアを行うことで二重設定を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
- プロセス優先度・CPU affinity ユーティリティ
  - set_process_priority / set_cpu_affinity（src/kabusys/utils/process_priority.py）
    - Windows と POSIX の差分を吸収。権限不足時や未対応 OS では警告してスキップ。
    - set_process_priority("high") を起動スクリプトの冒頭で呼ぶ設計を採用。
- ポートフォリオ構築モジュール
  - portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等重み/スコア重み算出（calc_equal_weights/calc_score_weights）。
    - スコア全0 の場合は等分配へフォールバックして警告。
  - risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有のセクター比率が閾値を超える場合、新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）: bull/neutral/bear に応じた乗数（1.0/0.7/0.3）を提供。未知レジームは 1.0 にフォールバック。
  - position_sizing.py
    - ポジションサイズ算出ロジック（risk_based / equal / score の各方式）。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、利用可能資金に応じた aggregate cap スケーリング、cost_buffer による保守的見積り、残余キャッシュに基づく端数配分ロジックを実装。
    - 価格欠損時のスキップやログ出力に対応。
- 研究・ファクター計算（骨格）
  - research/factor_research.py にモメンタム/ボラティリティ/バリュー等の計算設計（DuckDB 経由で prices_daily / raw_financials を参照する方針）を追加（calc_momentum などの実装開始）。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成 CLI。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）等を SQLite の各テーブルから集計して PASS/FAIL 判定（しきい値をファイル先頭に定義）。
    - --from/--to/--db オプションをサポート。P95 算出と出力整形を実装。

### Changed
- （初期リリースのため過去変更はなし。内部設計を反映した仕様記載のみ。）

### Fixed
- run_monitoring と run_execution において、例外・終了時に DB 接続を必ずクローズするよう try/finally を整備（リソースリーク対策）。
- MONITOR_POLL_INTERVAL の不正入力（0 以下や文字列）に対して警告を出し、デフォルトに戻すフェールセーフを追加。

### Security
- .env の取り扱いに関する注意書きを config_setup の生成テンプレートに含め（.env を絶対に Git にコミットしない旨を明記）。

### Notes / Limitations / Known issues
- research/factor_research.py は設計と一部実装が含まれているが、完全実装（すべての因子の最終算出）には追加作業が必要。
- position_sizing の _max_per_stock / price フォールバック時に price=0 の扱いが現在簡易実装（将来的に前日終値や取得原価を用いるフォールバックを検討）。
- process priority / cpu affinity は環境によって権限不足で無効化される可能性があるため、起動スクリプトは警告を出して継続する設計。
- config/*.yaml の内容検証は PyYAML に依存する（未インストール時はパースチェックをスキップして警告）。

---

この CHANGELOG はコードベースの状態に基づく推測的なドキュメントです。実際のリリースノート作成時は、コミット履歴や PR の説明、実施済みのテスト結果を参考に詳細を補完してください。
# CHANGELOG

すべての重要な変更を Keep a Changelog の形式で記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※ この CHANGELOG は、提供されたコードベースの内容から実装意図・動作を推測して作成しています。

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期リリースを追加
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 実行用スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を行う。
    - エンジンはスレッドで起動し、data/stop_requested.flag による外部停止フラグ検知をサポート。
    - 起動時の PID を data/execution.pid に記録する（Engine に渡す仕様）。

  - 監視（Monitoring）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバックし警告を出す。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（monitoring 用テーブル初期化を実行）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - check_once() の例外はログに出力して次回ポーリングに進む耐障害性を確保。

- 設定管理
  - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）。
    - .env/.env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / paper trading 関連 / 監視閾値 / ログ設定等）。
    - PAPER_FILL_MODE の有効値検証（instant, partial, never, reject）や KABUSYS_ENV の許容値検査（development, paper_trading, live）を実装。
    - paper_sqlite_path（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）等のプロパティを提供。

  - .env 初期作成支援ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話式で .env を生成・更新する CLI。
    - 秘匿項目（トークン等）はマスク表示で入力を促す。
    - デフォルト値や選択肢の提示、既存 .env の読み込み・再利用をサポート。
    - 保存時のテンプレートに注意書き（.env を Git に絶対コミットしない等）を出力。

  - 設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在確認、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml ファイルの存在確認・パース検査（PyYAML がインストールされている場合）を実施。
    - 本番環境（KABUSYS_ENV=live）向けの追加警告（LINE 通知設定の未設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。
    - --strict オプションで警告も失敗（exit(1)）として扱うモードを提供。

- ロギングユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - ログディレクトリ（LOG_DIR / 引数 / デフォルト logs/）を自動作成し、ディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみで継続。
    - 既存ハンドラをクリアして重複設定を防止。

- プロセス優先度・CPU アフィニティ設定ユーティリティ
  - set_process_priority / set_cpu_affinity を提供（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux, Darwin, FreeBSD）を吸収する実装。権限不足や未実装環境では警告を出してスキップする安全設計。

- ポートフォリオ構築モジュール
  - ポートフォリオ選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順＋タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）を実装。

  - セクター・レジームによるリスク調整（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap：既存保有のセクター比率が閾値（デフォルト 30%）を超える場合にそのセクターの新規候補を除外。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0/0.7/0.3）を返す。未知のレジームは 1.0 でフォールバック。

  - 株数（ロット）決定ロジック（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - risk_based：risk_pct と stop_loss_pct に基づくポジションサイズ計算。
    - 等配分系：weight に基づく割当て、per-position 上限（max_position_pct）を考慮。
    - lot_size（単元）丸め、cost_buffer を考慮した保守的な費用見積り、aggregate cap（available_cash を超える場合のスケールダウン）と再配分ロジック（端数の扱い）を実装。
    - 価格が取得できない銘柄はスキップし、ログ出力により原因追跡を容易化。

  - portfolio パッケージエクスポート（src/kabusys/portfolio/__init__.py）。
    - 主要関数を top-level に公開。

- Paper Trading 検証レポート
  - Paper Trading の検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計。
    - P95 計算ロジックを実装、閾値に基づく PASS/FAIL 判定（デフォルト閾値: uptime >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200ms）。
    - CLI オプションで期間指定（--from / --to）や DB 指定（--db）をサポート。
    - DB が存在しない場合やテーブルが存在しない場合でも安全にエラーハンドリングし、可能な情報を出力。

- 研究用ファクターモジュール（骨子）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計方針と定数を定義（MA/ATR/期間等）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する予定の骨組みを実装。
    - （ファイル終端で切れているため、一部実装は未完）

### Changed
- 監視用 DB 初期化をエンジン起動時に整合的に呼び出すように統一（init_monitoring_db の冪等呼び出し）。
- ログ出力の標準を stdout に統一（StreamHandler を stdout に設定）し、cron 等でのリダイレクト運用を考慮。

### Fixed
- 環境ファイルパースの堅牢化（src/kabusys/config.py）
  - export 文の扱い、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、空行・コメント行のスキップなどを実装し、.env の多様な書式に対応。

### Security
- .env ファイル生成時に「絶対に Git にコミットしない」旨を明示するテンプレートを導入（config_setup）。

### Notes / Implementation details
- 監視（monitoring）は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する仕様のため、開発環境で監視テーブルを破壊しない設計になっています（ただし、run_execution は paper_trading 時に専用 DB を使用して本番 DB と分離）。
- process_priority.set_process_priority, set_cpu_affinity は権限やプラットフォームに依存する処理のため、安全に失敗をログに落として処理を継続する実装がなされています。
- position_sizing の aggregate cap スケーリングは端数処理（lot_size 単位）と残余キャッシュを最大限活かすロジックを備え、再現性のためにソート順を安定化しています。
- validate_config は PyYAML が存在しない場合に YAML 検査をスキップし、ユーザに警告を出す設計です。

---

今後のリリースでの TODO / 改善候補（コードにコメントとして示されている点）
- position_sizing: 銘柄ごとの lot_size を株マスタに持たせる拡張。
- risk_adjustment.apply_sector_cap: price 欠損時のフォールバック価格（前日終値や取得原価）の導入検討。
- research.factor_research の未完部分（calc_momentum 等の実装継続）。
- 監視・実行コンポーネントのユニットテスト追加、統合テスト（Paper Trading シミュレーション）整備。

以上。
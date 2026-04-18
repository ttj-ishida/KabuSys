# Changelog

すべての重要な変更点をこのファイルに記録します。本ファイルは「Keep a Changelog」の形式に従います。  

リリースは日付順（最新→過去）に並べています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

初回公開リリース。

### 追加 (Added)

- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / 設定管理
  - Settings クラスを実装（src/kabusys/config.py）
    - 環境変数から設定を取得するプロパティ群を提供（J-Quants / kabu API / DB パス / ログ等）。
    - KABUSYS_ENV の妥当性検査（development, paper_trading, live）。
    - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等の paper trading 周りの設定。
    - auto .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込み（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサの強化
    - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ対応、インラインコメント対応などを追加（_parse_env_line）。

- 設定ウィザード CLI（src/kabusys/config_setup.py）
  - 対話形式で .env ファイルを作成/更新するウィザード。
  - 標準項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL 等）を定義。
  - シークレット入力のマスク表示、既存 .env 読み込み、最終確認後にファイル書き出しを実行。

- 設定検証 CLI（src/kabusys/validate_config.py）
  - .env と config/*.yaml の事前検証ツールを追加。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML が存在する場合）を実施。
  - KABUSYS_ENV=live の際の追加ガードと警告。
  - --strict オプションで警告を FAIL 扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine の初期化・起動フローを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用（settings.paper_sqlite_path）し、BrokerClientFactory による MockBrokerClient の使用が想定される（本番 DB と分離）。
    - 停止制御: data/stop_requested.flag による停止、PID ファイル（data/execution.pid）サポート。
    - 実行時にプロセス優先度を高く設定（set_process_priority("high")）。
    - 主要コンポーネントの組み立て例を実装（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）。
  - 監視ポーリング起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor を SQLite（監視 DB）および DuckDB に接続して起動するポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 停止制御: data/stop_requested.flag による検知でループ終了。
    - 監視は環境に依らず本番 sqlite_path を使用する旨の挙動。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しにより監視用テーブルの初期化を保証（冪等）。run_execution/run_monitoring 内で利用。

- ロギング/プロセス管理ユーティリティ（src/kabusys/utils）
  - setup_logging（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - 環境変数/引数からログレベルやログディレクトリを解決。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで続行。
  - set_process_priority / set_cpu_affinity（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差を吸収してプロセス優先度設定を行う。
    - set_cpu_affinity による CPU コア固定機能を提供（psutil ベース）。権限不足等は警告ログでスキップ。

- ポートフォリオ構築関連モジュール（src/kabusys/portfolio）
  - portfolio_builder.py
    - select_candidates: スコア降順の候補選定（同点時のタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限を超える場合に当該セクターの新規候補を除外（unknown セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を算出（未定義レジームはフォールバックして 1.0）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて発注株数を計算。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash 超過時はスケールダウン）、コストバッファ（手数料・スリッページ見積り）を考慮したスケーリングロジックを実装。
    - スケーリング後の残余キャッシュを用いた端数配分アルゴリズム（lot 単位で再配分）を実装。
    - TODO コメントで将来的な lot_map（銘柄別単元）対応や価格フォールバックの検討を記録。

- 研究モジュール（研究用ファクター計算、src/kabusys/research/factor_research.py）
  - モメンタム / MA / ATR / 出来高等のファクター計算の方針実装（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。
  - （実装途中：ファイル末尾で関数定義が続く構成となっているが、計算ロジックの追加が想定される）

- ツールスクリプト
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から統計を集計してレポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）等。
    - 基準値（閾値）を定義し PASS/FAIL 判定を行う。CLI で期間指定（--from/--to）と DB パス指定（--db）に対応。

- パッケージエクスポート
  - src/kabusys/portfolio/__init__.py で主要関数群をパッケージエクスポート。

### 変更 (Changed)

- なし（初回リリースのため、既存コードの変更履歴はなし）

### 修正 (Fixed)

- なし（初回リリース）

### 既知の注意点 / TODO

- research/factor_research.py が実装途中の箇所を含む（ファクター計算ロジックの追加・整備が必要）。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の注記あり。将来的に前日終値等のフォールバックを検討する予定。
  - lot_size は現状全銘柄共通の仮定。将来的に銘柄別単元対応（lot_map）を検討。
- .env 読み込みはプロジェクトルート検出に依存。ルートが見つからない場合は自動読み込みをスキップする仕様。

---

Authors: KabuSys 開発チーム (コードベースから推測して記載)
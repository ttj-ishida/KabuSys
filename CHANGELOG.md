# Changelog

すべての注目すべき変更は Keep a Changelog の形式に従って記載します。  
このファイルは、コードベースの内容から推測して作成した初期リリースのリリースノートです。

全般的な注記
- バージョンはパッケージ定義（src/kabusys/__init__.py の __version__）に準拠しています。
- 日付はこの CHANGELOG 作成日です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18

### Added
- 初期リリース:
  - 日本株自動売買システム「KabuSys」のコアモジュールを追加。
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__=0.1.0 を設定。

- 起動スクリプト / ランタイム:
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動フローを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）。
    - ブローカークライアントを BrokerClientFactory 経由で抽象化。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine をバックグラウンドスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検出で安全に停止。
    - 実行 PID ファイル (data/execution.pid) のサポート。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを起動。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を参照する設計（環境に依存しない）。
    - 停止フラグ（data/stop_requested.flag）検出で監視ループを終了。

- 設定管理:
  - Settings クラス（src/kabusys/config.py）
    - .env/.env.local を自動読み込みする仕組み（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - 環境変数の厳密チェック（KABUSYS_ENV、LOG_LEVEL 等）、便利なプロパティ（is_live, is_paper, is_dev 等）。
    - Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）に対応。
    - PID/kill flag/閾値（CPU/MEM/DISK）等の各種監視設定をプロパティとして提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。

  - .env 設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式で .env 作成・更新が可能。
    - デフォルト値、選択肢、シークレット入力、既存値の再利用に対応。
    - 出力フォーマット（.env 書き込みテンプレート）と注意書きを自動生成。

  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env と config/*.yaml に対する事前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、YAML のパース検証（PyYAML がある場合）。
    - 本番環境 (KABUSYS_ENV=live) 時のガード（LINE 通知の有無、KILL_FLAG_CLEAR_ON_START の注意）を実装。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純関数群）:
  - 候補選定・重み算出（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、同点時は signal_rank 昇順で安定ソート。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合のフォールバックと警告。
  - セクター集中制限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear とフォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method に対応。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金でスケールダウン）を実装。
    - cost_buffer を考慮した保守的なコスト見積りと残差配分ロジック実装。

- ユーティリティ:
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。
    - LOG_DIR 指定・作成に失敗した場合はファイル出力を無効化してコンソールのみで継続。
    - ログレベル解決順（引数 > 環境変数 > デフォルト）。
  - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収。set_process_priority("high"|"normal"|"low")、set_cpu_affinity() を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ツール:
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - paper_trading DB（デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ等を集計しレポート出力。
    - 判定基準（稼働率、成功率、送信率、P95 レイテンシ）および PASS/FAIL 判定を実装。
    - P95 計算、日付フィルタ、コマンドライン引数 (--from, --to, --db) に対応。

- リサーチ基盤（着手済み）:
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム / ボラティリティ / 流動性 / バリュー等の計算を行うための骨格実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計方針を導入。

### Changed
- （初版のため該当なし）

### Fixed
- 安全性・堅牢性の改善:
  - MONITOR_POLL_INTERVAL が不正値の場合、デフォルト（60 秒）にフォールバックして警告出力する実装を追加（run_monitoring.py）。
  - ログディレクトリ作成失敗時は明示的に警告を出し、ファイルハンドラを省略してコンソール出力のみで継続（logging_setup.py）。
  - .env 読み込みでファイルが開けない場合に警告を出して読み込みをスキップ（config.py）。
  - process priority / cpu affinity の実行で権限不足や未対応 OS の場合に例外を投げず警告でスキップ（process_priority.py）。
  - ExecutionEngine 起動前に監視用テーブル（init_monitoring_db）を冪等に初期化しておくことで DB スキーマ未作成時の起動障害を低減。

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- （初版のため特記事項なし）
  - ただし .env は決して Git にコミットしない旨の注意が config_setup の生成ファイルに明記されています。

---

注: この CHANGELOG はリポジトリ内のソースコードから挙動・設計意図を推測して作成したものです。実際の変更履歴／コミット履歴とは差異がある可能性があります。必要であれば各モジュールごとにさらに詳細なリリースノートを作成します。
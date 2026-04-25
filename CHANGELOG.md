# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付は 2026-04-25（本コードベース作成日相当）です。

## [0.1.0] - 2026-04-25

### 追加 (Added)
- 基本パッケージと初回リリースバージョンを追加
  - パッケージバージョン: `__version__ = "0.1.0"` (src/kabusys/__init__.py)

- 実行・監視起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）
    - ExecutionEngine を起動しスレッドでセッションを実行。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用の SQLite DB（`data/paper_trading.db` または環境変数で上書き）を使用し、本番 DB と分離（MockBrokerClient の利用を想定）。
    - 停止制御: プロジェクト直下の `data/stop_requested.flag` を検知してエンジン停止。
    - 実行用 PID ファイルを `data/execution.pid` として管理。
    - リスク管理（RiskManager）・注文管理（OrderManager）・Reconciler 等を組み立てて起動。
    - プロセス優先度を "high" に設定（start 時）。

  - 監視起動スクリプトを追加（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用して監視 DB を初期化。
    - 停止フラグ `data/stop_requested.flag` によるループ終了。
    - プロセス優先度を "high" に設定して起動。

- 設定管理
  - Settings クラス（src/kabusys/config.py）
    - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）、優先順位: OS 環境 > .env.local > .env。
    - 複数のプロパティを定義（J-Quants、kabu API、LINE、DBパス、監視閾値、exec/paper 判定など）。
    - PAPER_FILL_MODE のバリデーション（"instant"/"partial"/"never"/"reject"）。
    - KABUSYS_ENV の値チェック（development/paper_trading/live）。
    - ログレベル検証等のユーティリティ。
    - settings インスタンスを提供。

  - 設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式で .env の初期作成・更新を支援。
    - J-Quants / kabu API / DB パス / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START 等の入力をガイド。
    - 既存 .env の読み込み・マスク表示（シークレットは ****）。
    - .env を生成・保存する `_write_env` を実装（保存時のテンプレート付き）。

  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env と config/*.yaml の基本的な妥当性検査を実行。
    - 必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML のパース確認（PyYAML がインストールされている場合）。
    - `--strict` オプションで警告も失敗扱いにできる。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite DB から集計してレポートを標準出力に生成。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、レイテンシ (avg/max/P95) など。
    - 判定基準（デフォルト閾値）を定義: 稼働率 >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200ms。
    - 日付範囲フィルタ `--from` / `--to`、DB パス指定 `--db` に対応。

- ポートフォリオ構築ライブラリ（純関数）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコアが全て 0 の場合は等分配にフォールバックし警告。

  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中制限適用（apply_sector_cap）：既存保有のセクター比率が上限を超える場合、新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）：`bull`/`neutral`/`bear` に応じて投下資金乗数を返す（未知レジームは 1.0 にフォールバックして警告）。

  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - 各銘柄の発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株丸め（lot_size）、1銘柄上限・aggregate 上限、コストバッファを考慮したスケーリングロジックを実装。
    - 利用可能現金に対するスケールダウンの際、残差を lot 単位で再配分するロジックを搭載。

  - portfolio パッケージエクスポート（src/kabusys/portfolio/__init__.py）

- ユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - setup_logging(app_name, log_dir, level) を提供。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
    - 既存ハンドラを一旦クリアして二重設定を防止。

  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する set_process_priority(level) を提供（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) で最初の N コアにプロセスを固定可能。
    - psutil を利用。権限不足や未サポート OS では警告を出してスキップ。

- 研究用ファクタ計算の骨組み（src/kabusys/research/factor_research.py）
  - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 系ファクタを計算する設計を導入。
  - 定数・設計方針・モメンタム計算関数の雛形（calc_momentum）を含む（prices_daily / raw_financials を参照する想定）。
  - （ファイル末尾が途中までの実装。詳細ロジックは続けて実装する予定）

### 変更 (Changed)
- なし（初回リリースのため新規追加が中心）

### 修正 (Fixed)
- なし（初回リリース）

### 削除 (Removed)
- なし

### 非推奨 (Deprecated)
- なし

### セキュリティ (Security)
- なし

---

注記（実装上の重要ポイント）
- .env の自動読み込みはプロジェクトルートが判定できない場合はスキップされるため、配布後の動作の安全性を確保。
- run_monitoring は監視 DB に対して本番 sqlite_path を常に使用する設計。環境に応じた分離が必要な場合は明示的に設定を変更してください。
- run_execution は paper_trading 環境で本番 DB と切り離された paper_sqlite_path を利用するため、ペーパートレード時に本番データベースへ影響を与えない設計になっています。
- logging_setup と process_priority は実行環境で失敗しても致命的に停止しないよう警告でフォールバックします。

もしリリースノートの粒度（機能ごとの詳細、既知の制限、移行手順など）をさらに細かくしたい場合は、その対象と追加情報（例えば実行手順、環境変数一覧、期待されるディレクトリ構成など）を教えてください。必要に応じて追記します。
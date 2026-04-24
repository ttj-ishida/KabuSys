CHANGELOG
=========

すべての注目すべき変更履歴はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

注記
----
このリリースノートは、提供されたコードベースの内容から推測して作成しています。実際のコミット履歴に基づくものではありません。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-24
-------------------

Added
- 基本実装の初期リリース。
  - パッケージバージョンを 0.1.0 に設定 (src/kabusys/__init__.py)。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag の存在で検知。
    - 監視は本番用 sqlite_path を環境に関わらず使用する実装。
    - プロセス優先度を上げる処理（set_process_priority）を起動直後に実行。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 用専用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント作成、注文管理・リスク管理・reconciler の組み立てと ExecutionEngine の起動を実装。
    - スレッドでエンジンを実行し、stop flag による安全停止処理を実装。
    - 起動時にプロセス優先度を High に設定。

- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順と上書きルール（OS 環境変数の保護）。
    - 複雑な .env パース実装（export 形式、クォート文字列、エスケープ、インラインコメントの扱い）。
    - Settings クラスで主要設定をプロパティ化（J-Quants / kabu API / DB パス / ペーパートレード設定 / 監視閾値 / 環境判定など）。
    - 設定値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の有効値チェック）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。

- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新するツールを追加。
    - シークレット項目はマスク表示、デフォルト値や選択肢の提示、保存確認機能を実装。
    - 保存時に .env テンプレートを生成（Git コミット禁止コメント付き）。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の存在・基本整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、PyYAML の有無に応じた YAML パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告をエラー扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 引数による優先順位解決。
  - utils/process_priority.py
    - Windows と POSIX(Linux/Mac/FreeBSD) を吸収するプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity 設定関数 set_cpu_affinity を追加。
    - 権限不足や未対応プラットフォームでは警告を出して安全にフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選抜する関数。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（スコア全ゼロ時は等分配へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づく候補フィルタリング（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数（未知の値は 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に基づく株数計算、単元株（lot_size）単位で丸め、per-stock 上限・aggregate cap（available_cash）に応じたスケーリング、cost_buffer を用いた保守的コスト見積り、端数の再配分ロジックを実装。
    - 多数のパラメータにより柔軟なリスク管理・制約（risk_pct, stop_loss_pct, max_position_pct, max_utilization 等）を設定可能。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を受けて prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計を追加（設計方針・定数を含む）。モメンタム計算関数の骨子が含まれる（実装途中の箇所あり）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを計算して PASS/FAIL を判定する。
    - P95 計算、日付フィルタ、SQLite DB パスの指定（引数または環境変数）に対応。
    - デフォルト閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200 ms）を定義。

- モニタリング DB 初期化
  - monitoring.monitoring_db:init_monitoring_db を各起動スクリプトから呼び出して監視テーブルの存在を保証（冪等）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし（初期リリース）

補足
- .env の自動読み込みはデフォルトで有効。テスト等で自動ロードを抑止するためには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視データに本番 sqlite_path を使用する設計上の注意点（環境に依存せず本番 DB を参照する）があります。運用時は意図した DB 設定を必ず確認してください。
- 本リリースは機能実装を中心とした初期版です。各モジュールにおいて入出力や外部依存（DB スキーマ、broker 実装、DuckDB テーブル構造など）の整合性確認が必要です。

---
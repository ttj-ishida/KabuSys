CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています（日本語で記載）。

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリースとして主要モジュールを追加。
  - 実行/監視用起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
      - エンジンはデーモンスレッドで実行され、data/stop_requested.flag を検知すると停止する。
      - プロセス優先度を "high" に設定する処理を起動時に実行。
      - 実行用 PID ファイル（data/execution.pid）を扱う。
    - run_monitoring.py
      - SystemMonitor のポーリングループを実行するエントリポイント。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
      - 監視は KABUSYS_ENV にかかわらず production 用の sqlite_path（デフォルト data/monitoring.db）を使用することに注意。
      - 停止は data/stop_requested.flag を監視して行う。
  - 設定管理
    - config.py
      - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - .env/.env.local の読み込み順と上書きルール（OS 環境変数の保護）を実装。
      - .env パーサを強化: export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメントを適切に扱う。
      - Settings クラスを提供し、主要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）と各種デフォルト値・検証ロジックを公開。
      - PAPER_FILL_MODE の有効値検証（instant/partial/never/reject）、KABUSYS_ENV の許容値検証（development/paper_trading/live）、LOG_LEVEL 検証などを実装。
  - 設定補助 CLI
    - config_setup.py
      - 対話式ウィザードで .env を初期作成・更新するツールを実装。
      - シークレット値はマスク表示、選択肢・デフォルト表示、保存前確認をサポート。
      - .env の書式テンプレートを出力（Git 管理禁止の注意喚起含む）。
    - validate_config.py
      - .env と config/*.yaml の事前検証を行う CLI を実装。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイル存在・パースチェック（PyYAML がない場合は警告）などを実装。
      - --strict オプションで警告をエラー扱いにできる。
  - ロギング・プロセスユーティリティ
    - utils/logging_setup.py
      - 共通のログ初期化ユーティリティを提供。StreamHandler（stdout） と TimedRotatingFileHandler（日次、30日分保持）をセットアップ。
      - LOG_LEVEL / LOG_DIR の解決ルール、ディレクトリ作成失敗時のフォールバックを実装。
      - コンソール出力は stdout を使用（cron 等での扱いを想定）。
    - utils/process_priority.py
      - プラットフォーム差を吸収したプロセス優先度設定関数を提供（Windows と POSIX をサポート）。
      - CPU affinity 設定補助（最初の N コアに固定）を実装。
      - psutil の権限エラー等は警告にフォールバック。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（スコア全て 0 の場合は等配分にフォールバック）を実装。
    - portfolio/risk_adjustment.py
      - セクター集中制限 (apply_sector_cap)：既存保有に基づき同一セクターの新規候補を除外するロジックを実装。unknown セクターは上限適用外。
      - レジーム乗数 (calc_regime_multiplier)：regime ラベルに応じた乗数（bull/neutral/bear）を実装。未知レジームは警告のうえ 1.0 にフォールバック。
    - portfolio/position_sizing.py
      - allocation_method（"risk_based"/"equal"/"score"）に応じた株数算出を実装。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン（残差処理で lot 単位で再配分）を実装。
      - cost_buffer を考慮した保守的見積り対応。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計してレポート出力する CLI を実装。
      - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）で Pass/Fail 判定を行う。
      - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。
  - research/factor_research.py（ファクター計算基盤）
    - DuckDB を用いたファクター計算の基盤を追加（モメンタム等の算出ロジックを実装開始）。
    - 設計注記: prices_daily / raw_financials テーブルのみ参照し、結果は (date, code) キーの dict リストで返す方針。

Changed
- なし（初回リリースのため該当なし）。

Fixed
- なし（初回リリースのため該当なし）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Notes / Usage highlights
- 環境変数自動読み込み
  - プロジェクトルートが検出可能な場合、自動で .env（既存 OS 環境変数を上書きしない）および .env.local（上書き可）を読み込みます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視/停止
  - 停止フラグ: data/stop_requested.flag を配置すると監視ループ／エンジンが終了します。
  - 起動時に Kill フラグを自動クリアする設定（KILL_FLAG_CLEAR_ON_START）は本番で誤設定すると危険（validate_config で警告）。
- ログ
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力（30日分保持）。ログディレクトリ作成に失敗した場合はコンソール（stdout）のみで継続。
- 実行例
  - .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 監視開始: python -m kabusys.run_monitoring
  - 実行開始: python -m kabusys.run_execution
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

開発メモ（実装上の注意）
- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path を利用する設計になっているため、開発時に監視データを本番 SQLite と混ぜたくない場合は sqlite_path を明示的に変更してください。
- config の .env パーサは引用符内のバックスラッシュエスケープや inline コメント処理を考慮しており、より堅牢に環境変数を読み込めます。
- position_sizing の aggregate スケールダウンロジックは lot_size 単位での再配分を行うため、端数処理の再現性を確保しています。

（以上）
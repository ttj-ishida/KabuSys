CHANGELOG
=========

すべての変更は Keep a Changelog の方針に準拠して記載しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 2026-04-25
-----------------

Added
- 基本リリース: KabuSys 日本株自動売買システム v0.1.0 を追加。
  - パッケージエントリポイントを定義 (src/kabusys/__init__.py)。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag により制御。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する旨の挙動。
    - duckdb および sqlite3 接続の初期化を行い、例外時はログに出力してループ継続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を利用し、data/paper_trading.db を使用（本番 DB と完全分離）。
    - スレッドでエンジンを実行し、停止フラグまたは終了時に安全に停止/結合する仕組み。
    - PID ファイル管理（data/execution.pid）と停止フラグ対応。
- 設定管理とセットアップ
  - config.py
    - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を探索）。
    - .env 自動読み込み（.env → .env.local、OS 環境変数優先）。自動読み込み無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パースの強化（export 形式、クォート、エスケープ、インラインコメントの扱い）。
    - Settings クラスを提供し、各種環境変数の取得・検証用プロパティを実装（J-Quants、kabu API、DB パス、監視閾値、PAPER_FILL_MODE など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject のみ有効）。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI を追加。
    - J-Quants/Kabu API の秘密情報をシークレット入力として扱う、各種デフォルト値を設定して .env を書き出し。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須/任意環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検証）。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番（live）環境向けの追加ガード（LINE 通知設定の未設定、KILL_FLAG_CLEAR_ON_START 設定等）を実装。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログレベル / ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームに対応したプロセス優先度設定（high/normal/low）を追加。Windows/Linux/macOS を考慮。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応 OS では警告ログを出してスキップ。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコアが全て 0 の場合は等分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（"unknown" セクターは無視）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを追加。allocation_method に応じた株数計算（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限・総投資上限（aggregate cap）を考慮したスケーリング処理、cost_buffer を用いた保守的見積り、残余キャッシュを用いた端数配分ロジックを実装。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH を参照。
    - 稼働率、注文成功率/送信率、リスク却下数、APIレイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を行う。
    - P95 計算及び期間フィルタ（ISO8601 UTC 変換）を実装。閾値はソース内定義（稼働率 >=99% など）。
- リサーチ基盤（骨組み）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity の設計方針と定数を実装）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / マイグレーション
- 初回セットアップ手順の推奨:
  1. python -m kabusys.config_setup で .env を作成
  2. python -m kabusys.validate_config で設定を検証
  3. python -m kabusys.run_monitoring および python -m kabusys.run_execution を必要に応じて起動
- .env 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番起動時は KABUSYS_ENV を適切に設定し、KILL_FLAG_CLEAR_ON_START は誤設定によるリスクを避けるため 0 を推奨します。
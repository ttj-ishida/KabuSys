保持チェンジログ（Keep a Changelog 準拠）形式で、コードベースから推測した変更履歴を日本語で作成しました。

注意:
- 日付は本日（2026-04-18）をリリース日として記載しています。
- 記載内容はソースコードから推測した機能追加・重要挙動の要約です。実際の変更履歴やリリースノートの要件に合わせて必要に応じて修正してください。

CHANGELOG.md
=============

以下は Keep a Changelog の形式に準拠した変更履歴です。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アプリケーションの初期実装を追加。
  - パッケージバージョン: __version__ = "0.1.0"

- 起動スクリプト / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート/data/stop_requested.flag ファイルで検知。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する旨を明記（注意点）。
    - 例外発生時はログに例外を残して次ポーリングまで待機する実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient と data/paper_trading.db を使用（本番 DB と分離）。
    - 実行中は execution.pid を PID ファイルとして管理。停止フラグ検知で Engine.stop() を呼んで安全停止。
    - スレッド実行とデーモン化をサポート。

- 設定管理 / 初期化ツール
  - config.py
    - 設定用 Settings クラスを追加（.env の自動読み込み機能含む）。
    - 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を探索して行う。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パース機能は export 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントに対応。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API、DB パス、PID/kill フラグパス、監視しきい値、環境/ログレベルなど）。
    - PAPER_FILL_MODE の有効値チェック ("instant","partial","never","reject")。
    - 環境値の妥当性チェックで不正値は例外を送出。

  - config_setup.py
    - 対話式ウィザードで .env の初期生成・更新を支援。
    - 各種項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）をインタラクティブに入力可能。
    - シークレット項目は表示マスク、既存 .env の読み込み・再利用に対応。

  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB/SQLITE パスの親ディレクトリ存在チェック（起動時自動作成の注記）。
    - config/*.yaml の存在確認と、PyYAML がインストールされていればパース検証を実施。
    - KABUSYS_ENV=live 時に本番向けの追加警告（LINE 設定、KILL_FLAG_CLEAR_ON_START の危険性など）。
    - CLI オプション --strict をサポート（警告も FAIL 扱いで exit(1)）。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティを追加。
    - stdout 出力（StreamHandler）と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリは引数 > 環境変数 LOG_DIR > デフォルト logs/ の順に決定。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - 既存ハンドラのクリア処理（重複設定防止）。
    - ログレベル指定は引数 > 環境変数 LOG_LEVEL > デフォルト INFO。

  - utils/process_priority.py
    - プロセス優先度設定と CPU affinity 設定を提供。
    - set_process_priority(level) — Windows/Linux/macOS を吸収して high/normal/low を設定（権限不足時は警告でスキップ）。
    - set_cpu_affinity(cpu_count) — 指定コア数にプロセスを固定（サポートされない環境では警告でスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で上位 N を選出（signal_rank をタイブレーク）。
    - calc_equal_weights: 等金額ウェイトを計算。
    - calc_score_weights: スコア比率に基づくウェイト。全スコアが 0 の場合は等金額にフォールバック（警告ログ）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック。既存保有のセクター比率が上限を超える場合に新規候補を除外。unknown セクターは制限対象外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルトフォールバックと警告あり）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数決定ロジック（allocation_method: "risk_based" / "equal" / "score"）。
      - risk_based: 許容損失リスク率と stop_loss_pct を用いてポジションサイズ算出。
      - equal/score: ウェイトに応じた配分。
      - lot_size（単元）で丸め、aggregate cap（available_cash）を越える場合はスケールダウンして端数は残差に基づき追加配分。
      - cost_buffer により手数料・スリッページを保守的に見積もる。

- 解析 / レポート
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - データベース（PAPER_TRADING_SQLITE_PATH または --db で指定）から集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を算出。
    - デフォルト基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づいて PASS/FAIL 判定。
    - CLI オプション: --from, --to, --db。

- リサーチ（計算モジュール）
  - research/factor_research.py（モメンタムなどのファクター計算の下地実装）
    - DuckDB 接続を受け取り prices_daily/raw_financials を参照する設計。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ATR、流動性指標の設計方針と定義を追加。
    - calc_momentum の実装開始（関数シグネチャと定数定義、ドキュメントあり）。（ファイル末尾で実装が途中で切れているため、追加実装が必要）

Changed
- （初期リリースのため特記事項なし）

Fixed
- （初期リリースのため特記事項なし）

Security
- （現時点で特記事項なし）

Notes / Important
- 監視（run_monitoring）は「環境にかかわらず」Settings.sqlite_path（本番監視 DB）を使用する実装になっている。ローカル開発で監視を動かす際は DB パスに注意すること。
- run_execution は paper_trading の場合に paper_sqlite_path（data/paper_trading.db をデフォルト）を使って本番 DB から分離する設計。ペーパートレードと本番 DB の完全分離を意図。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされる。テストや一時的に自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- PAPER_FILL_MODE などの設定は厳密な有効値チェックが入るため、誤った値を設定すると起動時に ValueError が発生する。
- process_priority / set_cpu_affinity は権限やプラットフォームにより実行できない場合がある（警告でスキップ）。

今後の TODO / 改善候補（コードからの推測）
- research/factor_research.calc_momentum 等のファクター計算の実装完了。
- ポートフォリオ構築関連で銘柄別の lot_size を考慮する拡張（TODO コメントあり）。
- 価格欠損時のフォールバック（前日終値や取得原価）を導入して exposure の過小評価を防ぐ改善。
- logging_setup のファイルハンドラ作成失敗時の挙動（現状は警告して stdout へフォールバック）やログフォーマットの微調整。
- validate_config の YAML 検証を強化（スキーマ検証など）。

--- End of CHANGELOG ---
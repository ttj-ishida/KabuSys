Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

[未リリース]
------------

- （現在のスナップショットは初回公開に相当するため、未リリース項目はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本構成・起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、MockBrokerClient を利用する設計を想定。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止、実行 PID ファイルの扱い（data/execution.pid）をサポート。
    - ExecutionEngine を別スレッドで起動、停止フラグ検知でエンジン停止を行うループを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用する仕様。
    - 停止フラグ検知でループ終了、KeyboardInterrupt によるグレースフル終了処理を実装。

- 設定・環境読み込み機能
  - config.py: Settings クラスを実装し、環境変数経由で各種設定を取得（J-Quants / kabuAPI / DB パス / 監視閾値など）。
    - .env 自動ロード機能を実装（プロジェクトルート判定は .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順（OS 環境 > .env.local > .env）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パースは export プレフィックス・クォート・インラインコメントなどを考慮した堅牢な実装。
    - 各種プロパティに入力検証（有効値チェック、必須項目の検出）を実装（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE のバリデーション）。
  - config_setup.py: 対話式ウィザードにより .env を初期作成/更新する CLI を実装。シークレットマスクや選択肢、デフォルト値に対応。
  - validate_config.py: 起動前検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV 検証、DB パスや config/*.yaml の存在チェック（PyYAML 未導入時は警告）、本番向けガード（LINE 設定や KILL_FLAG_CLEAR_ON_START）を実装。--strict オプションで警告を失敗扱いにできる。

- ロギングおよびプロセス運用ユーティリティ
  - utils/logging_setup.py: 統一ロギング初期化ユーティリティを実装。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力（logs/<app_name>.log、30 日保持）を設定。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラの二重登録防止のため初期化時に既存ハンドラをクリア。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定ユーティリティを実装。
    - 標準的なレベル "high" / "normal" / "low" をサポート。権限不足や未対応環境では警告でスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選別。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分を実装。全スコアが 0 の場合は等分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用するフィルタを実装（既存保有時価ベースで判定、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に従った株数算出ロジックを実装。
    - 単元（lot_size）丸め、1 銘柄上限・ポートフォリオ集計上限の考慮、cost_buffer を考慮した保守的見積り、スケールダウン時の端数配分ロジックを実装。

- 解析・研究系（DuckDB ベース）
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / 流動性等を想定）。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。
    - （ファイル末尾は実装途中の断片を含む。将来の実装で具体的な SQL/計算ロジックを補完予定。）

- 運用ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを実装。
    - PAPER_TRADING_SQLITE_PATH（または --db オプション）で DB を指定可能。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）などを算出。
    - 各種閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms）に基づき PASS/FAIL 判定を行う。
    - P95 は簡易的なパーセンタイル計算を実装。

- パッケージ基礎
  - __init__.py: パッケージバージョンを 0.1.0 に設定し、主要サブパッケージを __all__ に公開。

Security
- なし

Changed
- 初回リリースのため変更項目はありません。

Fixed
- 初回リリースのため修正項目はありません。

Removed
- 初回リリースのため削除項目はありません。

Notes / 補足
- デフォルトのデータベース・ログパスや挙動
  - DuckDB: data/kabusys.duckdb
  - 監視用 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
- 停止フラグ・Kill Switch の取り扱い
  - スクリプトは data/stop_requested.flag を参照して外部から安全停止可能。
  - 設定 KILL_FLAG_CLEAR_ON_START により起動時の Kill Flag 自動クリアの挙動を制御（本番では無効を推奨）。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされる（配布後の安全性確保）。

今後の予定（推測）
- research/factor_research.py の完全実装（DuckDB 上での具体的なファクター集計と正規化）。
- ExecutionEngine / BrokerClient 等の詳細実装（本コードベースでは呼び出し先の骨格が参照されているが、具体的なブローカー実装は外部モジュールに依存）。
- テスト・ドキュメント（PortfolioConstruction.md 等参照に基づくテストケース整備）。
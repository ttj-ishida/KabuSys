CHANGELOG
=========

すべての重要な変更は Keep a Changelog の方針に従って記載しています。
リリース日付はコードベースから推測した日付を使用しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-25
-------------------

Added
- 基本機能の初期実装（初回リリース）。
  - 実行エントリ／デーモン類
    - run_execution.py
      - ExecutionEngine を起動するスクリプトを追加。
      - KABUSYS_ENV による paper_trading モードをサポート。paper_trading 時は専用の SQLite（data/paper_trading.db デフォルト）を使用して本番 DB と完全分離。
      - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine を別スレッドで実行する仕組みを実装。
      - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理（data/execution.pid）に対応。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
      - 停止フラグ検知時の安全終了処理と例外発生時のログ化を実装。
  - 設定・運用支援
    - config.py
      - 環境変数ラッパー Settings を追加。プロパティ経由で各種設定（DB パス、ログレベル、KABUSYS_ENV、paper_trading 用設定など）を取得可能。
      - プロジェクトルート自動検出（.git / pyproject.toml を基準）と .env 自動読み込みを実装（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env のパース処理において export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
      - PAPER_FILL_MODE の入力検証、paper_sqlite_path 等のプロパティを追加。
    - config_setup.py
      - 対話式 .env 作成/更新ウィザードを追加。既存値の再利用、シークレット項目のマスク表示、保存確認などを実装。
    - validate_config.py
      - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV の検証、DB パスや config/*.yaml の存在チェック、KABUSYS_ENV=live の追加注意点（LINE 通知設定や Kill Switch 設定）などを実装。--strict モードをサポート。
  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py
      - すべての起動スクリプトから共通で使用するロギング設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテートのファイル出力（TimedRotatingFileHandler、デフォルト logs/）を設定。
      - 既存ハンドラのクリア処理を行い二重設定を防止。ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
    - utils/process_priority.py
      - psutil を用いたクロスプラットフォームのプロセス優先度設定ユーティリティを追加（"high"/"normal"/"low"）。Windows/Linux/macOS（BSD）での差分を吸収。
      - CPU affinity 設定機能も追加（set_cpu_affinity）。権限不足や未対応 API の場合は警告を出してスキップする安全設計。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - シグナルの選定（score 降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（スコア総和が 0 の場合は等配分にフォールバック）を実装。
    - portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）を実装。unknown セクターの扱いやレジームのフォールバックロジックを含む。
    - portfolio/position_sizing.py
      - 株数計算ロジックを実装。allocation_method として "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（投下資金合計が available_cash を超える場合のスケールダウン）を実装。cost_buffer（手数料・スリッページ見積り）を考慮。
      - 価格欠損時のスキップやログ出力を行うなど堅牢性を確保。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH で指定）から稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）などを集計して、人間向けに判定（PASS/FAIL）するレポート生成スクリプトを追加。
      - P95 計算ロジック、期間フィルタ、DB テーブル未存在時のフォールバック処理などを実装。各種閾値（稼働率 99% 等）を定義。
  - 研究用モジュール（骨格）
    - research/factor_research.py
      - Momentum / Value / Volatility / Liquidity の計算方針を定義し、モメンタム計算の骨格（calc_momentum）を追加。DuckDB 経由で prices_daily / raw_financials を参照する設計。実装の一部（関数の続き）はまだ未完（後続実装予定）。

Changed
- なし（初回公開）

Fixed
- .env 読み込み処理の強化
  - export PREFIX, 引用符付き値のバックスラッシュエスケープ、コメント扱いの改善などにより .env の互換性と堅牢性を向上。
- ロギング設定の堅牢化
  - 既存ハンドラを事前に閉じてから再設定することで二重ログ出力を防止。ログディレクトリ作成失敗時のフォールバックを導入。

Security
- なし特記事項。ただし .env を絶対に Git にコミットしない旨を config_setup のヘッダに明記。

Notes / TODO
- research/factor_research.py の一部実装（calc_momentum の続きなど）が途中で終わっており、追加実装が必要。
- pipeline / ExecutionEngine の詳細実装（ExecutionEngine, BrokerClient, OrderManager 等の内部ロジック）はこの差分では外部モジュールとして参照されているため、別途テストと監査が必要。
- process_priority の一部操作は権限が必要（nice 値変更や CPU affinity 設定）。実運用時は実行権限とプラットフォーム互換性を確認してください。

Credits
- 初回実装およびドキュメント化に関連するコード群。README や追加の運用手順は別途整備予定。
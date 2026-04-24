CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
日付はコードベースのスナップショット（本ファイル生成日: 2026-04-24）に基づき推測しています。

Unreleased
----------

- ドキュメント整備・マイナー修正
  - 内部ログメッセージや注釈の改善、型注釈の補強などを行いました（機能的な変更はありません）。
  - research/factor_research.py の実装が途中（コメント・定数・インポート整備済み、関数実装継続中）。

[0.1.0] - 2026-04-24
--------------------

Added
- 実行・監視の起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動エントリポイント。プロセス優先度設定、DB 接続、Broker クライアント生成、ExecutionEngine の起動と停止フラグ対応を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と分離。
    - エンジンはデーモン・スレッドで実行され、data/stop_requested.flag による停止を監視。PID ファイル出力に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトへフォールバック。
    - 停止フラグ（data/stop_requested.flag）検出で安全にループ終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB に記録）。

- 設定管理・ウィザード・検証ツールを追加
  - config.py: Settings クラスを導入。環境変数／.env(.local) の自動読み込み、.env 解析ロジック（クォート・エスケープ・インラインコメントの扱い）を実装。環境値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
  - config_setup.py: .env を対話式に生成・更新するウィザードを追加（シークレット入力マスク・既存値 reuse・保存確認あり）。
  - validate_config.py: 起動前に環境変数と config/*.yaml を検証する CLI を追加。--strict モードで警告を失敗扱いにできる。PyYAML が未インストールでも graceful に警告しスキップ。

- ロギング／プロセス管理ユーティリティを追加
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR／LOG_LEVEL 参照。既存ハンドラの二重登録防止を実装。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度と CPU affinity 設定ユーティリティを追加。失敗時は警告を出して安全にスキップ。

- ポートフォリオ構築関連の純粋関数群を追加
  - portfolio/portfolio_builder.py:
    - select_candidates(): BUY シグナルからスコア降順で候補選定。
    - calc_equal_weights(), calc_score_weights(): 等金額・スコア加重の重み計算（スコア全0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): セクター集中超過時に新規候補を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはログ警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method（risk_based / equal / score）に基づき銘柄ごとの発注株数を計算。単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り、残余キャッシュの再配分ロジックを実装。

- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py: ペーパートレードの SQLite（デフォルト data/paper_trading.db）から期間集計レポートを生成する CLI を実装。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づいて PASS/FAIL を判定。P95 計算・日付フィルタ・欠損テーブルの耐障害処理あり。

- research/factor_research.py（ファクター計算モジュール）を追加（実装途中）
  - モメンタム・ボラティリティ・バリュー等の計算方針と定数を整備。DuckDB 接続を受けて prices_daily などを参照する設計。calc_momentum の骨格と定数が定義済み（関数実装は継続中）。

- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- デフォルト構成・設計上の決定
  - 監視（monitoring）は環境に依存せず本番用 sqlite_path にデータを書き込むように決定（監視データの一元管理）。
  - run_execution は paper_trading 環境時に専用 DB を使用することで、本番データと完全分離する方針を採用。

Fixed
- 環境変数読み込みの堅牢化
  - .env パーサーでクォート内のバックスラッシュエスケープやインラインコメント処理を適切に扱うよう改良。
  - .env.local を .env より優先して上書きする（OS 環境変数は保護）。

Security
- シークレット値の扱い改善
  - config_setup の対話表示や .env 書き出しでシークレット項目（API トークン等）をマスクまたは明示的に扱うようにし、.env を絶対に Git にコミットしない旨の注意文を出力。

Notes / Known issues
- research/factor_research.py は一部実装が未完です。ファクター計算の完全実装とテストが必要です。
- position_sizing の注釈にあるように、価格データが欠損（0.0）の場合にエクスポージャーや発注量が過少見積りされる可能性があります。将来的にフォールバック価格（前日終値等）の導入を推奨します。
- process_priority と CPU affinity は環境により権限エラーや未実装例外が発生しうるため、失敗時は警告を出してスキップする設計です。
- monitoring の設計により、開発環境で監視データを本番 DB に書きたくない場合は sqlite_path を環境変数で切り替える必要があります。

今後の予定 (非拘束)
- factor_research の完成とユニットテスト追加
- ExecutionEngine / SystemMonitor の統合テストと稼働シナリオの自動化
- 銘柄ごとの単元株情報（lot_size）のマスタ取り込みによる position_sizing の改善
- YAML コンフィグのパース検証を CI に組み込み（PyYAML 必須化 or optional の明確化）

---
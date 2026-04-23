# Keep a Changelog — CHANGELOG.md
（この CHANGELOG は与えられたコード内容から推測して自動生成しています。実際のコミット履歴とは異なる場合があります）

全般的な運用方針:
- セマンティックバージョニングを想定（MAJOR.MINOR.PATCH）。
- ここでは初期公開バージョンとして 0.1.0 を記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-23
初期リリース（コードベースから推測）

### Added
- 実行用エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動するためのスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて Engine を起動。デーモンスレッド上でセッションを実行し、stop フラグを監視して安全に停止。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（set_process_priority）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番の sqlite_path を使用して監視情報テーブルを初期化。
    - ディレクトリ下の stop_requested.flag による外部停止フラグ対応。

- 設定・環境管理
  - config.py
    - 環境変数の読み込み・ラッパー Settings を追加。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑止可能。
    - .env パースの堅牢化（export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理など）。
    - 各種設定プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）を提供。
    - KABUSYS_ENV / LOG_LEVEL の検証ロジックを組み込み、Settings オブジェクト経由で利用可能。

  - config_setup.py
    - 対話式 Wizard による .env ファイル生成/更新ツールを追加。
    - J-Quants, kabuAPI, DB パス, LINE 通知など主要な設定項目を対話形式で収集し .env を出力。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（--strict オプションで警告を FAIL 扱い可能）。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL、DB パスや config/*.yaml の存在および PyYAML によるパース検証（PyYAML 未インストール時は警告）を行う。
    - 本番環境（KABUSYS_ENV=live）用の追加ガード（LINE 通知の有無、KILL_FLAG_CLEAR_ON_START の警告等）。

- ポートフォリオ構築ロジック（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による加重配分（全スコアが 0 の場合は等配分にフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価比率を計算し、上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を算出（未知レジームはフォールバックして 1.0 を返す）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出ロジックを実装。
    - 単元（lot_size）丸め、per-stock cap、aggregate cap、cost_buffer（スリッページ・手数料見積り）を考慮したスケーリングロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを提供（StreamHandler → stdout、TimedRotatingFileHandler 日次ローテーション）。
    - 環境変数/引数からログディレクトリ・ログレベルを解決。既存ハンドラをクリアして二重登録を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップして安全に継続。

  - utils/process_priority.py
    - プラットフォームを吸収したプロセス優先度設定（Windows:/POSIX の差分吸収）。
    - CPU affinity の設定ユーティリティ（最初の N コアにピン留め）を提供。
    - 許可エラーや未対応 OS では警告を出して安全にスキップ。

- 解析・レポートツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、レイテンシ（P95）などの指標を算出。閾値（稼働率 99%、fill 90%、send 95%、P95 200ms）を定義して PASS/FAIL を判定。
    - 日付フィルタ（--from/--to）をサポート。PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB パス指定可能。

- 研究用ファクター計算（研究モジュール）
  - research/factor_research.py
    - DuckDB を用いたファクター計算基盤（モメンタム、MA200乖離、ATR、出来高指標等）を用意（設計と一部実装を含む）。関数は DuckDB 接続と target_date を受け取り、prices_daily / raw_financials を参照する設計。

- パッケージ情報
  - __init__.py にてパッケージバージョン __version__="0.1.0" を設定。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Security
- 環境変数の取り扱いに関して、.env を絶対にコミットしない旨を config_setup の出力で明記。
- secret フィールド（J-Quants トークン、kabu パスワード、LINE トークン）はウィザード中にマスク表示。

### Notes / Implementation details（実装からの推測）
- 設計方針として「本番 DB とペーパートレード DB の分離」「起動スクリプトでの優先度向上」「ログの一元化」「設定の自動ロードと検証」「ポートフォリオ構築ロジックは純粋関数で副作用無し」を重視している。
- .env のパースはクォート内のエスケープやコメント処理に対応しており、実運用での柔軟性が考慮されている。
- logging は stdout を利用することで、cron/Task Scheduler 等からのリダイレクト運用を想定している。
- process_priority の設定は権限に依存するため失敗時は警告ログを出して安全に継続する実装になっている。
- Paper Trading 検証レポートは SQL と Python を組み合わせて計算し、DB スキーマが無い場合は N/A を返すなど堅牢性を考慮。

---

今後の追加候補（コード内容からの推測・提案）
- factor_research の完全実装（モメンタム / ボラティリティ / バリュー等の計算ロジックを完了）。
- 単体テストおよび CI 設定（設定パースや position sizing の境界条件等のテスト）。
- Strategy/Execution の連携テスト、ブローカーモックの拡充。
- 銘柄ごとの lot_size を持たせる拡張（現状はグローバルな lot_size を仮定）。

以上。必要であればリリースノートの粒度を増やす（ファイル別の変更一覧や既知の制限事項の追加）こともできます。どの程度の詳細が必要か教えてください。
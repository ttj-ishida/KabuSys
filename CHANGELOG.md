CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

バージョニングは semver を想定します。

Unreleased
----------

### Added
- なし（次回リリースに向けた未完了タスクは下記参照）。

### Known issues / TODO
- research/factor_research.calc_momentum の実装が途中で終端している断片が含まれているため、ファクター計算の完成が必要。
- position_sizing で将来的に銘柄ごとの lot_size をサポートする旨の TODO コメントあり（現状は全銘柄共通の単元株数を想定）。
- risk_adjustment.apply_sector_cap は価格欠損時のフォールバック（前日終値や取得原価など）実装の検討が必要。

0.1.0 - 2026-04-22
------------------

最初の公開リリース（推定）。以下はコードベースから推測できる主要な機能・変更点の要約です。

### Added
- 基本アプリケーション情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 環境設定・読み込み
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env のパースはクォート、エスケープ、コメント、`export KEY=value` 形式に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - Settings クラスを導入し、環境変数経由でアプリ設定を取得（J-Quants、kabu API、DB パス、監視閾値、実行環境判定など）。
  - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等の Paper Trading 向け設定を追加。
  - pid_file / kill_flag 等の監視・運用用設定を提供。

- 設定ファイル関連 CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI（`python -m kabusys.config_setup`）。
  - validate_config: .env と config/*.yaml の検証 CLI を提供（`python -m kabusys.validate_config`）。--strict オプションで警告を FAIL 扱いにできる。
  - validate_config は PyYAML 未インストール時に YAML 検証をスキップするフォールバックと、live 環境向けの追加ガード（LINE トークン、Kill Switch 設定の警告）を実装。

- 実行エンジン / 監視プロセス
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し Mock ブローカー経由で完全分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで実行。
    - data/stop_requested.flag を監視して安全に停止する仕組みを実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - stop flag による停止検知、例外発生時のログ出力とポーリング継続ロジックを実装。

- 監視 DB 初期化 / DuckDB 統合
  - init_monitoring_db を利用して監視用テーブルの存在を保証（冪等）。
  - DuckDB 接続を併用する設計（duckdb は分析用ストア）。

- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティ。
    - LOG_LEVEL / LOG_DIR / app_name による解決をサポート。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応する実装。
    - 権限不足や未対応 OS の場合は安全にスキップして警告をログに残す。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank を考慮）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコア0の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック。既存保有のセクター比率が max_sector_pct を超える場合、新規候補から除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく資金乗数を返す。未知レジーム時は警告してフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: 重み・候補・リスクパラメータに基づき発注株数を決定するアルゴリズムを実装。risk_based / equal / score の allocation_method をサポート。
    - aggregate cap（利用可能現金を超える場合のスケールダウン）と lot_size（単元株丸め）、cost_buffer（手数料/スリッページ推定）を考慮。

- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading の SQLite DB を読み取り、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して Pass/Fail レポートを出力するスクリプトを追加。
    - フィルタ期間指定（--from / --to）、DB パス指定（--db / 環境変数）に対応。
    - P95 計算、NULL/データ不足時の N/A 表示、閾値による判定を実装。

### Changed
- 新規リリースのため変更履歴はなし（初回公開相当）。

### Fixed
- なし（初回公開相当）。

### Removed
- なし。

Notes
-----
- 多くのコンポーネントは純粋関数／DI（依存注入）を意識した設計で、テスト・交換がしやすい構造になっている（例: BrokerClientFactory / duckdb 接続の注入 / sqlite_conn の受け渡し）。
- いくつかの箇所で将来的な改善予定や未完成の実装注記（TODO コメント）が見られるため、次期リリースでは以下が候補となる:
  - factor_research の完成（ファクター計算の完全実装および DuckDB ベースの SQL チェーン）。
  - 銘柄別 lot_size サポートや価格欠損時のフォールバックロジックの実装。
  - 単体テスト・CI の整備（現状ソースからはテストが同梱されている様子は見られない）。

以上。コードベースから推測できる要点をまとめました。必要であれば、各モジュールごとにより詳細な CHANGELOG（機能毎の注記や既知の制限、サンプル使用手順等）を作成します。どのレベルで拡張するか指示してください。
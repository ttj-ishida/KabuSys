CHANGELOG
=========

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。
https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-04-25
------------------

Added
- 基本機能の初期実装を追加（初回リリース）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 DB を使用（data/paper_trading.db がデフォルト）。BrokerClientFactory 経由で MockBrokerClient を切替え可能。
    - デーモンスレッドで ExecutionEngine を起動し、 data/stop_requested.flag による安全な停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - pid ファイルを書き込む仕組み（settings から PID ファイルパスを取得）。
  - run_monitoring.py
    - SystemMonitor をポーリングする監視プロセス起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は環境に関係なく本番用 sqlite_path を参照して監視テーブルを初期化。
    - stop フラグ (data/stop_requested.flag) による終了検知を実装。
  - 設定管理
    - config.py: 環境変数ラッパー Settings を追加。多くの設定値（DB パス、API トークン、閾値、環境種別など）をプロパティ経由で取得可能。
    - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。OS 環境変数を保護する仕組みを採用（.env.local を上書き可）。
    - .env パース処理は export プレフィックス、クォート、バックスラッシュエスケープ、行中コメントなどに対応。
  - CLI ツール
    - config_setup.py: 対話式ウィザードで .env の初期作成／更新を支援する CLI を追加（項目の選択肢、シークレット入力、保存確認など）。
    - validate_config.py: .env と config/*.yaml の事前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV 検証、ログレベル、DB パスの親ディレクトリ確認、YAML パースチェック（PyYAML があれば実行）、本番環境向けの追加ガードを実施。--strict オプションで警告を失敗扱いにできる。
    - tools/paper_verification_report.py: ペーパートレーディング用検証レポート生成スクリプトを追加。期間フィルタ、稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等の集計と PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB 指定可能。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - シグナルの候補選定（スコア降順、同点は signal_rank でタイブレーク）。
      - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分へフォールバック）。
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap を実装（既存保有のセクター比率が閾値を超える場合、新規候補を除外）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピングし、未知レジームは警告のうえ 1.0 にフォールバック）。
    - portfolio/position_sizing.py
      - position sizing の主要アルゴリズムを実装（risk_based / equal / score の各方式）。
      - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、総投下上限（max_utilization）、cost_buffer を考慮した集約スケーリングを実装。
  - utils
    - utils/logging_setup.py: 全アプリケーションで利用する共通ロギング設定ユーティリティを追加。stdout（StreamHandler）と日次ローテート（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして警告を出す。LOG_LEVEL / LOG_DIR を考慮した解決。
    - utils/process_priority.py: psutil を用いたプロセス優先度設定ユーティリティを追加（Windows/Linux/macOS を吸収）。CPU アフィニティ固定関数 set_cpu_affinity も提供。権限不足や未サポート環境では警告を出してスキップ。
  - research
    - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム、移動平均乖離、ATR 等）の骨格を追加。関数インターフェースと定数を定義（モジュールは prices_daily / raw_financials を参照する設計）。

Changed
- パッケージ公開情報
  - __init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ でエクスポート。

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- （初期リリースのため該当なし）

Notes / Known issues / TODO
- research/factor_research.py は一部実装が未完（ファクター計算の SQL/ロジックの続きが必要）。
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合の取り扱いに TODO コメントあり（前日終値や取得原価を用いるフォールバックの検討）。
- position_sizing: 将来的には銘柄別の lot_size をサポートするための拡張を検討中（現状は全銘柄共通 lot_size）。
- run_monitoring は監視用 DB を環境にかかわらず本番 sqlite_path を利用する設計（意図的）。運用時は環境変数の設定に注意すること。

References
- CLI 実行例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 実行プロセス:
    - 監視: python -m kabusys.run_monitoring
    - 実行エンジン: python -m kabusys.run_execution

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴がある場合はそちらを優先してください。）
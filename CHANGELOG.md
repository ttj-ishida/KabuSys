Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。

[Unreleased]

[0.1.0] - 2026-04-17
--------------------

Added
- パッケージ初版を追加（バージョン: 0.1.0）。
- 環境設定・管理
  - Settings クラスを追加。環境変数から各種設定を取得するプロパティを提供（KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, 各種閾値など）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。.env と .env.local を優先度に従ってロードし、既存の OS 環境変数は保護。
  - .env パーサーを実装。export KEY=val 形式、クォート／エスケープ、インラインコメントの取り扱いに対応。
- 設定ウィザード / 検証 CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI（項目定義、既存値再利用、保存確認をサポート）。.env 保存時のテンプレートを出力。
  - validate_config: .env と config/*.yaml の整合性チェック CLI を追加。--strict オプションで警告を失敗扱いにできる。PyYAML 未導入時は YAML 内容検証をスキップして警告出力。
- 実行・監視スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、デフォルトの RiskConfig を設定（max_position_pct 等）。
    - Engine を別スレッドで実行し、data/stop_requested.flag により安全停止。実行中は execution.pid を取り扱う流れを想定。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下／不正値はデフォルトにフォールバックして警告）。
    - 監視は環境にかかわらず本番 sqlite_path（settings.sqlite_path）を使用して起動。
    - 停止フラグファイル（data/stop_requested.flag）検知でループ終了。
- モニタリング DB 初期化
  - init_monitoring_db 呼び出しを run_monitoring/run_execution 起動フローに組み込み、監視用テーブルの存在を保証（冪等処理）。
- ツール
  - Paper Trading 検証レポート生成スクリプト (tools/paper_verification_report.py) を追加。
    - 稼働率、注文成功率（fill rate）、送信率、レイテンシ（P95 等）、リスク却下数を集計してレポート出力。
    - デフォルト DB は data/paper_trading.db。--from/--to/--db オプションをサポート。
    - テーブル不存在やデータ不足時に N/A を扱い、耐障害性を確保。
    - デフォルトの合格基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合は等金額にフォールバックして WARNING）。
  - risk_adjustment: apply_sector_cap（セクター集中上限適用）、calc_regime_multiplier（市場レジームに応じた乗数。bull/neutral/bear をマップし未知値はフォールバック）。
  - position_sizing: calc_position_sizes（allocation_method: risk_based / equal / score をサポート）、
    - 単元株（lot_size）丸め、個別上限（max_position_pct）、全体キャップ（available_cash）に基づくスケールダウン、cost_buffer による保守的見積もり、残余キャッシュを用いた端数配分ロジック等を実装。
- 研究用ファクター計算
  - research/factor_research.py を追加。DuckDB を用いて prices_daily / raw_financials から Momentum / Volatility / Liquidity 等のファクター（1M/3M/6M リターン、MA200乖離、ATR20、20日平均出来高等）を計算する関数を実装。
- ユーティリティ
  - utils/process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加（psutil 依存）。権限不足や未対応 OS の場合は警告を出してスキップ。
- パッケージ情報
  - __version__ を 0.1.0 に設定。公開 API (__all__) を定義。

Changed
- 初版のため無し。

Fixed
- レポート／検証系 CLI がテーブル不存在・データ不足な場合でもクラッシュしないよう堅牢化（OperationalError の捕捉と N/A 表示）。
- .env 読み込みで既存の OS 環境変数を保護する仕組みを実装（.env.local の上書き時も OS 環境変数を上書きしない）。

Deprecated
- 初版のため無し。

Removed
- 初版のため無し。

Security
- .env ファイルは絶対に Git にコミットしない旨を config_setup の生成ファイルヘッダに明記。
- Settings._require は必須環境変数未設定時に ValueError を発生させ起動を防止することにより、重要なトークン等の未設定を検出。

Notes / Usage
- 主なエントリポイント:
  - 環境ウィザード: python -m kabusys.config_setup
  - 設定検証:      python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動:      python -m kabusys.run_monitoring
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔を秒単位で上書き（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告。
- Paper Trading（KABUSYS_ENV=paper_trading）は監査／テストのため本番 SQLite を使わず PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようと試みる。権限がない場合は警告を出して続行。

既知の制約 / TODO
- position_sizing の lot_size は現状全銘柄共通（将来的には銘柄別 lot_map に拡張予定）。
- apply_sector_cap は price_map の欠損（0.0）によりエクスポージャーが過少見積りされ得るため、将来的に価格フォールバック（前日終値等）を導入して改善する予定。
- research/factor_research は DuckDB の prices_daily / raw_financials の存在・整合性を前提とするため、データ準備手順のドキュメント化が必要。

----
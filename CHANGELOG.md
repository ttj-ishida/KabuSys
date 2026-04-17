# Changelog

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
リリース方針: SemVer 準拠。

## [0.1.0] - 2026-04-17

### Added
- 初回公開リリース。
- 基本コア:
  - パッケージ情報: kabusys パッケージ（__version__ = 0.1.0）。
- 実行用スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager（RiskConfig）、Reconciler、ExecutionEngine の組み立てと実行ループ。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止、実行用 PID ファイル出力サポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - 停止フラグファイル検知でループを終了。
- 設定関連:
  - config.py: 環境設定読み取りモジュールを追加。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込み順序: OS 環境 > .env.local > .env。
    - .env パースロジックは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメントを考慮。
    - Settings クラスを提供（各種環境変数をプロパティで取得、バリデーション含む）。
    - PAPER_FILL_MODE 等の値検証とデフォルト値。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。
    - 秘匿値のマスク表示、選択肢・デフォルト表示、保存前の確認、.env 書き出し（テンプレートヘッダ付き）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース検証（PyYAML があれば）。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py:
    - select_candidates, calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中上限により候補を除外、"unknown" セクターは上限適用しない）、calc_regime_multiplier（regime による乗数: bull=1.0, neutral=0.7, bear=0.3。未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes（allocation_method: risk_based / equal / score、単元株（lot_size）に丸め、per-stock / aggregate cap、cost_buffer による保守的見積り、スケーリングと残差処理）。
  - portfolio/__init__.py: 主要関数をエクスポート。
- 解析・リサーチ:
  - research/factor_research.py:
    - DuckDB を用いたファクター計算ユーティリティ（モメンタム、ボラティリティ等）。prices_daily テーブル参照で mom_1m/3m/6m、MA200 乖離、ATR、平均出来高等を計算。
- ツール:
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を計算し PASS/FAIL を判定するしきい値（デフォルト）を提供。
    - DB パス指定は --db または PAPER_TRADING_SQLITE_PATH 環境変数。
- ユーティリティ:
  - utils/process_priority.py:
    - プラットフォーム差を吸収したプロセス優先度設定（Windows の PRIORITY_CLASS、POSIX の nice 値、及び CPU affinity 設定関数 set_cpu_affinity）。
    - 権限不足・未サポート環境で警告しスキップ。

### Changed
- （初回リリースのため過去変更なし。実装上の設計注記を README/ドキュメントに反映することを推奨。）

### Fixed
- （初回リリースのため修正履歴なし。）

### Notes / Implementation Details
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる（配布後の動作を考慮）。
- run_monitoring は Monitoring に対して本番用 sqlite_path を使う設計（環境に依存せず一貫した監視データを保持するため）。
- run_execution は paper_trading 時に DB を分離することで本番データの汚染を防止する。
- 設定の厳格な検証（validate_config）と対話ウィザード（config_setup）を組み合わせることで、初期セットアップと本番移行時の安全性を高める設計。
- 一部関数は外部依存（psutil、duckdb、PyYAML 等）を利用するため、実行環境にこれらのパッケージが必要。

### Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0 や None）だと見積りが不正となる可能性があり、将来的にフォールバック価格（前日終値や取得原価）を導入予定。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターは現状上限適用外。運用ポリシーによっては扱いを変更する必要あり。
- process_priority.set_cpu_affinity:
  - プラットフォーム差分や権限によっては設定に失敗することがある（警告を出して安全にスキップ）。

---

今後のリリースでは、ユニットテストの拡充、ドキュメント（API リファレンス・設計文書）の整備、運用ツールの改良（監視アラート、LINE 通知統合）の強化を予定しています。
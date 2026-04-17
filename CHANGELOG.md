# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
リリース日は自動生成時点（この CHANGELOG はコードベースから推測して作成されています）です。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回公開リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` として定義。

- 実行系 / デーモン類
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全停止。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出し。
    - 監視データは設定にかかわらず本番用 sqlite_path を使用して初期化。
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - `KABUSYS_ENV=paper_trading` の場合は専用の paper trading SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 等の組立てと ExecutionEngine の起動処理を提供。
    - 停止フラグ検知での安全停止、実行 PID 出力（data/execution.pid）。

- 設定管理・ウィザード・検証
  - Settings クラス（src/kabusys/config.py）を実装。
    - 環境変数自動ロード（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
    - 多数のプロパティを定義（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境判定等）。
    - `PAPER_FILL_MODE` の妥当性検証（"instant"|"partial"|"never"|"reject"）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証。
  - 環境設定ウィザード CLI（src/kabusys/config_setup.py）を追加。
    - 対話式で .env を初期作成・更新可能。項目・説明・デフォルト・シークレットマスク表示等を提供。
    - 書き込みはテンプレート形式で .env に出力。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在/パース検証（PyYAML がある場合）。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 本番環境（live）向けの追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコアが全て 0 の場合は等金額配分にフォールバックして警告。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - セクター集中制限の適用（apply_sector_cap）。既存保有を考慮して同一セクターが上限を超える場合に当該セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数の計算（calc_regime_multiplier）：bull/neutral/bear をマップし未知値はフォールバック。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - position sizing ロジック（risk_based / equal / score）を実装。ロット（lot_size）丸め、1銘柄上限、aggregate cap のスケーリング、cost_buffer 考慮の実装。

- 監視・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を算出。
    - 合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義し PASS/FAIL 判定を表示。
    - 日付レンジ指定 (--from / --to) と DB 指定 (--db / 環境変数 PAPER_TRADING_SQLITE_PATH) に対応。

- 研究・ファクタ計算
  - factor_research（src/kabusys/research/factor_research.py）を追加（DuckDB を利用したファクタ計算）。
    - Momentum（1M/3M/6M、MA200 乖離）、Volatility（ATR20 等）、流動性指標等の計算ロジック（prices_daily テーブル参照）。
    - DuckDB の SQL ウィンドウ関数を用いた効率的な実装。データ不足時の None ハンドリング。

- ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows / POSIX に対応）。
    - CPU affinity 設定関数（set_cpu_affinity）を追加。権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- 初期 DB 初期化ヘルパ
  - monitoring DB 初期化用ユーティリティ（import 参照: src/kabusys/monitoring/monitoring_db.py の初期化呼び出し箇所あり。init_monitoring_db を使用して監視テーブルを冪等に確保）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / ドキュメント的な補足
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）を起点に行われるため、配布後や任意の CWD からの実行でも動作するよう設計されています。
- .env 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。
- run_execution は paper_trading モード時に本番 DB と完全分離するため、ペーパートレードの検証が容易です。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告ログを残して処理を継続します。

---

今後の改善候補（未実装・TODO としてコード内にコメントあり）
- position_sizing: 銘柄別の lot_size（マスタ）のサポート拡張。
- risk_adjustment: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価等）の利用。
- factor_research: さらに多くのファクターや z-score 正規化のユーティリティ統合（kabusys.data.stats との連携参照）。

[0.1.0]: https://example.com/releases/0.1.0 (初回リリース)
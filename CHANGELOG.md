# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
このファイルはコードベース（現状バージョン 0.1.0）の機能・導入事項をコードの内容から推測してまとめたリリースノートです。

## [0.1.0] - 2026-04-17

まずの初期リリース（推測）として、以下の主要機能・ユーティリティを追加しました。

### 追加 (Added)
- 全体
  - パッケージ初期版を追加。パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - DuckDB/SQLite を用いた分析・監視基盤を導入（duckdb, sqlite3 を利用）。

- 実行/監視関連
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時はペーパートレード専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動する仕組みを導入。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) によるプロセス制御をサポート。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を用いた単回チェック loop（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可、デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を参照（環境に依存しない監視 DB 利用）。
    - stop フラグの検知・ログ記録・例外ハンドリングを実装。

- 設定・環境管理
  - Settings クラスによる環境設定管理を追加（src/kabusys/config.py）。
    - .env ファイル（.env/.env.local）自動ロード機能（自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）。
    - .env の高度なパース（export プレフィックス、シングル/ダブルクォートのエスケープ処理、インラインコメント処理）に対応。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL、閾値設定など）。
    - env 判定（development / paper_trading / live）やユーティリティプロパティ（is_live, is_paper, is_dev）を実装。
  - 対話式の .env 設定ウィザードを追加（src/kabusys/config_setup.py）。
    - よく使う設定項目を対話形式で入力可能。既存 .env の読み込み・既存値の再利用が可能。
    - .env の書き出しテンプレートを提供（注記: .env を Git にコミットしない旨を明示）。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML があれば実際にパース）などを実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（Portfolio）モジュール
  - 銘柄候補選択、重み計算（等配分・スコア加重）を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順・タイブレークルールを実装。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化、ゼロスコア時に等配分へフォールバック（warning ログ）。
  - セクター集中リスク制御とレジーム乗数を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは 1.0 へフォールバック（warning ログ）。
  - ポジションサイズ計算を実装（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method ("risk_based", "equal", "score") に応じた株数計算、lot_size（単元株）で丸め、max_position_pct／max_utilization／コストバッファを考慮した aggregate cap（スケールダウン）ロジックを実装。
    - risk_based 時に stop_loss_pct/risk_pct を用いた決定方法を提供。
    - 各所で価格欠損時のスキップやログ出力を行う。

- リサーチ / ファクター計算
  - DuckDB 接続を利用したファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR 等）、流動性指標等を計算するための関数骨格を提供。
    - DuckDB 上の prices_daily テーブルを参照し、ウィンドウ関数を活用した効率的な集計を実装。
    - データ不足時に None を返す等の堅牢性を確保。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX 系（Linux, Darwin, FreeBSD）を考慮して優先度を設定（psutil に依存）。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応環境では警告ログを出して安全にスキップ。
  - tools に Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - ペーパートレード用 SQLite から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して標準出力にレポートを出力。
    - しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200 ms）に基づく PASS/FAIL 判定を実装。
    - コマンドラインで --from/--to/--db オプションを提供。

### 変更 (Changed)
- 環境依存の挙動の整備
  - 監視関連はどの環境でも本番用 sqlite_path を参照する（run_monitoring.py: 明示的に本番 DB を使用）。
  - run_execution.py は KABUSYS_ENV=paper_trading の場合に専用 DB を使って本番 DB と分離する設計。

### 修正 (Fixed)
- エラーハンドリングを強化
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもログを残し次のポーリングを継続するように保護。
  - config/_load_env_file: .env 読み込み失敗時に warnings.warn で通知し処理を続行。
  - process_priority の権限・未実装例外を捕捉して警告を出すように修正（環境による起動失敗を回避）。

### ドキュメント（コード内コメント）
- 各モジュールに設計方針や注意点を注釈（PortfolioConstruction.md / StrategyModel.md に言及するコメントなど）。
- .env の扱い（自動ロード順序・保護キー）の説明を追加。

### 互換性 / 注意点 (Notes)
- 必須ランタイム / ライブラリ:
  - psutil（プロセス優先度・CPU affinity）、duckdb（分析用）、sqlite3（標準ライブラリ）を使用。
  - config 検証で YAML 検証を行う場合は PyYAML が必要（未インストールなら YAML 検証はスキップされ警告）。
- 環境変数の重要点:
  - JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD は必須。未設定の場合は Settings._require が例外を投げます（起動前に validate_config の実行を推奨）。
  - KABUSYS_ENV は development / paper_trading / live のいずれかのみ有効。live 時は追加の注意（LINE トークン等）を喚起。
  - MONITOR_POLL_INTERVAL に不正な値を渡すとログ警告のうえデフォルト（60 秒）へフォールバック。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により .env の自動ロードを抑止可能（テスト等で有用）。
- ファイルベースの制御:
  - 停止フラグ (data/stop_requested.flag) により run_monitoring/run_execution 両方が停止・起動抑止を行う。PID ファイル（data/execution.pid 等）により実行プロセスの管理が可能。
- ペーパートレード:
  - paper_trading 環境では MockBrokerClient を用い、データは data/paper_trading.db（デフォルト）へ記録するよう想定。実環境と完全分離。

### 既知の制限 / TODO
- position_sizing の lot_size は現在全銘柄共通（将来的に銘柄別 lot_map へ拡張予定）。
- apply_sector_cap の価格欠損時のエクスポージャー算出は過少見積の可能性があり、将来的に前日終値や取得原価でのフォールバックを検討。
- factor_research は prices_daily / raw_financials の存在に依存。データ不足時は None を返す実装のため、前処理で適切にデータを整備する必要あり。

---

今後のリリースでは、テストケースの充実（特にポジション計算のエッジケース、スケールダウンアルゴリズム）、銘柄別単元対応、より詳細な監視アラート（LINE通知等）の実装・統合が想定されます。
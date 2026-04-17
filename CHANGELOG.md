# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成したリリースノートです。

全般
- リリースバージョン: 0.1.0
- 日付: 2026-04-17

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - __init__.py にバージョン情報を追加。
- 環境・設定管理
  - Settings クラス実装（kabusys.config）。
    - 各種環境変数をプロパティ経由で取得（J-Quants / kabuステーション / LINE / DB / 監視 / システム設定など）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL 等）とデフォルト値を提供。
    - paper_trading 用の paper_sqlite_path、PAPER_FILL_MODE の検証等を実装。
  - .env 自動読み込み機能を導入（プロジェクトルートに基づく、自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env ファイルのパーサ実装（クォート・エスケープ・コメント取り扱いに対応）。
- 設定支援ツール
  - 対話式環境設定ウィザード CLI（kabusys.config_setup）。
    - .env の初期作成・更新を対話的に支援。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）を扱う。
  - 設定検証 CLI（kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL などの妥当性検証。
    - config/*.yaml ファイル存在チェックおよび PyYAML があればパース検証を実行。
    - --strict オプションで警告を FAIL 扱いにするモードを提供。
- 実行 / 監視スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）。
    - ExecutionEngine を組み立て・起動する起動スクリプトを追加。
    - BrokerClientFactory 経由で実行環境に応じたブローカークライアントを生成（paper_trading 時は Mock を使用し DB を分離）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててエンジンをスレッドで実行。停止フラグファイルで安全停止を行う。
    - paper_trading 環境では専用 SQLite（デフォルト: data/paper_trading.db）を使用。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）。
    - SystemMonitor のポーリングループを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照する挙動を明示。
    - 停止フラグファイルを検知して正常終了。
- モニタリング DB 初期化ユーティリティ（init_monitoring_db の利用箇所を追加）。
- 実行時プロセス制御ユーティリティ（kabusys.utils.process_priority）。
  - set_process_priority(level) を追加し Windows/Linux/macOS の差分を吸収してプロセス優先度を設定。
  - set_cpu_affinity(cpu_count) を追加（指定があれば最初 N コアに固定）。
  - psutil を使用し、権限不足や未対応環境は警告でスキップする堅牢性を確保。
  - run_execution / run_monitoring 起動時に優先度を "high" に設定する処理を追加。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコア全てが 0 の場合は等金額配分にフォールバックして警告を出す。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - apply_sector_cap は "unknown" セクターを上限適用対象外とする。
    - calc_regime_multiplier は bull/neutral/bear に対する乗数を返す（未知レジームは 1.0 でフォールバックし警告）。
  - position_sizing: 株数算出ロジック（calc_position_sizes）。
    - allocation_method に応じた株数決定（risk_based / equal / score）。
    - 単元株数（lot_size）対応、最大ポジション上限・投下資金上限・aggregate cap（スケーリング）実装。
    - cost_buffer を考慮した保守的な投資額計算。
    - スケールダウン時に remainder を考慮して lot 単位で追加配分するアルゴリズムを実装。
    - TODO コメントにより将来の拡張点（銘柄別 lot_size や価格フォールバック）を明示。
- リサーチ / ファクター計算（kabusys.research.factor_research）
  - Momentum・Volatility 等のファクター計算関数（calc_momentum, calc_volatility）を追加。
    - DuckDB で prices_daily テーブルを参照し、1M/3M/6M リターン、MA200 乖離、ATR、20日平均出来高等を算出。
    - スキャン窓や欠損データの取り扱いを設計に含む。
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を出力。
    - 判定閾値を定義（稼働率 99%、fill_rate 90% 等）して PASS/FAIL 判定を出す。
    - p95 の計算ロジック、日付フィルタリング、DB 存在チェックを実装。
- DB 関連
  - DuckDB と SQLite 両方を想定した接続パターンを導入（デフォルトパス: data/kabusys.duckdb, data/monitoring.db）。
  - 監視テーブルの初期化呼び出し（init_monitoring_db）をエンジンスクリプトおよび監視スクリプトで行い、冪等性を確保。

### Changed
- 新規リリースにつき該当なし（初期リリース）。

### Fixed
- 新規リリースにつき該当なし（初期リリース）。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数の設定ウィザードで .env を生成する際に、.env を Git にコミットしない旨を明記（セキュリティ注意喚起）。

### Notes / Migration / Known issues
- .env 自動ロード:
  - 自動ロードはプロジェクトルート（.git または pyproject.toml 存在箇所）を基準に行います。配布後にプロジェクトルートが見つからない場合は自動ロードをスキップします。
  - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR の挙動:
  - run_monitoring は MONITOR_POLL_INTERVAL でポーリング間隔を制御可能（不正な値の時は 60 秒にフォールバック）。
  - 監視は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用するように実装されています。テスト・ペーパートレードと監視 DB を分離したい場合は運用手順に注意してください。
- Paper Trading:
  - run_execution は KABUSYS_ENV=paper_trading の場合に専用の paper_trading SQLite を使用します（デフォルト: data/paper_trading.db）。本番 DB とは完全分離されます。
- TODO / 将来の改善点（コード内コメントより）
  - position_sizing: 銘柄別の lot_size をサポートする拡張（今はグローバル lot_size を想定）。
  - risk_adjustment: 価格データが欠損した際のフォールバック価格（前日終値や取得原価）を使う改善。
- 依存関係:
  - PyYAML がない場合、validate_config は YAML の内容検証をスキップし警告を出します。YAML 検証が必要な場合は PyYAML をインストールしてください。
  - psutil を利用（プロセス優先度 / CPU affinity）。権限がない環境では設定がスキップされ警告になります。

---

この CHANGELOG は、ソースコードの構造・コメント・実装から推測して作成した要約です。運用上の正確なリリースノートや変更履歴が必要な場合は、プロジェクトのコミット履歴（Git log）や正式なリリースノート作成者へ確認してください。
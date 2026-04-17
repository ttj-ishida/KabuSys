CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に従い、リポジトリ内のソースコードから推測して作成した変更履歴です。
リリース日付はソースから明示されていないため省略しています。

なお、本ファイルはコードの構造・コメント・実装から推測した内容を記載しており、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

- なし

## [0.1.0] - 初期リリース

### Added
- 全般
  - パッケージ初期バージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - ログ出力は標準 logging を使用する設計。

- 環境設定・検証・ウィザード
  - .env ファイルの自動読み込み機能を追加。プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込む（kabusys.config）。
  - .env パーサーは export 形式やクォート、行内コメント、エスケープを考慮して堅牢にパースする実装を追加（kabusys.config._parse_env_line）。
  - 環境設定ウィザード CLI を提供（python -m kabusys.config_setup）。対話式で .env を作成・更新できる（デフォルトや秘匿項目表示など対応）。
  - 設定検証 CLI を提供（python -m kabusys.validate_config）。必須環境変数や config/*.yaml の存在・パースなどを検査し、エラー/警告/情報を出力。--strict による警告の FAIL 扱いオプションあり。

- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカー抽象、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）による起動/停止制御をサポート。
  - システム監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバック。
    - Monitoring は環境にかかわらず production sqlite_path を使用して監視データを格納。
    - 監視用 DB テーブルを初期化（init_monitoring_db）してから監視ループを実行。

- データベース / 分析
  - DuckDB を分析用 DB として利用する設計（Settings.duckdb_path）。
  - Paper Trading 用検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などの指標を算出し PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで指定可能。
    - 判定用のしきい値（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）を定義。

- ポートフォリオ構築（純関数群）
  - 候補選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順ソート、同スコア時は signal_rank の昇順でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重。全スコアが 0 の場合は等配分にフォールバックして警告を出力。
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、そのセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告を出して 1.0 にフォールバック。
  - 株数決定・リスク制限・単元丸め（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method に応じて発注株数を計算（risk_based / equal / score）。
    - risk_based: 許容リスク率・損切り率から理論株数を算出し単元（lot_size）で丸める。
    - equal/score: 重みと portfolio_value を用いて per-position 上限や aggregate cap を考慮。
    - aggregate cap を超えた場合はスケールダウンし、残余キャッシュに基づいて小数端数を lot 単位で再配分するアルゴリズムを実装。
    - 単元やコストバッファ（手数料・スリッページ見積り）に対応。

- 研究用ファクター計算
  - ファクター計算モジュールを追加（kabusys.research.factor_research）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算。DuckDB の prices_daily テーブルを利用。
    - calc_volatility: ATR（20日）、相対 ATR、20日平均売買代金、出来高比率等を計算する（実装途中のコメント有）。
    - 入力データ不足時は None を返すように設計。

- ユーティリティ
  - process_priority ユーティリティを追加（kabusys.utils.process_priority）。
    - set_process_priority(level): Windows / POSIX を吸収して優先度（high/normal/low）を設定。未対応 OS はスキップして警告。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定する機能。アクセス権限不足等は警告を出してスキップ。

- 設定オプション・デフォルト
  - 多数の環境変数に対する Settings プロパティを提供（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, しきい値等）。
  - PAPER_FILL_MODE は instant/partial/never/reject のみを許容し、不正値は ValueError。
  - KILL_FLAG_CLEAR_ON_START のサポート（本番環境では注意喚起）。

### Fixed
- 初期リリースのため特定のバグフィックス履歴はなし。コード内に例外処理・フォールバック処理を導入して堅牢性を確保（例: 環境変数パース不正時のフォールバック、DB がない場合のレポート時の扱い、process_priority の権限エラー無視など）。

### Changed
- 初回リリースのため変更履歴なし。

### Removed
- なし

### Security
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストや CI の安全対策）。
- .env 作成時に「絶対に Git にコミットしないこと」という注記を README 的に出力（config_setup）。

### Known issues / TODOs / 注意点
- apply_sector_cap:
  - price_map に price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価等のフォールバックを検討する必要あり。
- position_sizing:
  - lot_size は現状グローバルな単一値（デフォルト 100）。将来的には銘柄別 lot_map に拡張する計画のコメントあり。
- research.factor_research のボラティリティ計算部はソースの途中で切れている（本CHANGELOG作成時点のコード断片に基づく）。実装が続く可能性あり。
- run_monitoring は Monitoring の DB に production sqlite_path を常に使用するため、運用時の DB 指定に注意が必要。
- 本番（KABUSYS_ENV=live）における重要設定（LINE 通知設定、KILL_FLAG の自動クリア設定など）に関する警告ロジックあり。運用前に validate_config を実行し注意喚起を確認することを推奨。

---

参考: 主な CLI / スクリプト
- python -m kabusys.config_setup : .env 対話式ウィザード
- python -m kabusys.validate_config : 設定検証
- python -m kabusys.run_execution : ExecutionEngine 起動
- python -m kabusys.run_monitoring : SystemMonitor ポーリング起動
- python -m kabusys.tools.paper_verification_report : Paper Trading 検証レポート生成

以上。
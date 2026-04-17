Keep a Changelog に準拠した変更履歴（日本語）
======================================

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

変更履歴
-------

### [0.1.0] - 2026-04-17 (初回リリース)
Added
- 基本アプリケーション構成と CLI/ツール群を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 実行時にプロセス優先度を "high" に設定。
    - 監視用 SQLite は環境にかかわらず本番（設定された sqlite_path）を使用するよう実装。
    - 停止はプロジェクトルート/data/stop_requested.flag によるフラグ検知で行う。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用の専用 SQLite（data/paper_trading.db 既定）に記録して本番 DB と完全分離。
    - プロセス優先度を "high" に設定、実行中の PID 管理・停止フラグ対応。
    - リスク管理・オーダー管理・Reconciler を組み合わせてエンジンを起動する流れを実装。
- 設定管理
  - config.py
    - 環境変数／.env 読み込みと Settings クラスを実装。
    - 自動 .env ロードの優先順位: OS 環境変数 > .env.local > .env（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
    - .git/pyproject.toml を基準にプロジェクトルートを自動探索。
    - 各種設定プロパティ（DB パス、paper_trading DB パス、ログレベル、閾値等）と値検証ロジックを提供。
    - PAPER_FILL_MODE 等の列挙的な値検証を実装。
- 設定ツール／検証
  - config_setup.py
    - .env の初期作成・更新の対話式ウィザードを追加。
    - 主要な設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 等）を対話的に設定・保存。
    - 保存前の確認、シークレット項目は表示マスク。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML ファイルのパース検証（PyYAML があれば実行）を実装。
    - `--strict` オプションで警告を FAIL 扱いにする機能を追加。
- 監視 DB 初期化
  - monitoring.monitoring_db モジュールの初期化呼び出しを run_monitoring/run_execution で使用（監視テーブルの冪等な準備）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を追加。
    - スコア合計が 0 の場合は等配分にフォールバックし警告を出す実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（売却予定銘柄を除外できる）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear マッピング、未定義レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出 calc_position_sizes を追加。
    - allocation_method: "risk_based" / "equal" / "score" に対応。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した安全なスケーリングロジックを実装。
- ユーティリティ
  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定関数 set_process_priority(level) を追加。失敗時は警告を出してスキップ。
    - CPU affinity を固定する set_cpu_affinity(cpu_count) を追加（未対応環境では警告）。
- リサーチ
  - research/factor_research.py
    - DuckDB 接続を用いたファクター計算モジュールを追加。
    - モメンタム（1m/3m/6m リターン、MA200 乖離） calc_momentum、ボラティリティ・流動性指標 calc_volatility を実装（DuckDB SQL を利用して prices_daily テーブルから算出）。
    - 設計上は純粋関数（DB 参照は受けるが副作用なし）、結果は (date, code) ベースの dict リストを返す。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）からデータを集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を表示。
    - PASS/FAIL の判定基準（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms など）を定義。
    - 日付フィルタ (--from / --to) と --db オプションに対応。DB が存在しない場合はエラー表示して終了。
- パッケージエクスポート
  - portfolio パッケージで主要関数を __all__ でエクスポート。

Changed
- 初回公開のため既存の設計仕様やドキュメントに合わせてコード構成を整理（モジュール分割、CLI の追加、Settings による集中管理）。

Fixed
- （初回リリース）なし（実装段階で想定される例外処理やフォールバックを入れているため、実用上の安定性を高める実装を含む）。
  - process_priority / cpu_affinity で権限不足等の例外を捕捉し警告でスキップするようにした。
  - .env パーサーはクォート・エスケープ・インラインコメントに対応し、不正行を無視する耐性を持たせた。

Security
- 秘密情報（API トークン等）は config_setup の対話でマスク表示し、.env をコード管理に絶対コミットしない旨の注意を追記。

Notes / 補足
- run_execution は paper_trading 環境では本番 DB を触らない設計になっているため、実機試験時に DB 分離に注意する必要があります。
- .env の自動ロードを無効化したいテスト等の用途には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- DuckDB を使用したファクター計算は prices_daily / raw_financials テーブルの存在を前提としています。YAML ベースの設定ファイル（config/*.yaml）は validate_config で存在確認／パース検証できます（PyYAML が必要）。
- いくつかのモジュール（例: ExecutionEngine / BrokerClientFactory / SystemMonitor 等）はここに含まれる起動フローから呼び出される前提で実装されています。これらの内部実装は本リリースの範囲外（既存実装を利用）です。

今後の予定（予定的メモ）
- stocks マスタに銘柄ごとの lot_size を持たせ、position_sizing の lot_size を銘柄別にする拡張。
- apply_sector_cap の price 欠損時のフォールバック（前日終値や取得原価の利用）。
- factor_research の追加ファクターや Z スコア正規化ユーティリティの整備。
- monitor / engine のより細かな監視メトリクス追加、LINE 通知等のアラート機能強化。

ライセンスや貢献ルール、リリース手順などは別途ドキュメントにまとめてください。
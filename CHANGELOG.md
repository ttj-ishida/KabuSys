# CHANGELOG

すべての重要な変更点を Keep a Changelog の形式で記録します。  
日付はパッケージの初期公開バージョン（0.1.0）として記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除された機能
- Security: セキュリティ関連

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-20
初期リリース。システム全体の起動スクリプト、設定管理、ロギング・プロセス制御ユーティリティ、ポートフォリオ構築ロジック、ペーパートレード検証ツール等を含む最小限の自動売買フレームワークを追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了、KeyboardInterrupt ハンドリング、SQLite/DuckDB 接続のクローズ処理を実装。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用するよう分離。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知で Engine.stop() を呼びスレッドを終了させる仕組みを導入。
    - 起動時に実行 PID を記録するための PID ファイルパスをサポート。

- 設定管理
  - src/kabusys/config.py
    - 環境変数読み込み・ラッパー Settings クラスを提供。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード（.env, .env.local）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースの堅牢化（export プレフィックス、引用符・エスケープ、インラインコメントの取り扱い）を実装。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE のバリデーション等）を実装。
    - 環境種別（development, paper_trading, live）とヘルパプロパティ（is_live / is_paper / is_dev）を提供。
  - config_setup.py
    - 対話型ウィザードで .env を生成・更新する CLI を追加（質問・既存値再利用・シークレットマスク表示・保存確認をサポート）。
    - デフォルト値を含むテンプレート形式で .env を書き出す `_write_env` を実装。

- 設定検証ツール
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パス（親ディレクトリの存在）チェック、config/*.yaml の存在確認・（PyYAML がある場合は）パース検証、KABUSYS_ENV=live 時の追加警告（LINE 周りや KILL_FLAG_CLEAR_ON_START）を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用する logging 設定ユーティリティを追加。
    - stdout 出力の StreamHandler と 日次ローテーション（TimedRotatingFileHandler）でログファイル出力を行う。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
    - 環境変数 LOG_LEVEL / LOG_DIR と引数による優先順を実装。
  - utils/process_priority.py
    - psutil を用いたプラットフォーム差分吸収のプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - CPU affinity を設定する set_cpu_affinity を追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) に対応。権限不足等で失敗した場合は警告ログでスキップする。

- ポートフォリオ構築ロジック（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選択（select_candidates）、等重み（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - 全スコアが 0 の場合は等重みへフォールバックする警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存ポジションからセクター別エクスポージャ計算、一定比率超過セクターの候補除外）。
    - 市場レジームに基づく投下乗数 calc_regime_multiplier（bull/neutral/bear のマップ）を実装。未知のレジームは 1.0 でフォールバックし警告を出す。
    - 一部挙動（price 欠損時の扱い等）は TODO コメントで将来改善を記載。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株丸め（lot_size）、1 銘柄上限・aggregate cap（利用可能現金を超える場合はスケーリングして端数取り扱い）を実装。
    - cost_buffer を考慮した保守的見積り・スケーリングロジックを実装。
    - 将来的な拡張（銘柄別 lot_size 等）を TODO として記載。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から指標を集計して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）など。
    - P95 算出、日付フィルタ (--from / --to)、--db オプションによる DB パス指定をサポート。
    - 指標の閾値比較による PASS/FAIL 判定を行う。DB テーブル欠如時のフォールバック（N/A や 0）を実装。

- 研究用モジュール（計算ロジックの下地）
  - research/factor_research.py（部分実装）
    - DuckDB 接続を受け取り価格・財務データからファクター（Momentum, Value, Volatility, Liquidity）を計算する設計を追加。
    - モメンタム計算のための定数と関数シグネチャを追加（calc_momentum）。一部実装は未完（ファイル末尾が未完の状態のまま含まれる）。

- その他
  - monitoring/monitoring_db.init_monitoring_db 呼び出しを各スクリプトで行い、監視テーブルを冪等に保証。
  - Execution 側で RiskManager の初期設定に broker.get_available_cash() を用いるように注入（初期ポートフォリオ値連携）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes
- research/factor_research.py は一部実装が未完（ファイル末尾で途切れている）。ファクター計算ロジックの完成・テストが必要。
- apply_sector_cap:
  - price が欠損（0.0 等）の場合にエクスポージャが過少見積りされる可能性がある点を TODO として明記。価格フォールバックロジック（前日終値等）の導入を検討する必要あり。
- position_sizing:
  - lot_size の将来的な銘柄別対応は未実装（全銘柄共通 lot_size を前提）。
- run_monitoring は監視 DB 接続に本番 sqlite_path を常に使用する仕様のため、paper_trading と monitoring データが混在しないよう運用での注意が必要。
- process_priority / set_cpu_affinity は環境によって権限不足等で失敗する場合があり、その場合は警告が出力され処理はスキップされる。

---

以上がコードベースから推測できる初期リリース（0.1.0）の変更履歴です。追加のコミット履歴や意図したリリースノートがある場合は、それに合わせて調整します。
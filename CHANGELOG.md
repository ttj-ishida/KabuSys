# CHANGELOG

すべての重要な変更履歴を記載します。フォーマットは "Keep a Changelog" に準拠しています。

全般:
- 本リリースは初期リリースです。システム設定、起動スクリプト、ポートフォリオ構築ロジック、ユーティリティ、検証/ウィザードツール、Paper Trading 検証レポート等の基本機能を実装しています。

## [0.1.0] - 2026-04-21

### Added
- 基本パッケージ定義とバージョン
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き対応（デフォルト 60 秒）。
    - 停止はプロジェクト data/stop_requested.flag によるフラグ検知で行う。
    - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority を使用）。
    - 監視は常に本番用 sqlite_path を使用して DB を初期化（monitoring DB 初期化処理を呼び出し）。
    - duckdb 接続を使用。

  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db がデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを生成（Mock を含む）。
    - ExecutionEngine をスレッドで実行し、停止フラグ検知で安全に停止。
    - PID ファイル管理（data/execution.pid）と停止フラグ検査を行う。

- 設定管理
  - src/kabusys/config.py: Settings クラスによる環境変数・設定値取得を実装。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）・.env.local 優先上書きの実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能（テスト向け）。
    - 各種プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL のバリデーション、監視閾値や Kill フラグ関連設定など。

  - src/kabusys/config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を実装。
    - シークレット入力のマスク表示、選択肢・デフォルト表示、既存 .env の読み込み再利用、保存確認をサポート。
    - .env の書式/テンプレート生成機能を提供。

  - src/kabusys/validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認および PyYAML がある場合はパース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定・Kill フラグ設定の注意喚起）を実装。
    - --strict オプションで警告をエラー扱いにできる。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py: 共通ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を root ロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_DIR / LOG_LEVEL / app_name による出力先・レベルの解決、ログディレクトリ自動作成（失敗時はファイル出力を無効化して継続）。
    - 日次ローテーションで 30 日分保持。

  - src/kabusys/utils/process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows (psutil の優先度定数) と POSIX 系 (nice 値) を抽象化して利用。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告ログを出してフェイルセーフにする。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソートおよび上位 N 件選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の計算。全スコア 0 の場合は等配分にフォールバック（警告ログ）。

  - src/kabusys/portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用し、既存保有のセクター露出が閾値を超えるセクターの新規候補を除外（sell_codes を除外して計算）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームでは警告を出して 1.0 でフォールバック。

  - src/kabusys/portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に応じて各銘柄の発注株数を計算。
    - 単元株丸め（lot_size）、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した分配ロジックを実装。
    - 板情報欠損や価格 0 の場合はスキップ、再現性のある残差処理を実装。

  - src/kabusys/portfolio/__init__.py で上記主要関数群をエクスポート。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py:
    - Paper Trading 用 SQLite DB から統計（稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95））を集計し、PASS/FAIL 判定付きレポートを生成する CLI を実装。
    - P95 計算、日付フィルタ、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）による判定。
    - DB 存在チェックや例外時のフォールバック（テーブル未存在時の安全処理）を実装。

- リサーチ（骨格）
  - src/kabusys/research/factor_research.py: ファクター計算モジュールの骨格を追加。
    - Momentum / Value / Volatility / Liquidity 等のファクターを DuckDB の prices_daily / raw_financials を用いて計算する方針と定数を定義。calc_momentum の実装開始（ファイル末尾で途切れたため、以降は継続実装予定）。

- 監視 DB 初期化ユーティリティの利用
  - 各起動スクリプトで監視用テーブルの初期化を保証する init_monitoring_db 呼び出しを追加（冪等）。

### Security
- 環境変数のシークレット値（.env での J-Quants / KABU API パスワード 等）は config_setup ウィザードでマスク入力を推奨。README 等で .env を Git にコミットしない注意喚起を出力。

### Notes / Implementation details
- .env パーサ (.parse_env_line / _load_env_file)
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱い（クォート外かつ直前にスペース/タブがある場合）を考慮した堅牢なパース処理を実装。
  - OS 環境変数を保護するため既存変数を上書きしないオプション（override 引数）を提供。

- logging_setup:
  - StreamHandler を stdout に向ける設計（cron 等で stdout/stderr を一本化する運用を想定）。
  - 既存ハンドラを明示的に flush/close → 削除し、新しいハンドラ群を設定することで二重出力を防止。

- process_priority:
  - psutil による優先度/affinity 操作は権限やプラットフォーム制約により失敗する可能性があるため、例外をキャッチして警告にとどめる（フォールバック動作）。

### Known limitations / TODO
- research/factor_research.py の一部（calc_momentum の続きなど）は未完の箇所があるため、完全実装は今後のリリースで対応予定。
- position_sizing の lot_size は全銘柄共通固定（将来的に銘柄別 lot_map に拡張予定）。
- apply_sector_cap の既存価格が 0.0 の場合に過少見積りされる可能性があり、前日終値や取得原価等のフォールバック価格を検討中（TODO コメントあり）。
- ログディレクトリ作成失敗時はファイル出力を無効化するが、その旨をより分かりやすく CLI 等で報告する改善が考えられる。

---

今後のリリースでは research の完成、テストカバレッジ拡充、運用向けの監視/アラート強化や性能チューニングを予定しています。
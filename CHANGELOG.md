# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

注: 以下の項目はリポジトリ内のコードから推測してまとめた変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-xx
初回公開リリース。本リリースでは自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、レポートユーティリティ等を提供します。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite(DB: data/paper_trading.db) を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動・監視する仕組みを実装。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視 DB 初期化（init_monitoring_db）と duckdb 接続を行い、停止フラグ検知で安全に終了。

- 環境設定・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI ツールを追加。シークレット項目はマスク表示。
    - 保存前に内容確認プロンプトあり。
  - validate_config.py
    - .env と config/*.yaml の整合性チェック用 CLI。
    - 必須環境変数の未設定検出、KABUSYS_ENV の妥当性確認、YAML のパースチェック（PyYAML がない場合は警告）や DB パスの親ディレクトリ存在チェック等を実施。
    - `--strict` オプションで警告を失敗扱いにできる。

- 環境 / 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - .env のパースで `export KEY=val` 形式やクォート、インラインコメントの取り扱いに対応（エスケープ処理含む）。
    - Settings クラスで各種環境変数をプロパティ化（DB パス、API トークン、paper_trading 用パス、監視閾値等）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。
    - KABUSYS_ENV/LOG_LEVEL の妥当性チェックと容易に問い合わせできる is_live / is_paper / is_dev プロパティを用意。

- ポートフォリオ関連（純粋関数群・副作用なし）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコアソート・上位選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア比率配分（スコア合計が 0 の場合等金額へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限検査と候補除外ロジック（売却予定銘柄をエクスポージャー計算から除外可能）。
    - calc_regime_multiplier: 市場レジームから投下資金乗数を返す（"bull"/"neutral"/"bear" とフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: weight/candidates/portfolio_value 等から発注株数を決定する多機能ロジックを実装（risk_based / equal / score をサポート）。
    - lot_size（単元株）丸め、ポジション上限、aggregate cap によるスケーリング、cost_buffer を考慮した安全な配分アルゴリズムを提供。

- ユーティリティ
  - utils.logging_setup
    - 共通ログ設定ユーティリティ。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - LOG_LEVEL の解決順と LOG_DIR の解決順を仕様化。
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度（"high"/"normal"/"low"）を設定するユーティリティと、CPU affinity を設定する関数を提供。
    - Windows/Linux(Mac 等) の差分を吸収し、アクセス権不足等は警告でスキップ。

- ツール・レポート
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加（期間フィルタ対応）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) などを集計し PASS/FAIL 判定を出力。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。

- research.factor_research (部分実装)
  - ファクター計算モジュールの骨子を追加（モメンタム等の計算方針を定義）。DuckDB を用いた prices_daily / raw_financials 参照設計。

- パッケージ情報
  - kabusys.__version__ = "0.1.0" を追加。

### Changed
- ロギング挙動の統一
  - 全起動スクリプトは setup_logging を呼び出し、ログ出力の形式・ローテーションを統一。

- DB 接続方針の明確化
  - 監視（monitoring）は環境に関係なく本番 sqlite_path を使用する方針を run_monitoring に明記。
  - run_execution は paper_trading の場合に専用 DB を使用することで本番 DB とのデータ分離を確保。

### Fixed
- 環境変数パースの堅牢化
  - .env のクォート内でのバックスラッシュエスケープおよびインラインコメント処理を改善し、意図しないコメント切り取りやエスケープ漏れを防止。

- ポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL に不正（0 以下・非整数）が渡された場合、ValueError を避けるためにデフォルトにフォールバックし警告を出力する処理を追加。

- ログディレクトリ作成失敗時の回復
  - ログディレクトリが作成できない場合にファイルハンドラの作成をスキップして stdout のみで継続するようにして、起動不可になる事象を回避。

- process_priority の例外ハンドリング
  - 権限不足や未対応プラットフォームでの例外をキャッチして警告を出力し処理を続行するよう改善。

### Security
- `.env` テンプレート出力時に注意喚起を表示（config_setup が .env を生成する際に Git にコミットしない旨を明記）。

### Notes / その他
- Paper Trading 検証レポートの P95 計算は簡易的実装（length に基づくパーセンタイル）を用いているため、将来的に厳密な統計ライブラリへ置換する余地あり。
- position_sizing の price fallback（price が 0 の場合）の注意コメントを残しており、将来的に前日終値や取得原価を用いたフォールバックを検討する想定。
- research.factor_research はモジュールの冒頭までの実装が含まれており、実際の計算ロジックは引き続き実装が必要。

---

今後のリリースでは、strategy 実装、ExecutionEngine の詳細、monitoring/system_monitor の実装詳細、research モジュールの完全実装等を反映予定です。
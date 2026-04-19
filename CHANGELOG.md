CHANGELOG
=========

すべての重要な変更は "Keep a Changelog" の形式に従って記載しています。
リリース日: 2026-04-19

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリース。以下の主要機能・CLI・ユーティリティ・ライブラリを追加。
  - 実行・監視関連スクリプト
    - run_execution: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
      - BrokerClientFactory 経由で実運用/モックブローカーを切り替え可能。
      - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による外部停止指示をサポート。
      - 起動時にプロセス優先度を "high" に設定する呼び出しを行う（utils.process_priority）。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視データを記録。
      - 停止フラグ（data/stop_requested.flag）の検知でループ終了。
  - 設定関連
    - config_setup: 対話式 .env ウィザードを追加。既存 .env の読み込み・更新、生成テンプレート、シークレットマスキングなどを提供。
    - validate_config: 起動前の設定検証 CLI を追加。必須環境変数・KABUSYS_ENV・DB パス・config/*.yaml の存在/パースなどを検証。--strict オプションで警告を失敗扱いにできる。
    - Settings クラス（config.py）を追加。環境変数の取り扱いと各種型チェック/妥当性検証を提供。
      - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
      - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の妥当性チェックを実装。
  - 環境ファイルパーサ
    - .env のパース実装を追加（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理のルール）。
  - ロギング／プロセス管理ユーティリティ
    - utils.logging_setup: 統一的なロギング設定を提供。
      - stdout への StreamHandler（stderr ではなく stdout を使用）と、日次ローテート（TimedRotatingFileHandler）でログファイルを出力（デフォルト logs/<app_name>.log、30 日保持）。
      - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続する安全処理あり。
    - utils.process_priority: Windows / POSIX を吸収したプロセス優先度設定と CPU affinity 設定を提供。権限不足や未対応環境では警告を出してスキップ。
  - ポートフォリオ構築ライブラリ（kabusys.portfolio）
    - portfolio_builder: 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights。全スコアが 0 の場合は等重みへフォールバック）。
      - select_candidates はスコア降順、同点時は signal_rank 昇順でタイブレーク。
    - risk_adjustment: セクター集中上限の適用（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）。
      - apply_sector_cap は "unknown" セクターを上限適用対象外とする設計。
      - calc_regime_multiplier は既定で {bull:1.0, neutral:0.7, bear:0.3} を提供し、未知レジームは 1.0 でフォールバックして警告を出力。
    - position_sizing: 発注株数算出（calc_position_sizes）。
      - allocation_method に "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）や aggregate cap（available_cash）を考慮したスケーリング実装。
      - cost_buffer による保守的なコスト見積りを反映。スケーリング時の端数配分は残差（fractional_remainder）に基づき再配分するロジックを実装。
  - Paper Trading 補助ツール
    - tools.paper_verification_report: ペーパートレード DB から稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し、PASS/FAIL 判定を行うレポート生成 CLI を追加。
      - デフォルト閾値: 稼働率 99.0%、成功率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。
      - P95 計算、日付フィルタ指定（--from/--to）、DB パスのオーバーライド（--db または 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
  - データ分析基盤（研究用）
    - research.factor_research: DuckDB 接続を受けてモメンタム等のファクター計算を行うモジュール（設計方針と定数を含む）。（一部実装が継続中）

Changed
- (初回リリースのため該当なし)

Fixed
- ログ設定の堅牢化:
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合でも、StreamHandler（コンソール）にフォールバックしてプロセスの起動を阻害しないように改良。
- .env 読み込みの堅牢化:
  - ファイル読み込み失敗時に警告を出してスキップする実装。
  - .env のパースでクォート・エスケープ・インラインコメントを適切に処理することで、想定外の値解釈を低減。
- プロセス優先度設定時のエラー耐性を追加:
  - psutil の権限不足や未サポート属性に対して警告を出し、安全にスキップするように変更。

Deprecated
- (初回リリースのため該当なし)

Removed
- (初回リリースのため該当なし)

Security
- 機密値は config_setup の表示でマスク（****）し、.env ファイルにコミットしないことを README にて強く推奨する注意喚起を出力するテンプレートを生成。

Notes / Known issues / TODO
- research.factor_research モジュールはファクター計算の主要設計を含むが、calc_momentum の実装冒頭でコードが未完となっている個所（サンプル中の末尾断片）があります。研究用途の完全実装は今後のタスク。
- position_sizing の価格欠損（price == 0.0）の扱いに関して注釈（TODO）あり。将来的には前日終値や取得原価へのフォールバックを検討。
- apply_sector_cap は "unknown" セクターを上限適用対象外としているため、マスタ側の sector_map の充実が運用上重要。
- 実運用時は validate_config による事前チェック（および KABUSYS_ENV の設定確認）を推奨。

ライセンス・その他
- パッケージバージョンは kabusys.__version__ = "0.1.0" に合わせています。
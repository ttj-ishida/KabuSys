# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
通常の慣習に従い、セマンティックバージョニングを想定しています。

最終更新日: 2026-04-22

## [Unreleased]

追加予定 / 注意事項（コード内の TODO やログ出力等から推測）
- Position sizing の将来的な拡張:
  - 銘柄ごとの単元情報（lot_size）を stocks マスタに持たせ、銘柄別 lot_map を受け取る設計への移行を検討中。
- apply_sector_cap における price 欠損時のフォールバック改善:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題を解消するため、前日終値や取得原価などのフォールバック価格取得の導入を検討中。
- research.factor_research モジュール（ファイル末尾が途中で切れている箇所）について実装継続予定:
  - calc_momentum 等の関数実装の完了・テスト整備。

---

## [0.1.0] - 2026-04-22

初回リリース（コードベースから推測した主要機能・ユーティリティ群をまとめて記載）

### Added
- 基本パッケージ情報
  - kabusys パッケージ初期リリース（__version__ = 0.1.0）。

- 環境・設定管理
  - Settings クラスによる環境変数ベースの設定管理（J-Quants / kabu API / DB パス / 監視閾値等）。
  - .env 自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - .env 読み込みロジックは export 構文・クォート・インラインコメントに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。

- 設定ツール（CLI）
  - config_setup: 対話式ウィザードで .env を作成／更新する CLI を追加。
    - 質問項目として KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、Kill Switch 設定等を含む。
    - .env 書き込みテンプレートには注記（.env を Git にコミットしない旨）を記載。
  - validate_config: .env と config/*.yaml の事前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、YAML の存在/パースチェック（PyYAML 利用可時）。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行系（Execution）
  - run_execution スクリプト: ExecutionEngine 起動用のエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（実運用 / モックを切替）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てロジック。
    - RiskManager にデフォルト RiskConfig を設定（max_position_pct, max_utilization 等）。
    - エンジンは別スレッドで run_session を起動し、stop フラグ（data/stop_requested.flag）で安全終了。
    - 実行中は PID ファイル (data/execution.pid) を使用。

- 監視系（Monitoring）
  - run_monitoring スクリプト: SystemMonitor のポーリングループ起動エントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計（監視用 DB の一貫性確保）。
    - stop フラグ（data/stop_requested.flag）を検知してループを終了。
    - check_once() 実行中の例外は捕捉して次のポーリングでリトライ。

- ポートフォリオ構築（Portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコアでソートして上位 N を選択（スコア降順、同点は signal_rank 昇順でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額/スコア加重配分を計算（スコア合計が 0.0 の場合に等金額へフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を制限し、既存保有のセクター比率が閾値を超えるセクターの新規候補を除外（"unknown" セクターはチェック対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバックして警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に応じて発注株数を決定。
      - risk_based: 許容リスク率、stop_loss を元にポジションサイズを算出。
      - equal/score: 各銘柄の重みに基づいて金額配分し、lot_size（デフォルト 100）で丸め。
      - aggregate cap：総投資額が available_cash を超える場合はスケーリングして端数は fractional remainder ロジックで lot 単位で追加配分。
      - cost_buffer（スリッページ/手数料推定）を加味して保守的に見積もる。
      - 価格欠損時は対象銘柄をスキップしデバッグログを出力。
      - 将来的な拡張（銘柄別 lot_size）をコメントで明示。

- 研究・ファクター計算（Research）
  - research.factor_research（設計方針と一部定数および calc_momentum の仕様を記載）。
    - DuckDB の prices_daily / raw_financials を参照し、モメンタム・バリュー・ボラティリティ・流動性指標を計算する方針。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev 等の計算仕様（関数は途中まで実装されている状態から始まる）。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - PAPER_TRADING_SQLITE_PATH（環境変数）や --db オプションで DB を指定可能。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）。
    - Pass/Fail 基準（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 latency <=200ms 等）を設定し判定を出力。
    - P95 計算、期間フィルタリング、データ欠損時の N/A ハンドリングを実装。

- ユーティリティ
  - utils.logging_setup:
    - 統一的なログ設定ユーティリティを導入。
      - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler, 30日）をルートロガーに設定。
      - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。
      - LOG_LEVEL / LOG_DIR の解決順を明記。
      - stdout を使用することで cron 等のリダイレクト運用を想定。
  - utils.process_priority:
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（Windows / POSIX に対応）。
    - set_cpu_affinity: 指定コア数へ CPU affinity を固定する機能。
    - アクセス権限や未対応 OS の場合は警告メッセージを出してスキップ。

- DB / 接続
  - DuckDB と SQLite の両方を利用する設計（分析用は DuckDB、監視/発注履歴は SQLite）。
  - 監視 DB 初期化関数 init_monitoring_db を起動前に呼び出してテーブル存在を保証（冪等）。

- 安全停止 / 運用考慮
  - 停止フラグファイル（data/stop_requested.flag）によるプロセス停止制御を導入（monitoring / execution 起動スクリプトで利用）。
  - Kill Switch 関連環境変数（KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）を設定可能。
  - 実行時にプロセス優先度を "high" に設定するデフォルト挙動（起動スクリプトで最初に実行）。

### Changed
- （初回リリースのため該当なし。設計上の注記を README やドキュメントに反映する想定。）

### Fixed
- （初回リリースのため該当なし。実装内で例外発生時にログ出力してリトライする保護的実装あり。）

### Security
- .env ファイルを Git にコミットしない旨を明記（config_setup のヘッダ説明）。
- デフォルトでは OS 環境変数が優先され、.env の自動ロード時に OS 環境を保護するため protected キーが存在。

### Known limitations / Notes
- calc_position_sizes や apply_sector_cap で price が欠損（0.0）の場合、現在はスキップまたは過少見積りとなるコメントが残っており、将来的な改善が必要。
- research.factor_research の一部関数が途中実装で終了している箇所があり、完了とテストが必要。
- ログディレクトリの作成に失敗した場合はファイルログが無効化されコンソール出力のみとなる。
- process_priority / cpu_affinity はプラットフォームや権限に依存し、失敗時は警告を出して継続する設計。

---

今後のリリースでは上記の Unreleased 項目（価格フォールバック、銘柄別 lot_size、research モジュール完成、テスト整備）や運用周りの拡張（監視アラート強化、より詳細なメトリクス保存など）を計画してください。
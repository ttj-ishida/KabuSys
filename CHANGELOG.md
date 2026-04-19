# Changelog

すべての注記は Keep a Changelog 準拠で、重要な変更点を日本語でまとめています。

フォーマット:
- 変更種類: Added / Changed / Fixed / Removed / Security
- 各項目は関係するモジュール/ファイルと説明を含みます。

全般
- 初期バージョン: 0.1.0
- リリース日: 2026-04-19

## [0.1.0] - 2026-04-19

### Added
- 起動スクリプト: 実行および監視プロセスの起動用スクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - 実行停止は data/stop_requested.flag を検出して行う。
  - src/kabusys/run_monitoring.py
    - SystemMonitor 用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト60秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して起動する（監視は常に本番 DB を参照）。

- 設定管理・検証・ウィザード
  - src/kabusys/config.py
    - Settings クラスを提供。環境変数から各種設定を取得（J-Quants / kabu API / DB パス / paper_trading 関連 / 監視閾値 等）。
    - .env の自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml で探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START 等の設定を取り扱うプロパティを実装。入力値チェックを行い、無効な値で例外を送出する箇所あり。
  - src/kabusys/validate_config.py
    - 起動前に .env および config/*.yaml の設定を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML が存在する場合）や本番時のガード（LINE 通知の有無、KILL フラグ自動クリアの危険性）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
  - src/kabusys/config_setup.py
    - .env 作成・更新の対話式ウィザードを追加。既存 .env の読み込み、選択肢・説明付き入力、シークレットマスク、書き込み機能を提供。

- ロギング / プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なロギング初期化関数 setup_logging を提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定、既存ハンドラの二重設定防止、LOG_LEVEL / LOG_DIR の解決ロジックを実装。ログディレクトリ作成失敗時のフォールバック処理あり。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS（POSIX）差分を吸収し psutil を利用して優先度や affinity を設定、許可エラー時は警告でスキップ。

- ポートフォリオ構築ロジック（純関数群、DB非依存）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates（スコア降順で上位 N 抽出）、calc_equal_weights（等金額配分）、calc_score_weights（スコア正規化配分、全スコア0時に等分へフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中上限の判定と候補除外）、calc_regime_multiplier（market regime に応じた投下係数の計算、未知のレジームは警告してフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" をサポート）。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer による保守的見積り、残余キャッシュを残差順に割り当てるロジックを実装。

- 運用ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。指定期間の system_status / trade_logs / risk_logs を照会して稼働率、注文成功率、送信率、レイテンシ（P95 等）を算出し PASS/FAIL 判定を行う。閾値はソース内定数で定義（稼働率99%、成立率90%、送信率95%、P95<=200ms）。

- 研究用ファクター計算（雛形）
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨子を追加。モメンタム / MA200 / ATR / 出来高等の計算方針・定数を定義。calc_momentum の関数シグネチャとドキュメントを含む（実装の続きはファイル内で未完）。

- パッケージメタ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Changed
- ログ出力の標準化
  - setup_logging のデフォルトで stdout を使用するようにし、cron/スケジューラからの起動時に stdout/stderr を扱いやすくした。
- 実行・監視起動時のプロセス優先度設定を標準化
  - run_execution/run_monitoring の起動処理冒頭で set_process_priority("high") を呼び出すようにして、重要プロセスの優先度を高く設定する。

### Fixed / Defensive behavior
- 環境変数パースの堅牢化
  - src/kabusys/config.py の .env パーサは export プレフィックスやクォート内のエスケープ、行内コメントの取り扱いを適切に実装。空行やコメント行を無視する等の処理を追加。
- MONITOR_POLL_INTERVAL の入力検証
  - run_monitoring の _get_poll_interval で 1 未満や不正値を検出した場合にデフォルトへフォールバックして警告出力するようにした（time.sleep の ValueError 回避）。
- ExecutionEngine 起動時の停止フラグ処理
  - run_execution は起動前に停止フラグが既に立っている場合は起動を中止し、実行中は停止フラグ検知で engine.stop() を呼ぶようにして安全にシャットダウンする。
- DB 初期化の冪等処理
  - init_monitoring_db は監視テーブルを存在確認して必要なら作成するようにして複数回呼んでも問題にならないようにしている（run_execution/run_monitoring で利用）。

### Notes / その他
- 設定検証で PyYAML 未導入時は YAML 検証をスキップするが警告を出力する。
- Settings の一部プロパティ（paper_fill_mode, env, log_level 等）は無効値で ValueError を投げるため、運用時には .env の値を正しく設定する必要がある。
- research/factor_research.py はモジュールの骨子を含むが、calc_momentum の実装がファイル末尾で途中（コメント/未完）になっているため、完全なファクター計算の実装は今後の追加が必要。

---

今後のリリースでは、research/factor_research の実装完了、ExecutionEngine / SystemMonitor の更なるテストカバレッジ追加、paper_trading の挙動検証、単体テスト / CI 設定等を予定すると良いでしょう。必要であれば、CHANGELOG に含める具体的なコミットや PR 番号、影響範囲の詳細化（例: 破壊的変更の有無）を追加で生成します。
CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
セマンティックバージョニングを採用しています。

Unreleased
----------

（現時点の未リリース変更はありません。）

0.1.0 - YYYY-MM-DD
------------------

初回公開リリース。

Added
- 実行・監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - スレッドでエンジンをデーモン実行し、 data/execution.pid に PID を書き込む仕組み。
    - data/stop_requested.flag による停止フラグ検出と安全停止処理を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - 起動時にプロセス優先度を "high" に設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するよう明記。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了し、接続をクローズする安全処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理・ウィザード・検証ツールを追加
  - config.py
    - Settings クラスを追加し、各種設定（J-Quants トークン、kabuステーション設定、DB パス、ログレベル、監視閾値など）を環境変数から取得。
    - .env 自動ロード機能を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。.env と .env.local の読み込み優先度を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - paper_trading 用の paper_sqlite_path、pid/kill flag パスなどを提供するプロパティ。
    - env 判定ユーティリティ（is_live/is_paper/is_dev）を追加。

  - config_setup.py
    - 対話式ウィザードで .env の初期生成・更新を支援する CLI を追加。
    - 入力補助、シークレットマスキング、既存 .env 読み込みおよび最終確認→保存機能を実装。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在チェック（PyYAML が利用可能な場合は YAML パース検証も実行）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: シグナルをスコア降順で選択（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア重み配分（合計スコアが 0 の場合は等配分にフォールバックし警告）。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を防ぐための候補フィルタ（sell_codes の除外対応、unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルトフォールバックと警告）。

  - portfolio.position_sizing
    - calc_position_sizes: 各配分方式（risk_based / equal / score）に基づく株数計算を実装。
    - 単元株丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケーリング、残差に基づく追加配分ロジックを実装。
    - lot_size（単元）や cost_buffer（手数料/スリッページ見積り）を考慮。

  - portfolio.__init__ で上記関数群を公開。

- 研究用ファクター計算
  - research.factor_research
    - calc_momentum: MOMENTUM（1M/3M/6M、MA200乖離）の計算。
    - calc_volatility: ATR/平均売買代金/出来高比率等の計算（DuckDB の prices_daily を参照する設計）。
    - DuckDB 接続を受け、SQL + Python でデータを計算する方針を導入。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装し、Windows/Linux/macOS で適切にプロセス優先度（nice/HIGH_PRIORITY_CLASS）を設定（権限不足時は警告を出してスキップ）。
    - set_cpu_affinity(cpu_count) を追加し、最初の N コアにプロセスをピン留めする機能を提供（対応不可環境では警告を出してスキップ）。

- その他ツール
  - tools.paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づいて PASS/FAIL を判定。
    - CLI から期間指定（--from / --to）や DB パス（--db）を受け付ける。PAPER_TRADING_SQLITE_PATH 環境変数を優先。

Changed
- プロセス起動時の優先度設定を一貫して行うように変更
  - run_execution.py と run_monitoring.py の冒頭で set_process_priority("high") を呼び出すことで、重要プロセスの応答性を確保。

- 設定自動読み込みの優先順位を明確化
  - OS 環境変数 > .env.local > .env の順で読み込む挙動を実装。既存 OS 環境変数は protected として上書きされない。

Notes / Implementation details
- DB 関連
  - 監視用途の SQLite は settings.sqlite_path（デフォルト data/monitoring.db）を使用。paper_trading 時は settings.paper_sqlite_path（data/paper_trading.db）を使用して完全分離。
  - DuckDB は分析用に data/kabusys.duckdb（設定可能）を使用する前提。

- 停止フラグ / Kill Switch
  - data/stop_requested.flag を検知してグレースフルに停止する仕組みを run_* スクリプトに実装。
  - Settings で kill_flag 関連の設定を提供し、validate_config.py で本番環境向けのガード（KILL_FLAG_CLEAR_ON_START）チェックを行う。

- 設計方針
  - portfolio / research の関数群は「副作用なし（純関数）」「DB 参照は最小限（DuckDB を明示的に受け取る）」を目指した設計。
  - CLI ツールは Python 標準の argparse を使用し、非対話的運用にも対応。

Breaking Changes
- 初回リリースのため該当なし。

Security
- シークレット（J-Quants トークンや KABU_API_PASSWORD）の取り扱いは .env に依存。config_setup の出力では .env を Git にコミットしないよう注意喚起。

今後の予定（TODO / 改善案）
- portfolio.position_sizing: 銘柄ごとの lot_size を stocks マスタから取得する対応。
- risk_adjustment.apply_sector_cap: price の欠損時のフォールバック（前日終値や原価など）を追加。
- research.factor_research: さらに多くのファクター実装と z-score 正規化処理の統合。
- 単体テストの追加（validate_config の YAML チェック等は PyYAML に依存しているため、テストでの分離を検討）。

---
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートに反映する際は、コミット履歴やリリース管理方針に合わせて調整してください。
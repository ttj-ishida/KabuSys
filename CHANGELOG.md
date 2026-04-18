CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
（コードから推測して作成した初期の変更履歴です）

Unreleased
----------

（次回リリースに向けた変更点があればここに追記してください。）

0.1.0 — 2026-04-18
------------------

Added
- プロジェクト初期リリース。
- 環境 / 設定関連
  - Settings クラス導入（kabusys.config）。環境変数からアプリ設定を安全に取得するプロパティを提供。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 実行環境 (KABUSYS_ENV) などを取得。
    - KABUSYS_ENV、LOG_LEVEL 等の妥当性検証を実装。
  - .env 自動読み込み機能を追加（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パース処理を強化（export プレフィックス対応、クォート文字列内のエスケープ処理、インラインコメント処理など）。
  - config_setup CLI（kabusys.config_setup）: インタラクティブな .env 作成・更新ウィザードを追加。
    - デフォルト値、選択肢、シークレット入力、確認・保存機能を提供。

- 設定検証ツール
  - validate_config CLI（kabusys.validate_config）を追加。
    - 必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在／パース検証を実装。
    - --strict オプションで警告をエラー扱いにできる仕組み。

- 実行スクリプト / 実行管理
  - run_execution（kabusys.run_execution）を追加:
    - プロセス優先度を高く設定して起動（utils.process_priority を使用）。
    - 環境に応じて paper_trading 用 DB を分離（KABUSYS_ENV=paper_trading 時は data/paper_trading.db を使用）。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）や PID ファイルの取り扱い、スレッドでのエンジン実行・安全停止処理を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）をコード内で初期化。

  - run_monitoring（kabusys.run_monitoring）を追加:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満や不正値はデフォルトにフォールバック）。
    - 監視は環境に依らず本番 sqlite_path を使用して monitoring DB を初期化。
    - 停止フラグの検知、例外発生時のログ出力・再試行処理を実装。

- ログ周りユーティリティ
  - setup_logging（kabusys.utils.logging_setup）を追加:
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに統一的に設定。
    - ログディレクトリ自動生成、LOG_DIR / LOG_LEVEL の解決ロジック、ファイル出力失敗時のフォールバック動作を実装。
    - 既存ハンドラのクローズと再設定で二重登録を回避。

- プロセス／パフォーマンスユーティリティ
  - process_priority（kabusys.utils.process_priority）を追加:
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity 設定ユーティリティ set_cpu_affinity を提供（指定コア数でプロセスを固定）。
    - 権限不足や未対応プラットフォーム時に安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio モジュールを追加（kabusys.portfolio）:
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順／タイブレークでソートして上位 N 件を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア全0時は等配分にフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中を防ぐための候補フィルタ（売却予定銘柄を除外するオプション、"unknown" セクターは制限免除）。
      - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数を実装（未知レジームは警告の上フォールバック）。
    - position_sizing:
      - calc_position_sizes: リスクベース / equal / score の割当方式を実装。単元株（lot_size）で丸め、最大ポジション上限・max_utilization・コストバッファを考慮したスケーリングロジックを実装。
      - スケールダウン時に残差（fractional remainder）を用いて優先的に lot 単位で追加配分するアルゴリズムを採用。

- リサーチ
  - research.factor_research（部分実装）を追加:
    - モメンタム / MA200 / ATR / 出来高などのファクター計算を行う設計が含まれる（DuckDB 接続を受け prices_daily / raw_financials を参照）。
    - 日付・窓幅等の定数を定義（1M/3M/6M、MA200、ATR20 等）。

- ツール
  - tools.paper_verification_report を追加:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から期間集計を行い、システム稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）・リスク却下数を出力。
    - Pass/Fail 判定を行う閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - --from / --to / --db オプションをサポート。

- パッケージ情報
  - __version__ を "0.1.0" に設定。

Changed
- 内部設計上のデフォルトおよび安全策を導入:
  - MONITOR_POLL_INTERVAL のデフォルトは 60 秒、不正値はログに警告してデフォルトにフォールバック。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - process_priority / set_cpu_affinity は権限不足や非対応環境で警告ログを出してスキップ。

Fixed
- 例外処理とリソースクリーンアップの強化:
  - run_monitoring / run_execution で DB 接続（sqlite3 / duckdb）を finally ブロックで確実にクローズするように修正。
  - logging_setup で既存ハンドラの flush/close を行い二重出力を防止。

Security
- .env の取り扱いについて注意喚起:
  - config_setup で生成される .env に対し「絶対に Git にコミットしないこと」と明記。

Notes / その他
- 多くのモジュールは純粋関数（DB参照なし）で実装されておりユニットテストが容易な設計になっています（portfolio モジュール等）。
- DuckDB / SQLite / external broker client 等外部依存はインターフェースを通じて注入される設計のため、テスト用のモック差し替えが想定されています。
- 一部の実装は TODO コメントや将来の拡張（銘柄別 lot_size マスタ、価格フォールバックなど）を含みます。

どうしても追加・修正したい点があればコードの差分や意図を教えてください。CHANGELOG をさらに詳細化（ファイルごとの変更、コミット参照等）して更新します。
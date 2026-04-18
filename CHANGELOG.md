# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 以下はリポジトリ内のソースコードから機能・修正点を推測してまとめた変更履歴です。

## [Unreleased]

- ドキュメント / テスト用: 追加・調整予定の項目や未実装の機能のプレースホルダ（内部実装・関数の拡張など）。
- research/factor_research モジュールの続き（モメンタム等のファクター計算の実装完了）や追加のユニットテストを予定。

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期実装（初回リリース）
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を導入。
- 実行用エントリスクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御用フラグファイル (`data/stop_requested.flag`) による安全停止処理を実装。
    - 監視 DB は環境にかかわらず本番の `sqlite_path` を使用する設計。
    - DuckDB 接続を併用。
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、専用の Paper Trading DB（`data/paper_trading.db`）および MockBrokerClient を使用して本番 DB と分離。
    - 起動前に停止フラグを確認し、フラグが存在する場合は起動しない安全仕様。
    - 実行エンジンはデーモン・スレッドで実行し、フラグ検出時に engine.stop() を呼ぶ仕組みを提供。
- 設定・環境変数管理
  - `src/kabusys/config.py`
    - .env の自動ロード機構（`.env` → `.env.local`、OS 環境変数保護付き）。
    - `.env` パース処理を強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
    - `Settings` クラスを追加し、環境依存の設定をプロパティ経由で安全に取得（DB パス、KABUSYS_ENV 判定、paper_trading 用パス、各種閾値等）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化オプションを提供（テスト用途）。
- 設定支援ツール
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードによる `.env` ファイルの作成・更新を追加。
    - 既存 `.env` の読み込み、マスク表示、選択肢・デフォルト値の提示、保存確認などを提供。
    - `.env` の書式は安全に（Git コミットしない旨のヘッダ付き）保存。
  - `src/kabusys/validate_config.py`
    - 起動前検証 CLI を追加（必須環境変数のチェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、config/*.yaml の存在とパースチェックなど）。
    - `--strict` オプションで警告を失敗扱いにする機能を追加。
- ポートフォリオ構築関連（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナルのソート・上位選定 (`select_candidates`)。
    - 等金額配分 (`calc_equal_weights`) とスコア加重配分 (`calc_score_weights`) を追加。全スコアが 0 の場合は等配分にフォールバックし警告をログ出力。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限の適用 (`apply_sector_cap`)。既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに基づく投下資金乗数 (`calc_regime_multiplier`) を実装（"bull", "neutral", "bear" に対応。未知値は警告を出して 1.0 にフォールバック）。
  - `src/kabusys/portfolio/position_sizing.py`
    - 株数決定ロジックを実装（`calc_position_sizes`）。
    - `risk_based`, `equal`, `score` の配分方式に対応。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash に応じたスケーリング）、cost_buffer（手数料・スリッページ見積）を考慮。
    - キャパシティ超過時のスケーリングと残余キャッシュを使った端数調整アルゴリズムを実装。
  - `src/kabusys/portfolio/__init__.py` で上記機能をパッケージとしてエクスポート。
- 監視・実行共通ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続するフォールバック動作を実装。
    - ログレベル解決順（引数 > 環境変数 > デフォルト）を明示。
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する関数を追加（psutil 利用）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を追加。
    - 設定に失敗した場合は警告ログを出力してスキップする安全挙動。
- 実行系コンポーネントとの連携（起動フロー）
  - 起動スクリプトでプロセス優先度を最初に "high" に設定するよう共通運用ルールを採用。
  - Execution 起動時に BrokerClientFactory によるブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てを行う設計。
  - RiskManager のデフォルト設定を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker, max_drawdown 等）。初期ポートフォリオ値は broker.get_available_cash() から取得。
- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用の SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集約してレポート出力する CLI を追加。
    - デフォルト閾値: 稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms。基準未達は FAIL 判定として詳細理由を表示。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）に対応。
- research モジュール（初期実装）
  - `src/kabusys/research/factor_research.py`（ファイル途中まで実装）
    - ファクター計算の骨子（モメンタム、MA200乖離、ATR、流動性など）を作成。DuckDB 接続を受ける設計。
    - 日数定数やスキャンバッファなどの設計方針を定義。

### Changed
- ロギング
  - コンソール出力に stdout を使用（stderr ではなく）することで、cron/task scheduler 等でのリダイレクトを容易に。
  - 既存ハンドラをクリアしてから再設定することで二重ログ出力を防止。
- .env ロード順の明確化: OS 環境変数 > .env.local > .env（.env.local は override=True で上書き）。

### Fixed
- 停止フラグ / PID 管理
  - 実行中の安全停止フロー（stop flag を検知して終了、PID ファイルパスを設定）を起動スクリプト側で整備。
- DB 初期化の冪等性
  - `init_monitoring_db(sqlite_conn)` を起動時に呼ぶことで監視テーブルが必ず存在することを保証（冪等化）。

### Security
- .env の取り扱いに関する注意喚起を `config_setup.py` に付記（.env を Git にコミットしない旨のヘッダ）。

### Known issues / Notes
- research/factor_research.py は途中で終端しており、ファクター計算の完全な実装が未完（次期リリースで完成予定）。
- `apply_sector_cap` は price が欠損（0.0）だとエクスポージャーが過少推計される可能性があり、将来的に価格フォールバックを導入する必要がある旨を TODO コメントで残しています。
- process_priority / set_cpu_affinity は psutil の権限エラーや未実装 API を検出した場合にスキップしてログを残す実装のため、ユーザー権限によって期待どおりに動作しない可能性があります。

---

（この CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノート作成時はコミット履歴やリリースノート元データを参照して確定してください。）
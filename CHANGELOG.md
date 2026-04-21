# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
語彙はコードベースから推測してまとめています（実装・設計の注釈を含みます）。

※ バージョン番号はパッケージの `__version__`（0.1.0）に合わせています。

## [Unreleased]

- 今後の変更点・予定の追記用。

---

## [0.1.0] - 2026-04-21

### Added
- 全体
  - プロジェクト初期版をリリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装。
  - パッケージバージョンを `0.1.0` として公開（`src/kabusys/__init__.py`）。

- 設定管理
  - 環境変数自動読み込み機能を実装（`.env` / `.env.local` をプロジェクトルートから自動ロード）。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索する（`kabusys.config`）。
  - `.env` パースの堅牢化：
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理、コメント判定の改善。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入（テスト等で無効化可能）。
  - `Settings` クラスを導入し、アプリ設定をプロパティ経由で取得可能に：
    - J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）など多数の設定プロパティを提供。
    - Paper Trading 用の `paper_sqlite_path`、`paper_fill_mode`（入力値検証付き）を追加。
    - `is_live`, `is_paper`, `is_dev` 等の便利プロパティを追加。

- 設定ユーティリティ・CLI
  - 対話式設定ウィザード `kabusys.config_setup` を追加：
    - `.env` の初期作成・更新を支援するウィザード（シークレット項目のマスク表示、デフォルト提示、確認後保存）。
  - 設定検証ツール `kabusys.validate_config` を追加：
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DBパス親ディレクトリ存在チェック、`config/*.yaml` の存在および（PyYAML があれば）パース検証、`live` 環境に対する追加ガードを実施。
    - `--strict` オプションで警告も FAIL 扱いに可能。

- 実行・監視ランナー
  - `run_execution.py`（ExecutionEngine 起動スクリプト）を追加：
    - プロセス優先度を「high」に設定するユーティリティ呼び出しを行う。
    - Paper Trading 環境では専用 SQLite（`paper_sqlite_path`）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグファイル（`data/stop_requested.flag`）検知による安全停止、実行 PID ファイル管理、スレッド駆動でのセッション実行。
    - RiskManager の既定設定（上限比率、レート制限、サーキットブレーカー等）を組み込み、`initial_portfolio_value` をブローカーから取得して初期化。
  - `run_monitoring.py`（SystemMonitor ポーリング起動スクリプト）を追加：
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用して記録。
    - 停止フラグの検知でループを終了し、例外発生時にはログ出力後に次ポーリングへ移行。

- モニタリング DB
  - `init_monitoring_db` 呼び出しにより、起動時に監視テーブル存在を保証（冪等）。`run_execution` と `run_monitoring` の両方で呼び出し。

- ロギング
  - `kabusys.utils.logging_setup` を実装：
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - 既存ハンドラは開始時にクリアして重複出力を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。

- プロセス優先度 / CPU 固定
  - `kabusys.utils.process_priority` を実装：
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収して `set_process_priority(level)` を提供（"high"/"normal"/"low"）。
    - `set_cpu_affinity(cpu_count)` による最初 N コアへのピン留めをサポート。
    - 権限不足などの失敗は警告ログでフォールバック。

- Portfolio（銘柄選定・ポジション算出）
  - `portfolio_builder`：
    - BUY シグナルの候補選定 `select_candidates`、等金額配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコア 0 の場合は等配分にフォールバック）を実装。
  - `risk_adjustment`：
    - セクター集中制限 `apply_sector_cap`（既存保有を考慮して特定セクターの新規候補を除外、"unknown" セクターは除外適用対象外）。
    - 市場レジームに基づく乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" マップ、未知値は警告して 1.0 にフォールバック）。
  - `position_sizing`：
    - リスクベース / 等分 / スコア重みの各配分方式を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）、コストバッファ考慮、残差を使った追加配分ロジックを実装。
    - 価格欠損時のログ出力・スキップ、将来の銘柄別 lot_size 拡張の TODO コメント。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を実装：
    - Paper Trading の SQLite DB を基に稼働率、注文成功率、送信率、P95 レイテンシ等を集計して標準出力レポートを生成。
    - P95 計算関数、SQL クエリ／日付フィルタ作成、閾値による PASS/FAIL 判定を実装。
    - CLI 引数（--from/--to/--db）に対応。環境変数 `PAPER_TRADING_SQLITE_PATH` を優先して DB を決定。

- リサーチ
  - `kabusys.research.factor_research` の骨子を追加：
    - モメンタム／ボラティリティ等のファクター計算設計方針、定数、`calc_momentum` の導入（途中までの実装ソースを含む）。

### Changed
- （初版のため明確な「変更」はなし。実装方針やデフォルト値は各モジュール内コメントで明記。）

### Fixed
- `.env` パーサーの不具合予防：
  - 不正な空値やコメントの扱いで環境変数が誤って取り込まれるケースへの対処（`_parse_env_line` の堅牢化）。

### Deprecated
- なし

### Removed
- なし

### Security
- `.env` の取り扱いに関して注意喚起を README 相当（`config_setup.py` のヘッダ）に記載：`.env` を絶対に Git にコミットしない旨を明記。

---

補足・移行メモ
- 実行前に必須環境変数（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` 等）を設定してください。`kabusys.validate_config` で事前検証が可能です。
- Paper Trading を使う場合、`KABUSYS_ENV=paper_trading` に設定すると専用 DB（`PAPER_TRADING_SQLITE_PATH`）を使います。`run_execution` は本番とは DB を分離します。
- ロギングはデフォルトで `logs/` に日次ローテートされますが、ディレクトリ作成に失敗する環境（権限等）ではコンソール出力のみになります。
- プロセス優先度設定・CPU affinity は権限が必要な操作が含まれるため、環境によって警告が出力され処理がスキップされる場合があります。

もし希望があれば、上記 CHANGELOG を英語版に翻訳したり、各ファイルごとの細かいコミット単位（想定コミットメッセージ）に分解して記載することもできます。どのレベルの詳細が必要か教えてください。
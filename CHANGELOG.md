# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-04-23
初回リリース。以下の主要コンポーネントと機能を実装しました。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - ログ出力の統一ユーティリティを追加（kabusys.utils.logging_setup）。
    - コンソール出力は stdout を使用。
    - 日次ローテーション（TimedRotatingFileHandler）で logs/<app_name>.log に出力、30日分保持。
    - 環境変数/引数でログレベル・出力先を解決。
  - プロセス優先度・CPU アフィニティ設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX を吸収する API（psutil 使用）。失敗時は警告にフォールバック。
    - set_process_priority(level), set_cpu_affinity(cpu_count) を提供。

- 設定管理
  - 環境変数読み込みと Settings クラスを追加（kabusys.config）。
    - プロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を自動ロード（OS 環境変数は保護）。
    - .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグパス、閾値など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL のバリデーション、is_live/is_paper/is_dev プロパティ。

  - 対話式設定ウィザードを追加（kabusys.config_setup）。
    - .env の初期作成・更新を支援する CLI（秘密入力・デフォルト・選択肢対応）。
    - 生成テンプレートは .env に保存され、コミット禁止の注意を含む。

  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML があれば中身も検証）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE トークン等の警告、KILL_FLAG_CLEAR_ON_START の危険性警告）。
    - --strict オプションで警告を FAIL として扱う。

- 実行系 / 監視
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を利用して本番 DB と分離（BrokerClientFactory により Mock ブローカーを作成する想定）。
    - 監視テーブルの存在を保証するため init_monitoring_db を呼び出し（冪等）。
    - ExecutionEngine を別スレッドで run_session させ、data/stop_requested.flag による停止監視を実装。
    - 実行時 PID を data/execution.pid に保存するなどの PID 管理（設定パスは Settings 経由）。
  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。
    - 起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず production 用 sqlite_path を使用する設計。
    - stop_requested.flag による停止検出、monitor.check_once() 呼び出しで例外を拾ってログ出力しループ継続する堅牢化。
    - duckdb 接続も並行利用。

- モニタリング / 検証ツール
  - Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
    - SQLite（PAPER_TRADING_SQLITE_PATH / --db 指定）から system_status / trade_logs / risk_logs を集計。
    - 稼働率、注文成功率（Fill）、送信率（Sent）、P95 レイテンシ等を算出し、閾値（稼働率 99%、Fill 90%、Send 95%、P95 200ms）に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ（--from/--to）対応、存在しない DB へのエラーメッセージ出力。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio モジュールを追加し、以下の関数を提供：
    - select_candidates: BUY シグナルをスコア降順で最大 N 件取得（同点は signal_rank 昇順でタイブレーク）。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア比率で重み計算。全スコアが 0 の場合は等金額配分へフォールバックし警告を出す。
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用し、超過セクターの新規候補を除外。unknown セクターは上限対象外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバックして警告）。
    - calc_position_sizes: allocation_method に応じた株数決定（risk_based / equal / score）、単元株（lot_size）丸め、per-position と aggregate のキャップ、cost_buffer を用いた保守的見積、資金超過時のスケールダウンと残差処理ロジックを実装。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details / 制限事項
- 自動 .env ロードはプロジェクトルートが検出できない場合スキップされるため、パッケージ配布後の環境では明示的に環境変数を設定すること。
- process_priority と CPU affinity の設定は psutil の権限やプラットフォームに依存し、失敗時は警告を出してスキップする設計。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力をスキップしてコンソールのみで継続する。
- portfolio/position_sizing の価格欠損（price が 0.0 など）時の振る舞いに TODO コメントあり（将来的にフォールバック価格を検討）。
- research/factor_research.py はファクター計算の骨子（モメンタム等）を追加中（ファイル末尾が未完の状態のため一部実装が途中）。本リリースではスケルトンおよび定数類と calc_momentum の冒頭が含まれています。
- run_monitoring は監視用 DB に対し常に本番 sqlite_path を使う設計（意図的）。運用上の注意を要します。

### Security
- .env ファイルは絶対に Git にコミットしない旨を README / ウィザードの出力に明記。

---

今後の予定（例）
- research/factor_research の完全実装（各ファクターの SQL/集計ロジック完成）。
- broker / execution 関連のユニットテスト追加。
- portfolio 周辺で銘柄別 lot_size サポート、価格フォールバックロジックの実装。
- 監視・実行の systemd / container 向けユーティリティ追加。

(以上)
# Changelog

すべての注目すべき変更点はこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-20

初回公開リリース。KabuSys のコア機能（環境設定、起動スクリプト、ポートフォリオ構築ロジック、発注/監視起動、ユーティリティ、検証ツール等）をまとめて実装しています。

### Added
- パッケージ基礎
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として導入。
  - public API エクスポート（portfolio / execution / monitoring 等の主要モジュール）を定義。

- 環境設定・管理
  - .env 自動ロード機能を追加（プロジェクトルートの `.env` / `.env.local` をロード）。OS 環境変数が優先され、`.env.local` は上書き可能。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化フラグを実装。
  - .env パーサを実装（コメント、export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの一部取り扱いに対応）。
  - `Settings` クラスを追加し、環境変数の取得と妥当性チェックを提供（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の検証・既定値を含む）。
  - `.env` を対話式に作成・更新するウィザード CLI (`kabusys.config_setup`) を追加（`--env-file` オプション対応、シークレット入力マスク、確認後ファイル書き出し）。

- 起動スクリプト
  - Execution エンジン起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` 時はペーパートレード用 DB を使用（本番 DB と分離）。
    - ブローカークライアントを `BrokerClientFactory` 経由で生成（paper_trading 時はモックを利用する想定）。
    - `ExecutionEngine` の組み立てとデーモンスレッド起動、停止フラグ検出による安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視テーブルの存在を保証するため `init_monitoring_db` を実行（冪等）。
  - Monitoring ポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - Monitoring は環境に関係なく本番 `sqlite_path` を使用する旨の動作。
    - 起動時にプロセス優先度を "high" に設定、停止フラグ検出でループ終了。
    - DuckDB / SQLite の接続を初期化し監視用テーブルを準備。

- ポートフォリオ構築（純粋関数群）
  - 銘柄候補選定・重み付け
    - `select_candidates`：スコア降順（同点時は signal_rank 小さい方優先）で上位 N を選択。
    - `calc_equal_weights`：等金額配分を計算。
    - `calc_score_weights`：スコア比例配分を計算（全スコアが 0 の場合は等金額配分にフォールバックし WARNING）。
  - リスク調整
    - `apply_sector_cap`：既存保有のセクター比率が上限を超える場合は同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - `calc_regime_multiplier`：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知のレジームは警告を出して 1.0 フォールバック）。
  - ポジションサイジング
    - `calc_position_sizes`：`risk_based` / `equal` / `score` の配分方式に対応。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金超過時のスケーリング）や cost_buffer による保守的コスト見積りを実装。スケールダウン時は残差を考慮してロット単位で追加配分。

- ユーティリティ
  - ロギング設定ユーティリティ `setup_logging` を追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（30 日保持）をルートロガーにセット。
    - ログレベルとログディレクトリは引数→環境変数→デフォルトの順に解決。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラをクリアして二重出力を防止。
  - プロセス優先度・CPU affinity 設定ユーティリティ `set_process_priority` / `set_cpu_affinity` を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応した優先度設定を行う。アクセス権限不足や未対応 OS では警告を出してスキップする実装。

- 検証・レポートツール
  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードなど。
    - `--strict` オプションで警告を FAIL 扱いにできる。
  - Paper Trading 検証レポート `kabusys.tools.paper_verification_report` を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。CLI で期間指定（--from/--to）および DB パス指定（--db）に対応。
    - P95 関数、クエリの頑健性（テーブルがない場合にスキップ）等を実装。
    - しきい値（稼働率 99%, 成功率 90% 等）を定義。

### Changed / Design decisions
- 環境変数読み込み順序と保護
  - OS 環境変数は常に保護され、.env/.env.local の読み込みで上書きされない（ただし .env.local は override=True による上書き動作を行うが protected により OS 環境は保持）。
- .env の取り扱い
  - export プレフィクスやクォート、エスケープの扱い、インラインコメントの一部取り扱いに対応し、より現実的な .env 書式をサポート。
- ログ出力先
  - ログを stdout に出すことで、cron や Task Scheduler 等のランナーで stdout/stderr を一元管理できるように設計。
- 起動時のプロセス優先度
  - 重要なワーカー（execution / monitoring）は起動直後に優先度を "high" に設定するよう統一。
- Paper Trading と本番 DB の分離
  - paper_trading 環境用に別 SQLite DB（デフォルト: data/paper_trading.db）を利用し、本番の monitoring DB と完全に分離する設計。

### Fixed / Robustness
- ログハンドラの二重設定を避けるため、setup_logging は既存ハンドラを明示的に flush/close → remove してから再設定するようにした。
- .env 読み込み失敗時は警告を発生させ、処理を継続する（テスト実行や権限問題に耐性）。
- process_priority / set_cpu_affinity は AccessDenied 等の例外を捕捉し、警告を出して処理を継続する仕様にしている（運用環境の権限差に耐性）。
- run_execution / run_monitoring は停止フラグファイル（data/stop_requested.flag 等）を検出して安全に起動/停止する仕組みを導入。

### Notes / Known limitations
- research.factor_research の一部（ファクター計算）が実装途上（ファイル末尾が断片的）。将来リリースで各ファクターの完全実装・テストを追加予定。
- position_sizing の lot_size は現状はグローバル固定（デフォルト 100）。将来的には銘柄ごとの単元情報を参照する拡張を予定（コメントに TODO を記載）。
- apply_sector_cap は price_map の欠損（価格 0.0）によりエクスポージャーを過少見積もる可能性があり、将来的にフォールバック価格（前日終値等）を導入予定。
- `.env` ファイルは機密情報を含むため、絶対にリポジトリにコミットしない旨を config_setup のヘッダに明記。

---

このリリースは初版機能群の提供に焦点を当てています。今後は以下を予定しています:
- research モジュール内の各ファクター計算の完成・最適化
- ExecutionEngine / BrokerClient の統合テストおよびエンドツーエンドの検証
- モニタリング・アラートの充実（LINE 通知の整備、閾値ベースの通知）
- ポートフォリオ構築アルゴリズムのチューニングと自動テスト拡充

ご要望・不具合報告は issue にてお知らせください。
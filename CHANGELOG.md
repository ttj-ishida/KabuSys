# Changelog

すべての重要な変更を記録します。このプロジェクトは Keep a Changelog 準拠の形式を採用しています。セマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-23

### 追加
- 基本アプリケーション初期実装を追加。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"` に設定。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を使ってブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを起動。
    - 停止フラグ (data/stop_requested.flag) を検知すると安全に停止。
    - エンジン実行はデーモンスレッドで行い、PID ファイルに対応。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔オーバーライド（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を使用して接続（監視テーブルを初期化）。
    - 停止フラグ (data/stop_requested.flag) を検知するとループを終了。
- 設定管理
  - config.py: .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
    - 自動 .env 読み込み:
      - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を読み込む（OS 環境変数は保護）。
      - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサは以下をサポート:
      - `export KEY=val` 形式
      - シングル/ダブルクォート内のバックスラッシュエスケープ
      - クォート無しでのインラインコメント処理（直前に空白/タブがある '#' をコメントと認識）
    - 必須値チェック `_require()` による未設定時の例外
    - 各種プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path など）を提供
    - `PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` 等の値検証（不正値で ValueError）
    - `settings`（モジュールレベルの Settings インスタンス）をエクスポート
- 設定ツール
  - config_setup.py: 対話式ウィザードで `.env` を作成/更新する CLI を追加。
    - シークレットのマスク表示、デフォルト値、選択肢、保存確認などを備える。
    - 生成される `.env` にはセクション付きのコメントヘッダを含む。
  - validate_config.py: 起動前の設定検証用 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML がある場合はパース検証）を実施。
    - `--strict` オプションで警告を失敗扱いにする。
- ロギング・ユーティリティ
  - utils/logging_setup.py: 統一されたログ設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力）と、日次ローテーションする TimedRotatingFileHandler（既定 logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして再設定することで二重登録を防止。
- プロセス優先度ユーティリティ
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定 API を追加。
    - `set_process_priority(level: "high" | "normal" | "low")` を提供し、Windows では priority class、POSIX では nice 値を設定。
    - 権限不足や非対応 OS の場合は警告ログを出して安全にスキップ。
    - `set_cpu_affinity(cpu_count: Optional[int])` で先頭 N コアに固定可能（権限エラーは警告でスキップ）。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定 select_candidates（score 降順、同点時は signal_rank 昇順タイブレーク）
    - 等金額配分 calc_equal_weights
    - スコア加重 calc_score_weights（全スコアが 0 の場合は等金額にフォールバックして警告）
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値を超える場合に候補を除外、"unknown" セクターは除外しない）
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" マッピング、未知レジームは警告して 1.0 をフォールバック）
  - portfolio/position_sizing.py:
    - 株数計算 calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score" 対応）
    - 単元（lot_size）丸め、1 銘柄上限・総投下上限（aggregate cap）を実装。上限超過時はスケーリングして、端数は lot 単位で残差順に追加配分。
    - cost_buffer により保守的見積りが可能。
  - portfolio/__init__.py で主要関数をエクスポート
- 解析 / レポートツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）などを SQLite（デフォルト data/paper_trading.db）から集計してレポート化。
    - CLI 引数で期間指定 (--from, --to) および DB パス指定 (--db) に対応。
    - 判定基準は定数化（稼働率 99% など）されており、PASS/FAIL 判定を出力。
- 研究用モジュール
  - research/factor_research.py: ファクター計算モジュール（モメンタム・ボラティリティ等の計算基盤）を追加（DuckDB を用いる設計、prices_daily/raw_financials テーブル参照を想定）。一部の実装（calc_momentum の先頭）が含まれる。

### 変更
- DB 初期化
  - run_execution と run_monitoring の両方で監視テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等）。
- ログ出力の標準化
  - 全スクリプトは起動時に setup_logging(app_name=...) を呼ぶことで統一的にログ出力先とフォーマットを制御するように変更。
  - コンソール出力は stdout を使用する（stderr ではない）。
- .env 読み込み優先度
  - OS 環境変数 > .env.local > .env の優先順位で読み込む。既存の OS 環境変数は保護（上書きされない）。

### 修正
- .env パーシングの堅牢化
  - クォート内のバックスラッシュエスケープに対応し、export プレフィックスやインラインコメントの扱いを改善。
  - 不正な MONITOR_POLL_INTERVAL 等の数値環境変数は警告を出してデフォルト値にフォールバック（監視ループで ValueError を回避）。
- process_priority / cpu_affinity のエラー耐性強化
  - 権限不足や未サポート環境で例外を握りつぶし、警告ログを出して処理を継続するようにした。
- run_execution の停止処理を安全化
  - 停止フラグ検出時にエンジン.stop() を呼びスレッド終了を待つ仕組みを導入。
- paper_verification_report の堅牢化
  - テーブルが存在しないケース（OperationalError）を想定してデフォルト値にフォールバックするようにした。

### 既知の制限 / 注意点
- research/factor_research.py はモジュール設計・定数類は含まれるが、calc_momentum の実装が途中で切れている（未完成部分あり）。
- position_sizing の単元丸めや価格欠損時の挙動（価格が 0.0 の場合にエクスポージャーが過小見積りされる等）についてはコード内に TODO コメントがあり、将来的にフォールバック価格等の改善が検討される予定。
- monitor（run_monitoring）は KABUSYS_ENV にかかわらず監視用 DB に本番 sqlite_path を使う設計になっているため、テスト環境で別 DB を使いたい場合は設定に注意が必要。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソール出力のみとなる（警告を標準エラーに出力）。

---

今後の予定:
- research モジュールの完全実装（ファクター計算の SQL / Python 実装完了）。
- テストカバレッジの追加（ユニットテスト・統合テスト）。
- 発注ロジック・ブローカーインターフェースの拡張（実アカウント運用に向けた安全対策の強化）。
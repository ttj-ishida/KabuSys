# Changelog

すべての重要な変更をこのファイルで記録します。  
フォーマットは Keep a Changelog 準拠です。

なお、本リリースはパッケージ内のコードから推測して作成した初期リリース向けの変更履歴です（version: 0.1.0）。

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーション初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は専用の MockBrokerClient を用い、paper_trading 用 DB（既定: `data/paper_trading.db`）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定（`utils.process_priority.set_process_priority`）。
    - 停止制御: `data/stop_requested.flag` により実行中エンジンを停止。
    - PID 書き出し: `data/execution.pid` を使用。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（既定: 60秒）。不正な値はログ警告を出して既定にフォールバック。
    - Monitoring は環境にかかわらず本番用 `sqlite_path` を使用。
    - 停止制御: `data/stop_requested.flag` を検知してループを終了。
- 設定関連
  - config.py
    - プロジェクトルート自動検出（`.git` または `pyproject.toml` を基準）に基づく `.env` 自動ロード機能を実装（`.env` → `.env.local` の優先順位と OS 環境変数保護をサポート）。
    - 環境変数読み取りユーティリティ `Settings` を提供（各種設定プロパティ、検証、Paper Trading 用 DBパス、各種閾値等を包含）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを実装（コマンド: `python -m kabusys.config_setup`）。
    - デフォルト・説明付きの設定項目一覧（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連等）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI（`--strict` フラグで警告を失敗扱いにできる）。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、パスの親ディレクトリ存在確認、YAML ファイルのパース確認（PyYAML 未インストール時は警告）などを実施。
- ロギング・ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるログ設定ユーティリティを提供。
    - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ファイルは既定 `logs/<app_name>.log`（30日分保持）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし stdout のみで継続。
    - ログレベル・ログディレクトリは引数・環境変数で上書き可能。
- プロセス管理ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX を吸収してプロセス優先度（"high"/"normal"/"low"）を設定するユーティリティを実装。
    - CPU affinity を最初の N コアに固定する関数 `set_cpu_affinity` を提供。
    - 権限不足や未対応プラットフォームの場合は警告を出して安全にスキップ。
- Portfolio コンポーネント（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補選定 (`select_candidates`) と重み計算 (`calc_equal_weights`, `calc_score_weights`) を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap` を実装。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier` を実装（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック `calc_position_sizes` を実装（allocation_method: "risk_based"/"equal"/"score" をサポート）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash） に基づくスケーリング、端数分配ロジックを実装。
    - cost_buffer による保守見積もりをサポート。
    - TODO コメントで将来的な lot_size の銘柄別対応や価格フォールバックの改善を記載。
- 研究・分析用モジュール（下位実装）
  - research/factor_research.py（ファクター計算の枠組みを実装）
    - モメンタム、ボラティリティ、流動性、バリュー等の計算方針と定数を定義（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
    - 関数 `calc_momentum` 等の計算インタフェースを備える（実装は一部。コード末尾で切れているが設計が示されている）。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレード履歴を解析して検証レポートを出力するスクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等。
    - デフォルト DB: `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で上書き可能）。
    - パスが存在しない場合のエラーメッセージや SQL テーブルが無い場合のフォールバックを実装。
    - しきい値（PASS/FAIL 判定）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

### Changed
- 初版リリースとして、設計上の注意点・既知の挙動を明記。
  - `.env` 自動ロードの優先順位および保護機構（OS 環境変数の保護）を実装。
  - ログは stdout とファイル両方に出力するが、ファイル出力が失敗した場合は stdout のみで継続する実装により堅牢性を向上。

### Fixed
- （初期リリース）主要なクラッシュを回避する保護処理を多数追加。
  - 無効な MONITOR_POLL_INTERVAL 値に対するフォールバック（警告を出して既定値を使用）。
  - DB またはテーブルが存在しない場合のフォールバックロジック（paper_verification_report などで OperationalError を捕捉して処理を継続）。
  - 権限不足でのプロセス優先度設定や CPU affinity 設定の例外を安全にハンドリング。

### Known issues / Notes
- research/factor_research.py は関数の実装途中でファイルが末尾で切れている箇所がある（calc_momentum の実装は設計が始まっているが未完の可能性あり）。実行前に完全実装を確認してください。
- position_sizing.py と risk_adjustment.py にいくつかの TODO コメントあり:
  - 価格が欠損（0.0）の場合のフォールバック（前日終値や取得原価）を将来の改善点として記載。
  - 将来的に銘柄別 lot_size 対応を検討。
- Logging 設定でログディレクトリの作成に失敗した場合はファイル出力が無効化されるが、当該警告は stderr に出力される点に注意。
- `validate_config` は PyYAML が未インストールの場合は YAML ファイル内容検証をスキップして警告を出す仕様。

### Migration notes
- 環境構築時はまず `.env` を作成し、`python -m kabusys.config_setup`→`python -m kabusys.validate_config` の順で設定確認を推奨します。
- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` は既定で 0 を推奨（自動クリアを有効にすると危険）。
- Paper Trading と本番 DB は分離されているため、`KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite を使用する点に注意してください。

---

今後の改善案（参考）
- research モジュールの完成とユニットテスト追加。
- 銘柄ごとの lot_size サポートと価格フォールバックロジックの実装。
- より詳細な監視アラート（LINE 通知等）の統合テストとドキュメント整備。
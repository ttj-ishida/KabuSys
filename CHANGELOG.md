# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 全体
  - 初期リリース。パッケージバージョンを `__version__ = "0.1.0"` と設定。
- 設定・環境読み込み
  - Settings クラスによる環境変数ラッパーを実装（kabusys/config.py）。J-Quants・kabu API・DBパス・監視閾値などをプロパティで安全に取得できるようにした。
  - 自動 .env ロード機能を追加。プロジェクトルート（.git または pyproject.toml を基準）を検出し、`.env` と `.env.local` を OS 環境変数を保護しつつ読み込む仕様を導入。
  - .env パーサーを強化し、`export KEY=...` 形式、クォート付き値（エスケープ処理含む）、インラインコメントの扱いをサポート。
- 設定ウィザード / 検証 CLI
  - 対話式 .env 設定ウィザードを追加（kabusys/config_setup.py）。初回設定や既存 .env の更新をサポートし、シークレット値はマスク表示。
  - 設定検証ツールを追加（kabusys/validate_config.py）。必須環境変数・KABUSYS_ENV の妥当性・DBパス・config/*.yaml の存在とパース（PyYAML があれば内容検証）・本番向けガード等をチェック。`--strict` オプションで警告を失敗扱いにできる。
- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（`PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`）に分離して記録し、MockBrokerClient を使用する設計を想定。
    - 起動時にプロセス優先度を High に設定するフックを追加。
    - 停止フラグ（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）に対応。エンジンは別スレッドで動作し、停止フラグ検知で安全に停止する。
  - 監視（SystemMonitor）用起動スクリプトを追加（kabusys/run_monitoring.py）。
    - 環境にかかわらず本番の sqlite_path（監視 DB）を使用して監視テーブルを初期化する設計。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）、不正値はログ警告のうえデフォルトにフォールバック。
    - 停止フラグの検知でループを終了する仕組みを実装。
- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログファイル（デフォルト logs/<app_name>.log）を出力。既存ハンドラの重複登録を避けるため一旦クリアしてから設定する。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続する安全設計。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する実装。優先度 (high/normal/low) および CPU affinity を設定。権限不足や未対応プラットフォームでは警告を出してスキップ。
- ポートフォリオ構築（純関数群）
  - 銘柄選定と重み計算（kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights を実装。スコアが全て 0 の場合は等分配にフォールバックして警告。
  - セクター集中・レジーム調整（kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：既存保有のセクター比率に基づき新規候補を除外するロジックを実装（unknown セクターは制限対象外）。
    - calc_regime_multiplier：レジーム（bull/neutral/bear）に応じた投下資金乗数を返すユーティリティ。未知レジームでは 1.0 にフォールバックして警告出力。
  - 株数算出 / リスク制限（kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：risk_based / equal / score の各割当方法に対応し、単元株（lot_size）丸め、1株当たり上限、aggregate cap（利用可能現金でのスケーリング）、cost_buffer を考慮した保守的見積もりなどを実装。スケールダウン時の端数配分ロジックも実装。
  - 上記機能をパッケージエクスポート（kabusys/portfolio/__init__.py）。
- Paper Trading 検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計し、PASS/FAIL 判定を出力。
    - P95 計算・日付フィルタ・DB パス解決（引数 > 環境変数 > デフォルト）を実装。
- research モジュール（着手）
  - factor_research モジュールを追加（kabusys/research/factor_research.py）。DuckDB 接続を受け取り価格・財務データからモメンタム等のファクターを計算する設計。モジュールは関数設計・定数定義を含み、一部実装が継続中。

### 変更 (Changed)
- DB の取り扱い
  - 監視（run_monitoring）は KABUSYS_ENV に関わらず本番用の sqlite_path を使う設計とした（監視 DB を本番運用で一元管理する意図）。
  - 実行エンジンは paper_trading 環境時に paper_sqlite_path を使って本番 DB と完全に分離する仕様を明確化。
- .env 読み込み順
  - OS 環境 > .env.local > .env の優先順位でロードする仕様を明示。`.env.local` は OS 環境を上書きできるが、OS 環境で既に設定されたキーは保護される。

### 修正 (Fixed)
- .env パースの堅牢化
  - 引用符付き値のエスケープ・閉じクォート検出、`#` によるコメント扱いの条件（クォート外・直前が空白）等を正しく処理するロジックを導入し、より現実的な .env の記述に対応。
- ログ設定の堅牢化
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合でもコンソール出力にフォールバックするようにして、起動失敗を防ぐよう改善。
- プロセス優先度設定の安全化
  - 権限不足や未対応 OS で例外が発生しても警告ログを出してスキップするようにし、起動失敗しないように改善。

### 注意事項 / ガード (Notes)
- validate_config によるチェックでは PyYAML が未導入の場合に YAML の検証をスキップする。config/*.yaml の内容検証を行うには PyYAML のインストールが必要。
- Settings.paper_fill_mode は有効値を厳密にチェックし、無効な値は ValueError を送出する。
- run_monitoring の MONITOR_POLL_INTERVAL は 1 未満の値や非数が与えられた場合、デフォルト 60 秒にフォールバックして警告を出す（time.sleep に負の値を渡すのを防止するため）。
- KABUSYS_ENV=live の場合は validate_config が追加の警告（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定）を出すように設計されているため、本番導入前に必ず確認を推奨。

### 削除 (Removed)
- 該当なし

### セキュリティ (Security)
- 該当なし

---

以上がコードベースから推測可能な主な変更点・追加機能の一覧です。必要であれば、各ファイルごとの簡易使用例や設定例（.env の推奨値等）を付け加えた詳細版の CHANGELOG を作成します。
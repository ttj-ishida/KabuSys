# Keep a Changelog

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の慣例に従っています。

なお、記載内容はソースコードから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース。パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
- 起動スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。不正値の場合はデフォルトにフォールバックして警告を出力。
    - 停止制御のためのフラグファイル `data/stop_requested.flag` を監視して安全にループを終了。
    - 監視用 DB は環境にかかわらず production の `sqlite_path` を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して paper trading 用の専用 SQLite（デフォルト `data/paper_trading.db`）に記録することで本番 DB と分離。
    - 実行中の PID 管理（`data/execution.pid`）および停止フラグ `data/stop_requested.flag` を用いた安全停止処理を実装。
    - ExecutionEngine を別スレッドで実行し、外部フラグ検出で停止指示を送る仕組みを搭載。
- 設定/環境管理:
  - config.py
    - Settings クラスを提供し、環境変数経由で設定を参照する統一 API を実装。
    - .env ファイルの自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。OS 環境変数を保護する仕組みあり。
    - .env パーサが以下をサポート: `export KEY=val`、シングル/ダブルクォート内のエスケープ、行末コメントの取り扱い。
    - 多数のプロパティ（`duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, 各種閾値、`env`/`log_level` 検証など）を提供。
    - `PAPER_FILL_MODE`（paper trading の約定挙動）や `KABUSYS_ENV` の妥当性チェックを実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット値はマスク表示、各項目の説明やデフォルト提示あり。
    - `.env` 書き込み時にコメントヘッダを付与し、`Git にコミットしない`旨を明記。
  - validate_config.py
    - 起動前に環境変数や `config/*.yaml` の不備を検出する検証 CLI を追加。
    - 必須環境変数（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）のチェック、`KABUSYS_ENV`・`LOG_LEVEL` の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在/パースチェック（PyYAML があれば内容まで検証）などを実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築関連（純粋関数群、メモリ内処理）:
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、同点時 signal_rank でタイブレーク）、等金額重み、スコア加重重みを実装。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）実装。既存保有比率が閾値を超えるセクターは新規候補から除外。`unknown` セクターは適用除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（`bull`, `neutral`, `bear` をサポート。未知レジームは警告のうえ `1.0` にフォールバック）。
  - portfolio/position_sizing.py
    - position sizing（risk_based / equal / score の allocation_method）を実装。損切り率・リスク許容率・上限比率・単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積りを実装。スケーリング後の端数配分は残差（fractional remainder）順に lot 単位で追加配分する仕組みを実装。
  - portfolio/__init__.py で上記関数群を公開。
- ユーティリティ:
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。root ロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代保持）を設定。既存ハンドラをクリアして二重設定を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
    - 標準エラーではなく stdout を使用する仕様（cron/Task Scheduler で stdout/stderr を一本化する運用に配慮）。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加（`set_process_priority("high"|"normal"|"low")`）。Windows と POSIX（Linux/Mac/FreeBSD）をサポートし、権限不足や未対応 OS の場合は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を実装（権限等で失敗した場合は警告してスキップ）。
- ツール:
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。`PAPER_TRADING_SQLITE_PATH` を参照して指定期間（`--from`/`--to`）の集計を行う。
    - 指標: 稼働率 (uptime_pct)、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）などを算出し PASS/FAIL 判定を出力。閾値はソース内に定義（例: 稼働率 99% など）。
    - DB テーブル存在チェックやパース例外に対するフォールバックを備える。
- research/factor_research.py（ファクター計算基盤を追加、モメンタム等の計算を実装予定）
  - DuckDB を用いた価格・財務データ参照ベースでモメンタム、ボラティリティ、流動性、バリュー指標等を計算する設計。関数は DuckDB 接続と target_date を受け取り純粋関数で結果を返す想定（モジュール内に詳細実装の一部あり）。
- パッケージ構成: 多数のモジュールに対して docstring・使用例を充実させた。

### Changed
- ログ出力: ログのデフォルト出力先を stdout に統一し、ファイル出力はログディレクトリ作成に成功した場合のみ有効化することで、ファイル書き込みエラーによる起動失敗を回避するようにした。
- 起動時にプロセス優先度をデフォルトで "high" に設定する呼び出しを実行スクリプトの早期に配置（run_monitoring/run_execution）。これによりスクリプト起動直後に優先度調整を試行する。
- .env 自動読み込みの挙動:
  - OS 環境変数を保護（override を制御）し、`.env.local` を `.env` より後に上書き可能とした。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

### Fixed / Robustness
- MONITOR_POLL_INTERVAL が不正（非整数や負数）の場合に起動が失敗しないよう、警告を出してデフォルト値にフォールバックする実装を追加。
- .env パーシング: クォート内のエスケープや inline コメント処理の強化により、実務的な .env 記述に対して安定した読み込みを可能にした。
- validate_config: PyYAML 未インストール時は YAML パース検証をスキップして警告を出すようにし、依存の有無により挙動が壊れないようにした。
- position_sizing のスケーリングロジックで cost_buffer を考慮し、aggregate cap 超過時に余剰キャッシュを用いて lot 単位で再配分するロジックを導入（過少・過大発注を回避）。

### Documentation
- 各モジュールに docstring を充実。CLI スクリプトに対する使用例や環境変数の説明を追加。
- config_setup が生成する .env ヘッダに Git にコミットしないよう注意書きを記載。

### Breaking Changes
- なし（初回リリース）。ただし監視系の設計上、run_monitoring は実行環境にかかわらず production 用 `sqlite_path` を参照する挙動があるため、運用時に意図しない DB を参照しないよう注意が必要。

### Security
- .env は秘匿情報を含むため、config_setup の出力およびリポジトリにコミットしないよう明記。

---

今後の予定メモ（ソースからの推測）
- research/factor_research の機能実装完了・テストカバレッジ拡充
- strategy / execution の統合テスト、paper_trading の挙動検証自動化
- ユニットテスト・CI の整備とリリースワークフローの確立

もし CHANGELOG に追加したい注目点（優先すべき改善や既知の注意点）があれば教えてください。必要に応じてバージョン別により細かい差分分割も行えます。
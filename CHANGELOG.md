# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
各項目はコードベースから推測できる機能追加・挙動・改善点を日本語で記載しています。

## [0.1.0] - 初回リリース
（注: バージョン番号は src/kabusys/__init__.py の __version__ に基づく想定）

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いて実際のブローカー／モックを環境に応じて選択。
    - エンジンはスレッドで実行され、data/stop_requested.flag による外部停止要求を監視して安全に停止する仕組みを実装。
    - 実行中の PID を data/execution.pid に保存する機能（pid_file 連携）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず監視用 sqlite_path を使用する（本番 sqlite を参照して監視する設計）。
    - data/stop_requested.flag による外部停止検知を実装。
    - KeyboardInterrupt による終了処理をサポート。

- 設定・環境管理
  - config.py
    - 環境変数ラッパー Settings クラスを提供（各種設定をプロパティで取得）。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH などの環境変数を扱う。
    - KABUSYS_ENV の値検証（development / paper_trading / live）や LOG_LEVEL の検証を実装。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - 必須項目・デフォルト・説明・シークレット項目（マスク表示）をサポートし .env を書き出す。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML が無い場合は警告）などを実行。
    - --strict モードで警告を失敗扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 一貫したロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続するフォールバックを実装。
  - utils/process_priority.py
    - Windows/Linux/macOS を透過してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity 設定関数 set_cpu_affinity を提供（指定が None の場合は変更しない）。
    - 権限不足や非対応 OS では警告を出してスキップする。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークロジック実装）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額配分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap：既存保有に基づいてセクター比率が閾値を超える場合に候補から当該セクターを除外。
    - レジーム乗数 calc_regime_multiplier：regime ラベルに応じて投下資金乗数（bull/neutral/bear）を返す。未知のレジームは警告を出し 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - position sizing ロジック calc_position_sizes（allocation_method: risk_based / equal / score）。
    - lot_size に基づく丸め、max_position_pct（1銘柄上限）、max_utilization（総投下上限）、cost_buffer（スリッページ/手数料の保守的見積り）を考慮したスケーリング処理を実装。
    - aggregate cap 超過時のスケーリングと残差に対する再配分ロジックを実装。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）を算出。
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間や DB を指定可能。

- DB 接続
  - run_* スクリプトやツールで sqlite3 と DuckDB（duckdb パッケージ）を使用する実装を追加（duckdb_path / sqlite_path を環境変数で指定可能）。

### Changed
- ロギングの既定動作を統一
  - すべての起動スクリプトは setup_logging を呼び出して stdout と日次ローテートファイルに出力するように統一。

- .env 読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で読み込む。既存 OS 環境変数を保護するため protected セットを使用。

### Fixed / Robustness
- .env パースの堅牢化
  - クォート文字内のバックスラッシュエスケープ、export プレフィックス、行内コメントの取り扱いなどを考慮して .env 行のパースを改善。
  - 無効行のスキップや読み込み失敗時の警告出力を実装。

- ログディレクトリ作成失敗時のフォールバック
  - ログディレクトリの作成に失敗してもコンソールログは継続するように修正（ファイルハンドラ作成失敗は警告）。

- 実行・監視プロセスの安全な停止
  - data/stop_requested.flag による停止検知を run_execution / run_monitoring に追加。実行中は安全に停止処理を行う。
  - run_execution の場合、停止フラグ検知時に Engine.stop() を呼んでセッションを終了させる。

- 環境変数の検証と起動前チェック
  - validate_config により起動前に主要な環境変数や config/*.yaml の存在・パースをチェックし、問題を事前検出できるようにした。

### Notes / Design Decisions
- 監視（monitoring）は KABUSYS_ENV にかかわらず監視用 sqlite_path（Settings.sqlite_path）を使用する設計となっている（意図的に本番監視 DB を参照する想定）。
- apply_sector_cap はセクターが不明（"unknown"）な銘柄に対しては上限適用を行わない（除外しない）。
- calc_regime_multiplier は未知レジーム時に警告を出し、保守的に 1.0 でフォールバックする。
- position sizing の将来的拡張点として、lot_size を銘柄毎にする（stocks マスタに lot_size を持たせる）ことがコメントで示唆されている。

### Known limitations / TODO
- research/factor_research.py はファクター計算の実装が途中で切れている（calc_momentum の実装続きが必要）。
- 一部の TODO コメントに示された機能（価格フォールバック、銘柄別 lot_size 等）は未実装。
- YAML コンテンツ検証は PyYAML に依存するので、未インストール環境ではスキップされる（警告）。

---

この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、特定ファイルの変更点ごとにより詳細な項目を追記します。
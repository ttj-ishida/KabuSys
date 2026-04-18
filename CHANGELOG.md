# Changelog

すべての重要な変更は Keep a Changelog 準拠で記録します。  
このファイルはコードベースの内容から推測して作成しています。

全般:
- 初期リリース相当の機能群を追加（実行/監視ランナー、設定管理、ポートフォリオ構築、ユーティリティ類、解析ツールなど）。

## [0.1.0] - 2026-04-18

### Added
- 実行エンジン起動スクリプト run_execution.py を追加
  - ExecutionEngine を組み立てて別スレッドで run_session を実行するエントリポイントを提供。
  - BrokerClientFactory によるブローカークライアント生成を導入（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用してペーパートレード用 DB に記録）。
  - OrderRepository / OrderManager / Reconciler / RiskManager の組み立てロジックを追加。
  - stop フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による起動/停止管理を実装。
  - ペーパートレード時は paper_sqlite_path を使い本番 DB と分離する挙動を採用。

- 監視ポーリング起動スクリプト run_monitoring.py を追加
  - SystemMonitor を初期化して定期ポーリングを行うループを追加。デフォルトポーリング間隔は 60 秒。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。不正値はデフォルトへフォールバック。
  - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する設計。
  - 停止フラグ（data/stop_requested.flag）を検知してループ終了。

- 設定管理モジュール config.py を追加
  - .env 自動読み込み機能を実装（OS 環境 > .env.local > .env の優先順）。
  - プロジェクトルート検出（.git または pyproject.toml）に基づく .env ロード。ルートが見つからない場合は自動ロードをスキップ。
  - .env 行パーサーは export 形式、クォート（シングル/ダブル）のエスケープ、インラインコメント処理などに対応。
  - Settings クラスで各種設定値をプロパティとして提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連、閾値設定、KABUSYS_ENV/LOG_LEVEL の検証など）。
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）とエラー報告。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- 設定検証 CLI validate_config.py を追加
  - .env と config/*.yaml の存在・基本整合性チェックを実行する CLI を提供。
  - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、YAML パース（PyYAML がある場合）を実施。
  - `--strict` オプションで警告を失敗扱い（exit 1）にするモードを提供。
  - 本番 (KABUSYS_ENV=live) 向けの追加警告（LINE 通知未設定や Kill Flag 自動クリア設定）を提供。

- 環境設定ウィザード config_setup.py を追加
  - 対話式ウィザードで .env を初期作成/更新するツールを提供。
  - 秘密値のマスク表示、選択肢・デフォルト、既存 .env の読み込み対応、保存確認などを実装。
  - .env 書き込みテンプレートを組み込み（コメント付き）。

- ポートフォリオ構築モジュールを追加（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates: スコア降順で候補選択（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア重み配分（スコア合計0時は等配分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限判定と候補除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: レジームに基づく資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出、lot_size 単位丸め、単銘柄上限・aggregate cap（利用可能現金）によるスケーリング、残差の lot 単位追加配分ロジックを実装。

- ロギングユーティリティ utils/logging_setup.py を追加
  - setup_logging 関数でルートロガーを初期化（StreamHandler を stdout に設定、TimedRotatingFileHandler で日次ローテーション、30日保持）。
  - ログレベルおよびログディレクトリの解決順（引数 > 環境変数 > デフォルト）。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - 既存ハンドラは安全に flush/close してから再設定（多重ハンドラ防止）。

- プロセス優先度 / CPU affinity ユーティリティ utils/process_priority.py を追加
  - set_process_priority(level) で Windows / POSIX(Linux/macOS/FreeBSD) を吸収して優先度設定を試行。権限不足等は警告でスキップ。
  - set_cpu_affinity(cpu_count) で最初の N コアに固定する機能（未対応環境や権限不足は警告でスキップ）。
  - 実行スクリプトは起動時にプロセス優先度を "high" に設定するよう呼び出している。

- Paper Trading 検証レポート生成ツール tools/paper_verification_report.py を追加
  - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から統計を集計してレポートを出力。
  - 指標: 稼働率(uptime)、注文成功率(Filled/Created)、送信率(Sent/Created)、リスク却下数、API レイテンシ（avg/max/P95）。
  - P95 計算、日付フィルタ (--from/--to) 対応、閾値判定（稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms）による PASS/FAIL 判定を実装。
  - DB が存在しない場合の案内メッセージを出力。

- 解析 / 研究モジュールの骨組みを追加（research/factor_research.py）
  - DuckDB 接続を受け、Momentum / Value / Volatility / Liquidity 等のファクター算出設計を導入（関数 calc_momentum 等の実装を含むが一部ファイル切断による未完の箇所あり）。

### Changed
- .env の自動読み込みにおいて OS 環境変数は保護され、.env.local が .env より優先して上書き可能な設計に変更（override/protected の仕組み）。
- ログ出力: コンソール出力は stdout を使用（stderr ではない）。cron 等からのリダイレクト運用を意識した仕様。
- 監視: run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する旨を明示（監視 DB と実行 DB の分離を意図）。

### Fixed
- 環境変数パースの堅牢化（export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、無効行スキップ等）。
- ログハンドラ再設定時に既存ハンドラを適切に flush/close してから削除するよう改善（多重ハンドラ設定を防止）。

### Notes / Implementation details
- Settings で KABUSYS_ENV / LOG_LEVEL 等の値検証を行い、不正値は ValueError を発生させる仕様（起動時に早期検出）。
- run_execution では RiskManager の初期設定に broker.get_available_cash() を利用して initial_portfolio_value を設定するため、ブローカー実装は起動時に利用可能現金を返す必要がある。
- position_sizing のスケーリング処理は lot_size 単位での切り捨て／残差配分を行い、合計投下額が利用可能現金を超えないよう補正するロジックを備える。
- monitoring & execution の停止制御はファイルベース（data/stop_requested.flag）を採用。kill/stop フラグの運用方法に注意。

### Removed
- なし（初回リリース相当のため削除履歴なし）。

### Security
- なし特記事項。ただし .env は絶対に Git にコミットしない旨を config_setup の出力で明記。

---

今後の改善候補（コード内の TODO / 注意点から推測）
- price_map の欠損価格（0.0）のフォールバック戦略（前日終値など）を導入して sector exposure 算出を堅牢化する。
- 銘柄ごとの lot_size を取り扱うための拡張（stocks マスタを導入して個別 lot_map を許容）。
- research/factor_research.py の残り実装（ファイル末尾で切れている関数の完成）。
- テスト向けに KABUSYS_DISABLE_AUTO_ENV_LOAD を使った自動ロードの挙動確認・ユニットテスト整備。

もし特定のファイル単位で詳細な差分説明や英語版の CHANGELOG を併記したい場合は教えてください。
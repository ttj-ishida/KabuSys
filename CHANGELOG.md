# Changelog

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリース日: 2026-04-20

## [0.1.0] - 2026-04-20

### Added
- 初回公開: KabuSys コードベースの基本機能群を追加。
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離する。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止に use する stop flag（data/stop_requested.flag）および PID ファイル機構を備える。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する（監視用 DB の扱いを明確化）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）でループを終了。

- 設定管理・支援ツール
  - config.py: .env の自動ロード（.env, .env.local）・設定参照用 Settings クラスを追加。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）を提供し、バリデーションを実施。
  - config_setup.py: .env を対話式に生成・更新するウィザードを追加。
    - 各項目の説明、デフォルト、シークレットマスク表示、保存確認を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在と YAML パース（PyYAML があれば）などをチェック。
    - --strict オプションで警告も FAIL 扱いにできる。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア正規化配分（スコア合計が 0 の場合は等金額にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限をチェックして候補をフィルタ。セクター不明("unknown") は制限対象外。
    - calc_regime_multiplier: market regime（"bull"、"neutral"、"bear"）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックし警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく株数算出。単元（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer を考慮した縮小と再配分アルゴリズムを実装。

- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout 向け StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。ログレベルは引数 > 環境変数 > デフォルト の順で決定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定を追加。
    - set_process_priority(level) で Windows の priority class と POSIX の nice 値を切り替え。失敗時は警告でスキップ。
    - set_cpu_affinity(cpu_count) で最初の N コアにピン留め（失敗時は警告でスキップ）。

- 管理用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH または --db で DB 指定可能（デフォルト: data/paper_trading.db）。
    - システム稼働率、注文成功率（fill_rate）、送信率(send_rate)、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL を判定。
    - デフォルトの合格基準: 稼働率 >= 99.0%、成立率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。

- リサーチ（進行中）
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity 計算の設計・定数を含む）。DuckDB からの prices_daily / raw_financials を想定して実装予定（ファイル末尾に未完の箇所あり）。

- パッケージメタ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

### Changed
- 初期実装として、複数のセキュリティ・可搬性配慮を導入:
  - .env 自動ロード機構はプロジェクトルート探索（.git / pyproject.toml）に基づき、OS 環境変数を保護する protected 機構を導入。
  - logging_setup は stdout をメインに使う設計（cron/task scheduler でのリダイレクト運用を想定）。
  - process_priority はエラーを投げずに失敗を警告で扱う（権限差や未対応 OS を考慮）。

### Fixed
- なし（初回リリース）。

### Removed
- なし。

### Security
- シークレット値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE チャネルトークン等）は .env に保存する想定だが、config_setup の出力ヘッダで「.env は絶対に Git にコミットしないこと」を強調。

### BREAKING CHANGES
- なし（初回リリースだが注意点あり）:
  - 監視プロセス（run_monitoring）は KABUSYS_ENV にかかわらず監視用 DB 接続に settings.sqlite_path（デフォルト data/monitoring.db）を使用します。環境ごとに監視 DB を分けたい場合は設定を上書きしてください。
  - PAPER_TRADING（ペーパートレード）での DB は run_execution が settings.paper_sqlite_path（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）を利用します。運用時は env の設定に注意してください。
  - PAPER_FILL_MODE の値は "instant" / "partial" / "never" / "reject" のいずれかでなければ起動時に例外になります。

### Notes / TODO
- research/factor_research.py は一部未実装の箇所が存在（コメント末尾で切れている）。ファクター計算の SQL 実装を継続予定。
- position_sizing の価格欠損時の扱いや銘柄別 lot_size など将来的な拡張点を TODO コメントとして残している。
- config/*.yaml のテンプレート生成用スクリプト（scripts/generate_config.py）との連携を想定（validate_config で参照）。

---

上記はコードベースから推測して記載した CHANGELOG です。実際のコミット履歴がある場合は、差分に合わせて項目を調整してください。
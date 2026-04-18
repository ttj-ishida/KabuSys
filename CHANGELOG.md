# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

※日付はコードベースから推測して付与しています。

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 初回リリースを追加。
- 実行用スクリプトを追加：
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - デーモンスレッドで engine.run_session を起動し、 data/stop_requested.flag による停止を監視。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト: 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視（monitoring）は KABUSYS_ENV に関わらず本番 sqlite_path（data/monitoring.db 等）を使用。
    - stop_requested.flag による安全停止。
- 環境設定関連ユーティリティと CLI を追加：
  - config.py
    - .env 自動読込み機能（.env, .env.local の順、OS 環境変数は保護）。
    - .env 行パーサーは export プレフィックス、クォート、エスケープ、インラインコメント（空白前の # をコメントと扱う）に対応。
    - Settings クラスを提供し、各種環境変数のラッパー（J-Quants / kabu / DB パス / paper_trading など）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックと便利プロパティ（is_live, is_paper, is_dev）。
  - config_setup.py
    - .env の対話的ウィザード（作成・更新）を追加。秘密値マスク表示、既存値再利用、保存前確認などを実装。
    - .env 書き出し時に Git へコミットしない旨をコメントとして挿入。
  - validate_config.py
    - 起動前に .env と config/*.yaml の簡易検証を行う CLI（--strict オプションで警告も FAIL 扱い）。
    - 必須環境変数の未設定検出、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ確認、PyYAML 未インストール時のスキップや YAML パースエラー検出、live 環境向けの追加ガード（LINE 通知や KILL_FLAG_CLEAR_ON_START の警告）。
- ロギング・プロセス制御ユーティリティを追加：
  - utils/logging_setup.py
    - 全起動スクリプトから利用できる統一的なロギング設定。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）によるファイル出力（既定 logs/、30 日分保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順とフォールバック、ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）。
    - CPU affinity 設定関数 set_cpu_affinity を提供（指定コア数で最初の N コアにピン留め）。
    - 権限不足や未対応環境での安全なフォールバック（警告ログ）。
- ポートフォリオ構築関連モジュールを追加（純粋関数群、DB 非依存）：
  - portfolio/portfolio_builder.py
    - select_candidates: score 降順、同点は signal_rank 昇順でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全銘柄のスコアが 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（売却予定銘柄は露出計算から除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた株数決定（"risk_based"/"equal"/"score"）。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）適用、aggregate cap によるスケールダウンと残差処理（lot 単位で再配分）。
    - cost_buffer を考慮して手数料・スリッページを保守的に見積もる。
  - portfolio/__init__.py でエクスポートを集約。
- Paper Trading 検証ツールを追加：
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite から集計して検証レポートを出力する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）、リスク却下数。
    - デフォルトしきい値: 稼働率 >= 99.0%, 成功率 >= 90%, 送信率 >= 95%, P95 レイテンシ <= 200 ms。
    - 日付フィルタ（--from / --to）をサポート。DB パスは --db / PAPER_TRADING_SQLITE_PATH / デフォルト順で解決。
- research/factor_research.py（未完の計算モジュール）を追加（モメンタム等ファクター計算を想定）。DuckDB 接続を受け取る設計。

### Changed
- プロジェクトルート探索ロジックを実装（config._find_project_root）。
  - __file__ ベースで上位ディレクトリを探索し .git または pyproject.toml を基準にプロジェクトルートを特定。これにより CWD に依存しない自動 .env ロードが可能に。
- .env ローダーの挙動：
  - OS 環境変数を保護する protected 機構を導入し、.env.local は既存 OS 環境変数を上書きしないようにした（ただし override=True の場合 protected を除く上書きを許可）。
- ログ出力は stdout を標準にする設計（cron 等で stdout/stderr を一本化する運用を想定）。
- Execution と Monitoring 起動時に最初にプロセス優先度（high）を設定するよう統一。

### Fixed
- MONITOR_POLL_INTERVAL の負値や 0 による time.sleep の ValueError を防止するため、0 以下の値はデフォルト（60 秒）にフォールバックして警告を出す処理を追加。
- .env パースでクォート内のバックスラッシュエスケープを正しく処理する実装を追加（'"/' 内のエスケープ対応）。

### Notes / Behavioural details
- Monitoring は設計上、KABUSYS_ENV に関係なく常に production sqlite_path（Settings.sqlite_path）を使用する仕様。監視データは本番と同一 DB に記録される点に注意。
- Execution は paper_trading モード時に paper_sqlite_path を使用することで、本番データと完全分離するようになっている。
- validate_config は PyYAML がインストールされていない場合に YAML の内容検証をスキップし、その旨を警告する（環境に依存した柔軟な動作）。
- position_sizing の aggregate cap 処理は可解性のため lot_size 単位で丸め、残余資金がある場合は fractional 残差の大きい銘柄から追加配分するアルゴリズムを採用している（再現性のため同一残差は code を二次キーにする）。
- config_setup によって生成された .env はセキュリティ上の理由で絶対にリポジトリにコミットしない旨がコメントで明記される。

### Developers
- パッケージバージョンを __version__ = "0.1.0" として初期設定。

---

今後のリリース案（例）
- Unreleased:
  - factor_research の実装完了（Momentum / Value / Volatility / Liquidity）。
  - ExecutionEngine 周りの細かいログ・メトリクス追加、テストカバレッジ拡張。
  - 設定検証で config/*.yaml のスキーマ検証追加（jsonschema 等の導入検討）。


# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト: 60秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
    - 監視用途は KABUSYS_ENV に関わらず本番用の sqlite_path を使用。
    - 初期起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を利用し、ペーパートレード専用 DB（data/paper_trading.db、環境変数で上書き可）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定、実行中は停止フラグで安全に停止。
    - 実行管理用 pid ファイル（data/execution.pid）を使用。
- 設定・環境管理
  - config.py
    - .env 自動読み込み機構を追加（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` 環境変数で自動ロードを無効化可能。
    - 必須環境変数取得用ヘルパーと Settings クラスを追加（各種設定プロパティ、デフォルト値およびバリデーション含む）。
    - Paper Trading 周りの設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）をサポート。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 各設定項目の説明、既存値の再利用、シークレット項目のマスク表示などをサポート。
  - validate_config.py
    - 起動前チェック CLI を追加。必須環境変数確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの追加警告を行う。
    - `--strict` オプションで警告もエラー扱いにして終了コード 1 を返す。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合は等金額にフォールバック（警告出力）。
  - portfolio.risk_adjustment
    - セクター集中制限の適用（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知のレジームはフォールバックして警告）。
  - portfolio.position_sizing
    - 株数決定ロジック（calc_position_sizes）を追加。
    - allocation_method として "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregated cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、端数処理ロジック（残余キャッシュによる追加配分）を実装。
    - 将来の拡張点として銘柄別 lot_size の導入を想定する TODO コメントを追加。
- ユーティリティ
  - utils.logging_setup
    - 共通ロギング設定ユーティリティを追加。ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler (日次、30日保持) を設定。ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみ動作。
    - ログレベル解決順: 関数引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
  - utils.process_priority
    - プロセス優先度設定ユーティリティを追加。Windows と POSIX (Linux/Mac/FreeBSD) を吸収してプラットフォーム非依存インターフェースを提供。
    - CPU affinity 設定関数 set_cpu_affinity を追加（N コアにピン留め）。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。
- ツール
  - tools.paper_verification_report
    - ペーパートレード検証レポート生成スクリプトを追加。SQLite DB（デフォルト: data/paper_trading.db）から統計を集計して標準出力でレポートを出力。
    - 集計指標: システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）。
    - CLI 引数: --from / --to（日付範囲）、--db（DB パス）。環境変数 PAPER_TRADING_SQLITE_PATH でも DB パス指定可能。
    - デフォルトの合格基準（しきい値）を定義:
      - 稼働率 >= 99.0%
      - 注文成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
- 研究モジュール
  - research.factor_research
    - DuckDB を用いたファクター計算モジュールを追加（モメンタム、移動平均乖離、ATR、流動性等の計算ロジックを想定）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計。

### Changed
- 初期リリース（特段の互換性破壊はなし）。

### Fixed
- （本リリースでは該当なし）

### Security
- .env 読み込み時の上書き制御:
  - 自動ロード時、OS 環境変数は保護される（.env/.env.local による上書きを防止）。
  - _load_env_file の override/protected 制御により運用上の誤上書きを抑制。

### Notes / その他
- Settings クラス側で多くの設定値にバリデーションを導入:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ有効。
  - LOG_LEVEL は "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" のみ有効。
  - PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のみ有効（不正値は例外）。
- run_monitoring/run_execution は起動直後にプロセス優先度を "high" に設定しようと試みる（権限不足等で失敗した場合は警告）。
- 一部の箇所に将来的な改善点（価格フォールバック、銘柄別 lot_size 等）の TODO コメントを残しています。
- ローカル開発・ペーパートレードと本番を明確に分離する設計を採用。ペーパートレードは専用 DB に記録され、本番 DB とは独立しています。

---

今後のリリースでは以下を予定しています（案）
- ファクター計算の追加カバレッジ・ユニットテスト強化
- 発注関連の統合テスト（MockBroker の挙動検証）
- 設定検証・ウィザードの UI/UX 改善
- 銘柄別 lot_size のサポート、価格フォールバックの実装

もしリリースノートや記載内容で補足してほしい点があれば教えてください。
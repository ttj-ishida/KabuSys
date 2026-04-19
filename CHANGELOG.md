# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
セマンティックバージョニングを使用しています: https://semver.org/

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19

### Added
- 初回公開リリース: KabuSys v0.1.0（パッケージの初期実装を追加）
  - パッケージメタ情報（__version__ = "0.1.0"）を追加。（src/kabusys/__init__.py）

- 実行用スクリプトを追加
  - 実行エンジン起動スクリプト（run_execution.py）
    - プロセス優先度を起動時に "high" に設定する（set_process_priority）。
    - 環境に応じて Paper Trading 用の専用 SQLite を使用（KABUSYS_ENV=paper_trading の場合、PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。
    - BrokerClientFactory によりブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 実行はデーモンスレッドで行い、data/stop_requested.flag により安全に停止できる。
    - 実行時の PID ファイル出力に対応（data/execution.pid）。
  - 監視ループ起動スクリプト（run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する旨の設計（監視データは本番 DB に集約）。
    - SystemMonitor.check_once() を定期実行し、例外はログに記録して次ループへ継続。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。

- 設定管理と初期化ツール
  - Settings クラスによる環境変数ラッパー（src/kabusys/config.py）
    - .env / .env.local を自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 複雑な .env パース処理（export プレフィックス、クォート内のエスケープ、インラインコメント処理など）を実装。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / PID / Kill フラグ / しきい値 / 環境種別チェック 等）。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path の分離等に対応。
  - 環境設定ウィザード CLI（config_setup.py）
    - 対話式で .env を作成・更新するウィザードを提供。シークレットはマスク表示、デフォルト値・選択肢対応。
    - .env ファイル読み込み/書き込み機能を提供（テンプレートヘッダ付き）。
  - 設定検証 CLI（validate_config.py）
    - 必須環境変数の存在確認、KABUSYS_ENV の妥当性チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および（PyYAML が有効なら）パース検証を実施。
    - KABUSYS_ENV=live 時の追加安全チェック（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険設定など）。
    - --strict オプションにより警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ（setup_logging）（src/kabusys/utils/logging_setup.py）
    - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決とログディレクトリ自動作成。失敗時のフォールバック動作あり。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/macOS を吸収してプロセス niceness / priority を設定（"high"/"normal"/"low"）。
    - CPU アフィニティを設定する set_cpu_affinity を提供。権限不足等は警告を出してスキップ。

- ポートフォリオ構築モジュール（純粋関数群、DB 参照なし）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア順で上位 N 件選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、全スコアが 0 の場合はフォールバックで等配分）
  - セクターキャップ・レジーム補正（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有セクターの割合が閾値を超える場合、同セクターの新規候補を除外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に応じた投下資金乗数、未知レジームは警告して 1.0 にフォールバック）
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - allocation_method = "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、max_position_pct/max_utilization による上限、cost_buffer を考慮した aggregate cap のスケーリング処理を実装。
    - スケーリング時は端数を優先順位順に lot 単位で追加配分するロジックを備える。

- Paper Trading 関連ツール
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から集計してレポート出力。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等の指標を計算し PASS/FAIL 判定を行う。
    - P95 計算、期間フィルタ、SQL クエリの堅牢化（テーブル非存在時の例外回避）を実装。閾値は定数で定義。

- 研究用ファクター計算基盤（初期実装）
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）
    - Momentum / MA / ATR / Volume 指標の計算を目標とする設計。DuckDB 接続を受け SQL と Python で処理する設計方針。
    - calc_momentum 関数（モメンタム関連の計算）などの骨格と定数を実装（実装途中ファイルあり、今後拡張予定）。

- 監視用 DB 初期化（モジュール参照）
  - init_monitoring_db（監視テーブルの初期化）を参照して監視・実行スクリプトから冪等に呼び出すことでテーブル存在を保証。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Deprecated
- 該当なし。

### Removed
- 該当なし。

### Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に保存する設計。config_setup で生成する .env は Git にコミットしない旨を明記。

### Notes / Known issues / TODO
- src/kabusys/research/factor_research.py は現状で calc_momentum の実装が途中で終わる箇所（ファイル末尾で途中）があります。研究用ファクター計算は今後の拡張対象です。
- position_sizing や apply_sector_cap のコメント中にフォールバック価格や銘柄別 lot_size 導入の TODO が存在します（将来的な拡張点）。
- run_monitoring はドキュメントどおり「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」するため、テスト/開発環境でのデータ分離が必要な場合は運用上の注意が必要です。
- process_priority / set_cpu_affinity は権限やプラットフォームの差異により動作が制限される場合があり、その際はログ警告でスキップする設計です。

---

開発・運用に関する追加の記載やリリースノートの調整が必要であれば、対象箇所（ファイル・機能・期待する振る舞い）を指定してください。
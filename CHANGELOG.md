# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。重要な変更点・追加機能をコードベースから推測して日本語でまとめました。

## [0.1.0] - 2026-04-19
初回公開リリース（コードベースのスナップショットに基づく）。以下の主要機能・改善を含みます。

### Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じてペーパートレード用 DB を分離（data/paper_trading.db を使用）、BrokerClientFactory に基づき MockBrokerClient を利用可能にする。実行中は実行 PID（data/execution.pid）を書き込む。停止フラグ（data/stop_requested.flag）で安全に停止可能。
  - run_monitoring.py: SystemMonitor をポーリングで定期実行する監視スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用し、停止フラグで終了する。

- 設定管理・支援ツール
  - config.py: Settings クラスを実装。環境変数をラップして提供（J-Quants / kabu API / DB パス /監視閾値 /環境判定等）。KABUSYS_ENV / LOG_LEVEL 等の検証を実施し、不正な値は ValueError により検出。
  - config_setup.py: .env の対話式ウィザードを追加。対話で .env を作成・更新できるテンプレート生成機能を備える（J-Quants、kabu API、DB パス、ログレベル、Kill Switch 設定など）。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数の検出、KABUSYS_ENV の妥当性チェック、DB パスや config/*.yaml の存在・パース検証（PyYAML が無ければ警告）など。--strict モードで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定関数 setup_logging を追加。stdout 用の StreamHandler と日次ローテート（TimedRotatingFileHandler）を設定。LOG_DIR / LOG_LEVEL による設定、ファイルハンドラ失敗時はコンソール出力にフォールバック。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows / POSIX 差分を吸収し、set_process_priority("high"|"normal"|"low") と set_cpu_affinity() を提供。psutil を使用し、権限不足等は警告でスキップ。

- ポートフォリオ構築・リスク制御
  - portfolio/portfolio_builder.py: 候補選定関数 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を追加。スコア全て 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中度チェック apply_sector_cap、マーケットレジームに基づく投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマップと未知レジームのログ警告）。
  - portfolio/position_sizing.py: 発注株数計算 calc_position_sizes を追加。allocation_method として "risk_based", "equal", "score" をサポートし、単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超えるとスケーリング）や残差分配ロジックを実装。コストバッファ（slippage/commission 見積り）を考慮。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均／最大／P95）を集計し、しきい値（稼働率 99%、成功率 90%、送信率 95%、P95 200 ms）で PASS/FAIL 判定を出力。日付フィルタ、DB パス指定オプションあり。

- 研究用モジュール（着手）
  - research/factor_research.py: ファクター計算基盤を追加（Momentum/Value/Volatility/Liquidity 設計）。DuckDB 接続を用いて prices_daily や raw_financials を参照する設計。モメンタム計算関数 calc_momentum の実装開始（長期移動平均や各ホライゾンのリターン計算の定義あり）。※ファイル末尾で実装が途中で切れている（未完成の可能性あり）。

- パッケージ情報
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を設定。

### Changed
- 環境変数自動ロードの改善（config.py）
  - プロジェクトルート探索: .git または pyproject.toml を基準として自動検出。__file__ を起点に親ディレクトリを探索するため、CWD に依存しない自動ロード設計。
  - .env パーサの強化: export プレフィックスに対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート、クォート無しの値ではインラインコメントの取り扱い（' #' の直前が空白/タブの場合にコメント扱い）を実装。既存 OS 環境変数保護のため protected 引数を使った上書き制御を追加。
  - 自動ロード抑制: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途を想定）。

- DB/監視に関する挙動
  - run_monitoring: 監視は KABUSYS_ENV に関わらず設定された sqlite_path（デフォルト data/monitoring.db）を使用するよう明示。
  - run_execution: paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番データと分離する。

- ログ出力ポリシー
  - logging_setup は既存ハンドラを一旦 flush/close してから削除し、二重登録を防止。StreamHandler は stdout を使用（cron 等で stdout/stderr を一本化する運用を考慮）。

### Fixed
- ポーリング間隔の安全化（run_monitoring.py）
  - MONITOR_POLL_INTERVAL に不正値が与えられた場合にデフォルト（60 秒）にフォールバックし、time.sleep に渡す 0 以下や非整数値による例外を避けるためのバリデーションを追加。

- ロギングディレクトリ作成失敗時のフォールバック（logging_setup.py）
  - ディレクトリ作成に失敗した際はファイルハンドラを作成せず StreamHandler のみで継続し、標準エラー出力に警告を出すように修正。

- process_priority の権限エラー処理（utils/process_priority.py）
  - psutil の権限不足や未実装メソッドに対して警告を出して安全にスキップするように改善。

### Deprecated
- なし（初回リリース相当のため該当なし）

### Removed
- なし（初回リリース相当のため該当なし）

### Security
- 環境変数の取扱い:
  - .env の自動ロード時に既存 OS 環境変数を保護する仕組みを導入（protected set）。機密値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は設定ウィザードで secret 扱いでマスク表示。

---

補足・注意事項:
- research/factor_research.py はファイル末尾が途中で切れているように見え、実装完了が必要です（calc_momentum の続きなど）。
- 実運用では .env を絶対に Git にコミットしない運用指針が設定ウィザードのコメントにも明記されています。
- 実行スクリプトは停止フラグ（data/stop_requested.flag）や PID ファイルで外部からの停止監視・管理を想定しています。
- Paper Trading と Live を完全に分離する工夫（専用 SQLite、MockBroker の使用）は安全性の観点で意図的に設計されています。

この CHANGELOG はコードベースの内容から推測して作成しています。必要であれば項目の補足や日付・バージョンの調整を行います。
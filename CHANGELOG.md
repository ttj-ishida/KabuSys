CHANGELOG
=========

フォーマットは "Keep a Changelog" に準拠しています。
※ 日付はリリース時の想定日を付与しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 初回公開リリースを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。起動時にプロセス優先度を "high" に設定し、PID ファイル / stop フラグを扱う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag による検出で行う。
- 設定関連
  - config.py: 環境設定読み込み機能を実装。プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動読み込み（.env、.env.local の優先度や OS 環境変数保護を考慮）。多くの設定プロパティ（DB パス、PID/kill フラグ、閾値、PAPER_FILL_MODE の検証など）を公開する Settings クラスを追加。
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。既存値の再利用、シークレット扱い、.env テンプレート書き出し機能を提供（.env を Git にコミットしない旨の注記あり）。
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、PyYAML がある場合は YAML のパース検証、KABUSYS_ENV=live に対する追加ガードを実装。--strict フラグで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と等分・スコア重み（calc_equal_weights / calc_score_weights）を実装。スコアが全て 0 の場合のフォールバックロジックもある。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジーム時はフォールバックと警告を出す。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method に応じた株数計算（risk_based / equal / score）、単元株（lot_size）丸め、単銘柄上限・aggregate cap、cost_buffer を考慮したスケールダウンアルゴリズム（端数の分配を再現性を保って処理）を提供。
  - portfolio/__init__.py: 上記関数をエクスポート。
- 監視・モニタリング
  - monitoring DB 初期化呼び出し（init_monitoring_db）を run_monitoring/run_execution 起動時に実行し、監視用テーブルの存在を保証（冪等）。
  - Settings に監視閾値設定（cpu/memory/disk）を追加。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一セットアップを実装。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）を設定。ログディレクトリ作成失敗時のフォールバック動作を定義。
  - utils/process_priority.py: psutil を用いたクロスプラットフォームなプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定ユーティリティを実装。設定失敗時は警告を出してスキップする耐障害性あり。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。期間指定（--from / --to）や DB パス指定（--db / 環境変数）に対応。システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）などを算出し、閾値比較で PASS/FAIL を判定する。P95 算出ロジック、N/A 表示を備える。
- リサーチ
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム・MA200・ATR 等の定義／設計方針）。（実装途中の関数あり）
- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- なし（初回リリースのため変更履歴なし）。

Fixed
- 環境変数パースの堅牢化（config._parse_env_line）
  - export プレフィックスに対応
  - シングル/ダブルクォート内でのバックスラッシュエスケープ処理対応
  - クォートなしでのインラインコメント処理をスペース/タブの直前のみコメントとみなす仕様により誤削除を回避
- MONITOR_POLL_INTERVAL の不正値（0 以下・非数）に対する警告とデフォルトフォールバック処理を追加（run_monitoring._get_poll_interval）。

Security
- .env ファイルに関して config_setup に WARNING コメントを追記（.env を絶対に Git にコミットしないことを明示）。
- config._load_env_file は既存 OS 環境変数を保護する（protected 引数）ことでテスト/実行環境の意図しない上書きを防止。

Notes
- paper_trading と live の DB は分離される設計（Settings.paper_sqlite_path / sqlite_path を使い分け）。
- run_execution は BrokerClientFactory 等の外部コンポーネントに依存しており、paper_trading モードでは MockBrokerClient（想定）を使用して本番 DB と完全分離する運用を意図しています。
- research/factor_research.py は計算定義やスキャン幅など設計方針を実装済みだが、関数内部が途中で切れている箇所（このリリースでは骨子の追加にとどまる場所）があるため、今後の完成を予定しています。

---

この CHANGELOG はソースの内容から推測して作成しています。実際の変更履歴（コミットログ）と差異がある場合は、適宜調整してください。
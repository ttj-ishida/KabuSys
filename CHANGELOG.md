# Changelog

すべての重要な変更は Keep a Changelog に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-19
初回リリース。自動売買システム「KabuSys」の基盤機能群を追加。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。

  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite (data/paper_trading.db, 環境変数で上書き可) を使用して本番 DB と完全分離。MockBrokerClient を利用する設計に合わせたブローカーファクトリ連携を想定。
    - 停止フラグ検出でエンジン停止/起動中止を行う安全機構を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env の自動読み込み機能をプロジェクトルート (.git または pyproject.toml を基準) から実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - .env パースの堅牢化（export プレフィックス、クォート内エスケープ、コメントルールの考慮）。
    - Settings クラスを実装。主要な環境変数の取得、デフォルト値、妥当性チェック（KABUSYS_ENV / LOG_LEVEL など）、paper_trading 用 DB パス、paper_fill_mode の検証などを提供。
    - settings = Settings() をモジュールレベルで提供。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 入力補助、シークレットマスク、既存 .env の読み込み・再利用、保存プレビュー機能を実装。

  - validate_config.py
    - 起動前に .env および config/*.yaml の整合性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML 未導入時はスキップ）、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告をエラー扱いにするモードを提供。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
    - 既存ハンドラのクリーンな再設定処理を実装。

  - utils/process_priority.py
    - psutil を使ったクロスプラットフォームのプロセス優先度設定を追加（"high" / "normal" / "low"）。
    - Windows と POSIX (Linux/Mac/FreeBSD) の差分を吸収。アクセス権限による失敗時は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity() を追加（未指定時は変更しない）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補を抽出し最大ポジション数でトリミング。
    - calc_equal_weights: 等配分重みを計算。
    - calc_score_weights: スコアに応じた重みを計算（全スコアが 0 の場合は等配分にフォールバックし警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づき候補をフィルタ（"unknown" セクターは制約対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投資乗数を返す。未知レジームはログ警告を出しフォールバック 1.0。

  - portfolio/position_sizing.py
    - calc_position_sizes: weight / equal / score / risk_based に基づく株数計算を実装。
    - lot_size 単位で丸め、per-position 上限・aggregate cap を考慮してスケーリング、cost_buffer による保守的なコスト見積り、残差分の再配分ロジックを実装。
    - 価格欠損時のスキップやデバッグログを含む堅牢な動作。

  - portfolio/__init__.py
    - 上記関数群をエクスポート。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト: data/paper_trading.db）から統計を集計して検証レポートを出力する CLI を追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）などを算出。
    - Pass/Fail 判定基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を実装。
    - 日付フィルタ (--from / --to)、--db オプションで DB パス指定可能。
    - P95 の算出ロジック、データ不足時の N/A 表示などをサポート。

- 研究用モジュール（計画・実装途中）
  - research/factor_research.py
    - ファクター（Momentum、Value、Volatility、Liquidity）設計の枠組みを実装。
    - DuckDB 接続を受け prices_daily / raw_financials から計算する方針と関数インターフェース（例: calc_momentum）を導入（モジュール内に詳細実装の続きあり）。

- パッケージメタ
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため過去変更なし）

### Fixed
- （初回リリースのため過去修正なし）

### Notes / 補足
- 実行スクリプトは起動直後にプロセス優先度を "high" に設定する設計。ただし環境により権限不足で失敗するケースがあり、その場合は警告ログを出して続行します。
- run_monitoring は監視用 DB テーブルの初期化（init_monitoring_db）を行うため、監視用テーブルが必ず存在することを想定しています（冪等）。
- run_execution は Engine を別スレッドで実行し、停止フラグ検出でエンジン.stop() を呼ぶ仕組みです。PID ファイル管理、停止フラグ（data/stop_requested.flag）、kill フラグ関連の設定を想定。
- .env の自動読み込みはプロジェクトルートの検出に基づくため、パッケージ配布後や CWD が異なる環境でも安定して動作するように設計されています。自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 一部モジュール（ExecutionEngine、BrokerClientFactory、SystemMonitor 等）はこのスナップショットでは参照のみ（別ファイル実装を想定）です。

---

今後の変更提案（例）
- factor_research の完全実装（全ファクターの算出と単体テスト）。
- ExecutionEngine / BrokerClient 実装の充実、モックのテストサポート強化。
- 単体テスト・統合テスト用のテストデータ生成スクリプト、CI ワークフローの追加。
- 設定・シークレット管理の改善（Vault 等の統合検討）。
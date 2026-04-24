# Changelog

すべての重要な変更点を記録します。形式は "Keep a Changelog" に準拠し、バージョンとカテゴリ（Added / Changed / Fixed / Deprecated / Removed / Security）で整理しています。

なお、この CHANGELOG はリポジトリ内のコードからの推測に基づいて作成しています。実際のリリース履歴と差異がある可能性があります。

## [Unreleased]

- 今後のリリースに向けた一般的な TODO / 改善候補:
  - stocks マスタに銘柄ごとの lot_size を持たせ、position_sizing の lot_size を銘柄別に対応する拡張。
  - apply_sector_cap の価格欠損時のフォールバック（前日終値や取得原価など）を導入してエクスポージャー評価の精度を向上。
  - research.factor_research の計算ロジック（ファイル末尾が途中で切れている）を完成させる。
  - より詳細なユニットテストと CI の整備（現コード中に多くのファイル I/O / DB 接続が直接含まれるため、モック対応の強化が望まれる）。

---

## [0.1.0] - 2026-04-24

初回公開リリース。日本株自動売買システム "KabuSys" のコア機能を提供する一式を追加。

### Added
- 基本メタ情報
  - パッケージバージョンを定義: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト / ランタイム
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用する仕組みを追加。paper_trading 環境では MockBrokerClient を使用可能（BrokerClientFactory により抽象化）。
    - プロセス優先度を "high" に設定（utils.process_priority を利用）。
    - PID ファイル・停止フラグ（data/execution.pid / data/stop_requested.flag）による起動制御および安全停止処理を実装。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検知で安全に停止させるループを提供。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境に関わらず本番 sqlite_path を使用する設計。停止フラグ（data/stop_requested.flag）でループ終了。
    - check_once() 実行中の例外を捕捉してログに残し、次ポーリングへ継続する堅牢性を確保。

- 設定関連
  - config.py
    - .env 自動ロード機構（.env, .env.local）を実装。プロジェクトルート検出（.git または pyproject.toml）に基づくため CWD に依存しない。
    - クォートあり/なしの .env パースを強化（エスケープ、インラインコメント対応）。
    - 環境変数の getter を集約した Settings クラスを提供（J-Quants / kabuAPI / DB パス / Paper 設定 / 監視閾値など）。
    - KABUSYS_ENV や LOG_LEVEL の検証、PAPER_FILL_MODE の妥当性チェックなどを実装。
    - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用途）。
  - config_setup.py
    - 対話式 .env 作成ウィザードを実装。既存値を読み取りつつ新規作成や更新が可能。
    - 入力補助（選択肢・デフォルト・シークレットマスク）と保存前の確認を提供。
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、ファイルパスの親ディレクトリ存在確認、YAML パースの試行（PyYAML がある場合）を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定 select_candidates: スコア降順・同点は signal_rank でブレーク。
    - 配分計算: calc_equal_weights（等分配）、calc_score_weights（スコア正規化／全スコア0時は等分配にフォールバック）。
  - portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap: 既存保有比率に基づき同一セクターの新規候補を除外。
    - レジーム乗数 calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数（フォールバックあり）。
  - portfolio.position_sizing
    - calc_position_sizes: weight / score / risk_based の各方式に対応した発注株数計算、単元（lot_size）丸め、最大上限・aggregate cap スケーリング、cost_buffer を用いた保守的見積りを実装。
    - aggregate cap 超過時のスケールダウンと端数配分ロジックを実装。

- データ解析 / リサーチ
  - research.factor_research
    - Momentum / Value / Volatility / Liquidity のファクター計算モジュールを設計・実装（DuckDB を利用）。（注: ファイル末尾が途中で切れている箇所あり。基本設計と一部実装を含む。）

- ユーティリティ
  - utils.logging_setup
    - 統一的なログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority
    - プロセス優先度（nice / Windows priority class）および CPU affinity 設定ユーティリティを実装。psutil を利用し、未対応 OS やアクセス権限不足時には警告ログを出して安全にスキップ。

- モニタリング DB 初期化
  - monitoring.monitoring_db の init_monitoring_db を run_* スクリプトから呼び出し、監視用テーブルが必ず存在することを保証（冪等性）。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を追加。
    - システム稼働率、注文成功率、送信率、API レイテンシ（avg/max/P95）、リスク却下数などを集計し PASS/FAIL を判定する基準を実装。
    - 日付フィルタ（--from / --to）や DB パス指定（--db / 環境変数）に対応。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 複数箇所で堅牢性を強化:
  - .env パーサーでクォートやエスケープ、インラインコメントを正しく扱うようにして誤読を低減。
  - logging_setup: ログディレクトリ作成失敗時もアプリケーションが続行するようにして起動失敗のリスクを軽減。
  - run_monitoring / run_execution: 停止フラグ / KeyboardInterrupt のハンドリングを強化し、DB コネクションを確実にクローズするようにした。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の取り扱い注意:
  - .env は Git にコミットしない旨のヘッダを config_setup が出力するなど、秘密情報の流出防止に関するドキュメント上の配慮あり。
  - SECRET な設定項目はウィザードでマスク表示。

---

## 既知の制限 / 注意点
- research.factor_research の実装がファイル上で途中までの状態（切れている）であり、完全な計算フローは未実装の箇所がある可能性があります。実運用に投入する前に該当モジュールを確認してください。
- apply_sector_cap は price_map に価格が欠損（0.0）した場合、現状ではその銘柄を無視する実装のため、エクスポージャーの過少見積りを招く恐れがあります。コメント内に TODO があり、将来的なフォールバック価格対応が予定されています。
- 単元株（lot_size）は現状グローバル設定（デフォルト 100）として扱われています。将来的な銘柄別単元対応が望ましい旨の注記あり。
- process_priority / set_cpu_affinity は OS と権限に依存するため、無効化や警告でスキップされることがあります（アクセス権限不足等）。

---

よく使うコマンド（参考）
- .env の対話的生成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

（以上）
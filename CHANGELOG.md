# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
セマンティックバージョニングを採用します。  

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-19

初回リリース。自動売買システム KabuSys の基盤機能を実装しました。主な追加点は以下のとおりです。

### 追加（Added）
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止制御にプロジェクト直下の `data/stop_requested.flag` を使用。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して起動。
    - 例外発生時はログ出力し、次のポーリングに備えて継続する堅牢なループ実装。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient（BrokerClientFactory 経由）を使用し、`data/paper_trading.db` に記録（本番 DB と分離）。
    - 停止フラグと PID ファイル管理（`data/execution.pid`）に対応。スレッドでエンジンをデーモン起動し、停止フラグ検知で安全停止。

- 設定関連
  - config.py
    - 環境変数の自動ロード機能を実装（.env / .env.local）。プロジェクトルートを .git / pyproject.toml から探索。
    - `.env` の行パーサを実装（export 形式、クォート、インラインコメント対応）。
    - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得可能に（J-Quants / kabu API / DB パス / paper トレード設定 / 監視閾値 / ログレベル 等）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
    - `paper_fill_mode` の入力検証（instant/partial/never/reject）。
    - `env` の検証（development/paper_trading/live）やログレベル検証を実装。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。既存値の読み込み・マスク表示・選択肢サポートあり。
    - 書き込み時にテンプレートヘッダを付与し、Git にコミットしない旨を注記。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の検証、DB パス・ディレクトリの存在検査、YAML パース確認（PyYAML がある場合）。
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全てが 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存ポジションを基にセクターエクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装。allocation_method は `risk_based` / `equal` / `score` をサポート。
    - lot_size（単元株）丸め、per-stock 上限・aggregate キャップ適用、cost_buffer を用いた保守的なコスト見積り。キャッシュ超過時のスケーリングおよび端数処理アルゴリズムを実装。
    - 将来的な拡張箇所（銘柄ごとの lot サイズ対応など）に関する TODO コメントあり。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定。
    - ログレベルとログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時にファイルハンドラをスキップする安全処理。
  - utils/process_priority.py
    - プラットフォーム横断のプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。psutil を使用し、Windows / POSIX をハンドリング。アクセス権限や未対応 OS に対するワーニング処理を実装。
  - utils/__init__.py を追加。

- 監視・モニタリング
  - run_monitoring/run_execution で monitoring_db 初期化（init_monitoring_db）を呼び出すことで監視テーブルの存在を保証（冪等）。
  - SystemMonitor を用いた一時的なチェック実行（monitor.check_once）。

- ツール / レポート
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定する機能を実装。
    - デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms。
    - 日付フィルタ、DB パス指定オプション（コマンドライン / 環境変数）あり。
    - 空データや sqlite テーブル未存在時の安全なフォールバック処理を追加。

- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB 接続を使ったファクター計算モジュールを追加。モメンタム（1M/3M/6M / MA200 乖離）や ATR / ボリューム等のための定数・関数群の骨組みを実装（prices_daily / raw_financials テーブルを想定）。
    - 設計上、SQL + Python で完結し本番 API にアクセスしない点を明示。

- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。
  - portfolio パッケージの __all__ エクスポートを設定。

### 変更（Changed）
- 起動/運用上の安全対策
  - MONITOR_POLL_INTERVAL 等の不正値に対しデフォルトへフォールバックし警告を出す実装を追加（run_monitoring）。
  - logging_setup がログディレクトリ作成失敗を許容し、コンソール出力のみで継続するよう改善。
  - process_priority/set_cpu_affinity が権限不足や未対応環境をワーニングでスキップするように安定化。

### 修正（Fixed）
- エラー処理の強化
  - 実行ループ内での例外をログに残し、ループの継続を保証（monitor.check_once 呼び出し時）。
  - validate_config の YAML パース時に PyYAML 未インストールなら警告しパース検証をスキップするように変更。

### 既知の制限 / TODO
- portfolio.position_sizing の lot_size は現状全銘柄共通。将来的に銘柄別 lot サイズマップを受け取る設計に拡張予定（TODOコメントあり）。
- apply_sector_cap では price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、前日終値や取得原価を使ったフォールバックの検討が必要（TODOコメント）。
- research/factor_research はモメンタム計算の骨格が実装されているが、他ファクター（Value/Volatility/Liquidity）の完全実装やテストが今後必要。
- 実際のブローカー連携や発注ロジックはモック/Factory 経由で抽象化されているため、本番接続前に BrokerClient の実装と十分なテストが必要。

---

今後のリリースでは、戦略生成/シグナルパイプライン、取引実行テスト、さらなる監視・アラート強化、バックテスト・リサーチワークフローの拡張を予定しています。
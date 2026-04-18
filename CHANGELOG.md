# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

※ 初期リリース: 0.1.0（本リポジトリに含まれる機能をコードから推測してまとめています）

## [Unreleased]

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 全体
  - 初期リリース。自動売買システム KabuSys のコアユーティリティ、実行/監視ランナー、設定管理、ポートフォリオ構築ロジック、検証ツール等を追加。

- 起動スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag により検知。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して接続（monitoring 用テーブルを初期化）。
    - duckdb も併用している。
  - run_execution.py を追加。ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用（Mock）ブローカ/DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - プロセス優先度を "high" に設定。
    - BrokerClientFactory によるブローカ生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てを行い、デーモンスレッドで実行。
    - 停止は data/stop_requested.flag（存在時は起動しない、実行中は engine.stop() で停止）。

- 設定管理 / CLI
  - config.py を追加。Settings クラスにより環境変数を扱うユーティリティを提供。
    - .env/.env.local の自動読み込み（プロジェクトルート検出）機能を備え、既存 OS 環境変数の保護や override の挙動を実装。
    - 複雑な .env 行のパースに対応（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント規約など）。
    - 各種設定（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID ファイルパス 等）や検証付きプロパティ（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を提供。
  - config_setup.py を追加。対話式 .env ウィザード
    - 初期 .env の生成・更新をサポート。シークレットマスキングと選択肢/デフォルトを提供し .env ファイルを書き出す。
  - validate_config.py を追加。設定検証 CLI
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合は）パース検証を実行。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番環境向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の警告など）。

- ポートフォリオ構築ロジック（メモリ内純粋関数）
  - portfolio.portfolio_builder
    - select_candidates(): スコア降順で上位 N を選定（signal_rank によるタイブレーク）。
    - calc_equal_weights(), calc_score_weights(): 等金額・スコア加重の重み計算（全スコアが 0 の場合は等分配にフォールバックし警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap(): セクターごとの既存エクスポージャーが上限を越える場合、新規候補を除外（sell_codes を除外して計算可能、"unknown" セクターは無視）。
    - calc_regime_multiplier(): 市場レジームに応じた投入率乗数（bull/neutral/bear -> 1.0/0.7/0.3）。未知レジームは警告して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes(): allocation_method に応じた発注株数計算（risk_based, equal, score）。
      - lot_size（単元株）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジックを実装。

- ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - 既存ハンドラの重複設定を回避するため一度クリアしてから設定。
    - LOG_DIR の作成失敗時にファイルハンドラをスキップして標準出力のみで継続。
  - utils.process_priority: クロスプラットフォームでプロセス優先度（nice / Windows priority）と CPU affinity を設定するユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）の差異を吸収しつつ失敗時に警告してスキップする実装。

- ツール
  - tools.paper_verification_report.py を追加。ペーパートレード検証レポート生成スクリプト。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB を読み込み、システム稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - いくつかの閾値（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を行う。

- リサーチ
  - research.factor_research.py を追加（ファクター計算モジュールの骨格）。
    - Momentum / Value / Volatility / Liquidity 等の計算方針がコメントで定義され、DuckDB を用いた計算インターフェースを想定。calc_momentum の開始実装を含む（ファイル末尾は途中で切れている）。

### 変更 (Changed)
- ロギング
  - StreamHandler を stderr ではなく stdout に出力するように変更（cron/task scheduler からのログリダイレクトを考慮）。
  - ログディレクトリ作成失敗時はファイル出力を無効化し、コンソール出力のみ継続するフォールバックを導入。
- 実行周りの挙動
  - run_monitoring: MONITOR_POLL_INTERVAL の無効値（0 以下や数値でない）に対して警告を出しデフォルト値にフォールバック。
  - run_execution: paper_trading 環境時は paper_sqlite_path を使用して本番 DB と分離。ExecutionEngine 起動前に stop flag をチェックして起動抑止する安全措置を追加。

### 修正 (Fixed)
- .env 読み込みロジックの堅牢化
  - export プレフィックスやクォート内のエスケープ処理、インラインコメントの扱いなど、実運用で見られる .env 書式の多様性に対応。
  - 自動ロードはプロジェクトルートが特定できない場合（.git や pyproject.toml が見つからない場合）や KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されている場合にスキップするようにしてテスト時の衝突を回避。

### 注意事項 (Notes)
- run_monitoring は環境（KABUSYS_ENV）にかかわらず production 相当の sqlite_path を使用します。開発・テスト時にデータ分離が必要な場合は設計に注意してください。
- PAPER_TRADING_SQLITE_PATH を用いることでペーパートレードの記録は本番 DB と分離できます（run_execution がその分離を尊重します）。
- research.factor_research.py は一部実装が途中で切れている箇所があるため、完全実装は今後の作業が必要です。
- process_priority と CPU affinity の設定は権限やプラットフォーム依存で失敗する場合があります（失敗時は警告を出してスキップします）。
- config_setup によって生成された .env ファイルは絶対に Git にコミットしないでください（secret を含むため）。

### セキュリティ (Security)
- 現時点でセキュリティアラートは特に報告されていませんが、.env（シークレット）管理には十分な注意を払ってください。

---

この CHANGELOG はコードから推測して作成しています。実際の変更履歴やバージョン付け方針に合わせて適宜編集してください。
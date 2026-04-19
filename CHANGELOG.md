# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 基本パッケージ初期リリース:
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト / 実行系:
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト `data/paper_trading.db`）を使用する設計。ペーパートレードと本番 DB を分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御: プロジェクトルート下の `data/stop_requested.flag` を用いた外部停止フラグ検出。実行中は `_EXECUTION_PID` に PID ファイルを書き込む想定。
    - デフォルトでプロセス優先度を "high" に設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用エントリポイント。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（デフォルト `data/monitoring.db`）を使用。
    - 停止フラグ検出によりループを終了（`data/stop_requested.flag`）。
    - データベース初期化: init_monitoring_db を呼び出して監視テーブルの整備を保証。

- 設定関連ツール:
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - 優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 各種設定プロパティを提供（DB パス、PID パス、Kill Switch 設定、しきい値、環境種別判定等）。
    - PAPER_FILL_MODE（ペーパートレードの約定モード）や PAPER_TRADING_SQLITE_PATH をサポート。PAPER_FILL_MODE の妥当性チェックを実装。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI。
    - 必須項目（J-Quants トークン、kabu API パスワード等）や推奨デフォルトを提供。
    - シークレット項目はマスク表示。生成される .env ファイルには注意書きが付与される。

  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在確認を実装。
    - PyYAML 未導入時は YAML 検証をスキップする旨の警告を出す。
    - `--strict` オプションで警告を失敗として扱うモードを提供。

- 監視・レポート:
  - tools/paper_verification_report.py
    - ペーパートレード結果検証レポート生成スクリプトを追加。
    - DB（デフォルト `data/paper_trading.db`）から以下指標を集計してレポート出力:
      - 稼働率 (uptime_pct)、ポーリング数、エラー数
      - 注文成功率（Filled / Created）、送信率（Sent / Created）
      - リスク却下数（risk_logs）
      - レイテンシ (avg / max / P95)
    - 基準値（例: 稼働率 >= 99%、P95 <= 200 ms）を定義し PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。

- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み (calc_score_weights) を提供。
    - スコア全0 の場合は等配分にフォールバック。

  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) による候補除外機能。
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を提供（bull/neutral/bear をマップ）。
    - 未知レジームはログ警告の上フォールバックで 1.0 を返す。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算を実装（allocation_method: "risk_based"/"equal"/"score"）。
    - 単元株丸め（lot_size、デフォルト 100）、per-position 上限、aggregate cap（利用可能現金に応じたスケーリング）を考慮。
    - cost_buffer（手数料・スリッページの見積り）を加味して保守的に計算。

  - portfolio/__init__.py にて上記関数群を公開。

- ユーティリティ:
  - utils/logging_setup.py
    - 標準化されたロギング設定ユーティリティを提供。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト `logs/<app_name>.log`、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル解決（引数 > 環境変数 > デフォルト）。

  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / Windows priority class）を設定するユーティリティ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供（実行環境に依存して失敗する場合は警告でスキップ）。
    - アクセス権限が不足する場合は警告で無視する設計。

- 研究用モジュール（下流分析用）:
  - research/factor_research.py（設計と一部実装を含む）
    - DuckDB の prices_daily / raw_financials を用いたファクター計算フレームワーク（Momentum, Value, Volatility, Liquidity を想定）。
    - calc_momentum を含むモジュール骨格を提供（DuckDB 接続を受け、(date, code) 単位の dict リストを返す設計）。

### 変更 (Changed)
- 初版リリースのため履歴なし（初回公開）。

### 修正 (Fixed)
- 初版リリースのため履歴なし（初回公開）。

### 既知の制限・注意点 (Known issues / Notes)
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価などへのフェールバックが必要（TODO を注記）。
  - 単元株サイズは現状グローバルな lot_size を想定。将来的に銘柄別 lot_map へ拡張予定。

- risk_adjustment.apply_sector_cap:
  - "unknown" セクターはセクター上限適用対象外（意図的な挙動）。運用ルールに応じて変更検討が必要。

- research/factor_research.py:
  - ファイル内部に計算ロジックの続き（calc_momentum の実装途中）があるため、完全な生産利用には追加実装が必要（現状は設計段階〜部分実装）。

- validate_config.py:
  - PyYAML 未導入環境では YAML 検証をスキップするため、実際の YAML 構成ミスを検知できない可能性がある。CI 等で PyYAML を導入することを推奨。

- 一部ファイルは外部コンポーネント（ExecutionEngine, BrokerClient, SystemMonitor 等）に依存するため、これらの実装が必要。起動スクリプト単体では依存コンポーネントの具象実装が必要。

### セキュリティ / 運用上の注意
- .env ファイルは絶対にリポジトリにコミットしないことを README / ドキュメントで強調すること。
- 本番環境 (KABUSYS_ENV=live) では `KILL_FLAG_CLEAR_ON_START` を `0` にしておくことを推奨（validate_config で警告を出す）。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" にしようとするため、権限のない環境では警告が出るがスキップする設計。

---

今後の予定（例）
- research モジュールの完全実装（各ファクターの SQL/集計ロジック完成）。
- stocks マスタを用いた銘柄別 lot_size サポート。
- モニタリング/アラートの LINE 通知連携（Settings にはトークン項目あり）。
- 詳細な単体テスト・統合テストの追加。

もし CHANGELOG に追記してほしい点（特にリリース日や追加で強調したい変更等）があれば教えてください。必要に応じて別バージョンのリリースノート案も作成します。
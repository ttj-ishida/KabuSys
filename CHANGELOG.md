# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 以下の内容はソースコードの実装内容から推測して作成したリリースノートです。

## Unreleased

- 特になし

---

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を提供します。主な追加項目は以下の通りです。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて paper_trading 用 DB（data/paper_trading.db）を使用する分離処理を実装。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - デーモンスレッドでエンジンを実行し、 data/stop_requested.flag による安全な停止をサポート。
    - 起動時に data/execution.pid を PID ファイルとして扱う。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は常に本番用の sqlite_path を使用する（環境に依らず同一監視 DB）。
    - data/stop_requested.flag による停止検知をサポート。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - 独自の .env パーサ（export 文・クォート・インラインコメント対応）。
    - Settings クラスを導入し、環境変数をプロパティとして一元管理。
    - 多数の設定プロパティを追加（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - デフォルトパス: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db。

- 設定ツール・検証
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目は入力時・確認表示でマスク表示。
    - 書き込みテンプレートを用意（コミット禁止の注意文含む）。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在確認（PyYAML があればパースも実施）。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップ。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定(set_process_priority)。
    - CPU affinity 設定関数 set_cpu_affinity を追加。
    - アクセス権限により設定に失敗しても警告を出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア順ソートと上位 N 抽出。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み計算（スコア全0 の場合のフォールバックロジック含む）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（既存保有時価を考慮して候補除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マッピング、未知レジームは警告と 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数のアロケーション方式（risk_based / equal / score）に対応した株数計算。
    - 単元株（lot_size）による丸め、per-position 上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer を使った保守的見積り、残余キャッシュを使った端数配分ロジックを実装。

- 解析・レポートツール
  - tools/paper_verification_report.py
    - ペーパートレード DB から稼働率・注文成功率・送信率・レイテンシ等を集計して検証レポートを生成。
    - CLI オプション: --from / --to / --db。
    - P95 計算、各種閾値（稼働率 99%/成功率 90%/送信率 95%/P95 latency 200ms）による PASS/FAIL 判定を実装。
    - DB が存在しない場合のユーザーフレンドリなエラーメッセージ。

- 研究用 / ファクター計算（基礎実装）
  - research/factor_research.py
    - モメンタム・MA200・ATR 等の計算を行うための骨組み（DuckDB 接続経由で prices_daily / raw_financials を参照する設計）。
    - 定数定義や calc_momentum のインターフェースを実装（calc_momentum 実装は続きあり）。

- パッケージ情報
  - __init__.py にてバージョン __version__ = "0.1.0" を設定。

### Changed
- n/a（初回リリースのため既存コードの変更履歴はありません）

### Fixed
- n/a（初回リリース）

### Deprecated
- n/a

### Removed
- n/a

### Security
- config_setup の出力テンプレートで .env を Git にコミットしないよう明示的に注意を追加。
- 対話式ウィザードでシークレット表示をマスク。

### Notes / 実装上の注意点（既知の制約）
- .env 自動読み込みはプロジェクトルートを検出できない場合はスキップされる（配布後の挙動を考慮）。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告を出してスキップする設計。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0 等）があるとエクスポージャーが過少評価され、除外ロジックが想定より緩くなる可能性がある旨を TODO コメントで明記。
- research/factor_research.calc_momentum はファイル末尾で実装途中（切れている箇所あり）。完全実装は今後のリリースで対応予定。

---

今後の予定（例）
- factor_research の完全実装およびユニットテスト追加
- ExecutionEngine / SystemMonitor の統合テスト・異常系ハンドリング強化
- per-stock lot_size を銘柄マスタで管理する拡張
- ログの構造化出力（JSON ログ）オプション追加

--- 

（終）
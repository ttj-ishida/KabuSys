# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」の書式に準拠します。

現行バージョン: 0.1.0

## [Unreleased]
- （現在のリポジトリ状態から推測すると、本リリースは初回公開に相当します。将来的な変更はここに追記してください。）

## [0.1.0] - 2026-04-18
初回リリース — KabuSys のコア機能群をまとめた最初の公開版。

### 追加 (Added)
- 全体
  - パッケージ基礎を提供（__version__ = 0.1.0）。
  - DuckDB/SQLite を用いたローカルデータ管理をサポート。

- 設定・環境
  - .env 自動読み込み機構を実装（.env / .env.local をプロジェクトルートから自動読み込み）。
  - 複雑な .env パースに対応（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションを追加。
  - Settings クラスで環境変数をプロパティとして一元管理（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 用設定等）。
  - .env を対話式に作成/更新する CLI ウィザードを追加（kabusys.config_setup）。
  - 設定検証 CLI を追加（kabusys.validate_config）。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在/パース検証（PyYAML がない場合はスキップ）。--strict オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト（run_execution）を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory を経由したブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）や PID ファイル処理・安全なシャットダウンに対応。
  - 監視ループ起動スクリプト（run_monitoring）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番用 sqlite_path を使用する設計（監視データの一貫性確保）。
    - 停止フラグ検知でループを終了、例外発生時はログ出力して次のポーリングへ継続。

- ロギング / プロセス制御
  - 統一的なログ初期化ユーティリティを追加（kabusys.utils.logging_setup.setup_logging）。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR による動的設定、ハンドラ二重設定の防止、ログディレクトリ作成に失敗した場合はファイル出力をスキップ。
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux/Mac/FreeBSD）に対応し、`set_process_priority("high"|"normal"|"low")` で優先度設定、`set_cpu_affinity(n)` で先頭 n コアにピン留め（利用不可時は警告ログでスキップ）。
    - 起動スクリプト（monitoring / execution）は起動直後に優先度を "high" に設定する。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み付け（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順で候補を選択（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等分にフォールバック）。
  - リスク調整（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: セクター集中上限チェックで候補を除外（sell予定銘柄は除外に含める）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知値は 1.0 にフォールバック）。
  - ポジションサイジング（kabusys.portfolio.position_sizing）
    - calc_position_sizes: risk_based / equal / score の割当方式に対応。単元株（lot_size）丸め、1銘柄上限・集計キャップ（available_cash）を考慮したスケーリング、手数料/スリッページ想定の cost_buffer を反映。スケールダウン時の端数再配分ロジックを実装。

- 研究用 / 補助ツール
  - ファクター計算モジュール（kabusys.research.factor_research）を追加。モメンタム・ボラティリティ等の計算を行う設計（DuckDB 接続を受け prices_daily / raw_financials を参照する想定）。
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）を追加。
    - 稼働率・注文成功率・送信率・API レイテンシ（P95）などを計算し PASS/FAIL 判定。--from/--to/--db オプションに対応。デフォルト DB は data/paper_trading.db。

- DB / 監視
  - 監視テーブル初期化ユーティリティ（monitoring.monitoring_db.init_monitoring_db）呼び出しで監視テーブルの存在を保証（冪等）。
  - duckdb 接続を併用して解析用途に対応。

### 変更 (Changed)
- 起動時の振る舞い
  - run_execution は paper_trading モードで専用 DB を使用することで本番 DB と完全分離するよう設計。
  - run_monitoring は常に本番の sqlite_path を参照する仕様に明示（監視データの一貫性優先）。

### 修正 (Fixed)
- N/A（初回リリースのため既知のバグ修正履歴はありません）

### 注意事項 / 既知の制限
- factor_research モジュールは設計が整っているものの、ソースの一部（calc_momentum の実装冒頭）が途中で切れているように見えます。実運用前に完全実装とテストが必要です。
- 一部の機能（ブローカークライアント実装、ExecutionEngine の詳細、monitoring_db のスキーマ等）はこの差分からは外部モジュールに依存しており、実行時にはそれらの実装が必要です。
- .env ファイルは機密情報（トークン・パスワード）を含みうるため、README に従い Git 管理下に置かないでください（config_setup でも明示）。
- process priority / cpu affinity の設定は権限不足やプラットフォーム非対応で失敗する可能性があり、その場合は警告ログを出して安全に無視されます。

### 互換性
- 初回リリースのため後方互換性の議論は対象外。将来の変更は semver に従って扱うことを推奨します。

---

出典: リポジトリ内のスクリプト・モジュール（run_execution.py, run_monitoring.py, config.py, config_setup.py, validate_config.py, utils/*, portfolio/*, research/*, tools/* 等）の実装内容から推測して作成しました。テキストはソースコードの実装・ドキュメント文字列に基づき要約しています。
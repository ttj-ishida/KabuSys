# Changelog

すべての変更は Keep a Changelog の形式に従い、日本語で記載しています。  

## [0.1.0] - 2026-04-23

初回公開リリース。日本株自動売買システム KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定関連ツール群、および検証ツールを含みます。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンドスレッド実行と停止フラグ（data/execution.pid / data/stop_requested.flag）対応。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用するようになっている（設計上の意図）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
- 設定・検証ツール
  - config_setup.py
    - 対話式 .env ウィザードを提供。.env の初期作成・更新を支援。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 等の設定項目をカバー。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ有無チェック、config/*.yaml の存在・パース検証（PyYAML が存在する場合）などを実行。`--strict` オプションで警告を fail 扱いにできる。
- 設定管理
  - config.py
    - 自動 .env 読み込み機構を導入（プロジェクトルートを .git / pyproject.toml から検出し、`.env` → `.env.local` の順で読み込む。OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - Settings クラスを導入し、環境変数のラッパー（トークン、API、DB パス、監視閾値、環境判定、paper_trading 用設定等）をプロパティとして提供。必須項目未設定時は明確なエラーを投げる。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）を実装。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。既存ハンドラはクリアして二重設定を防止。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力を無効化して継続。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定（Windows / POSIX に対応）を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。権限不足や未対応環境では警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率に基づき新規候補を除外）を実装。unknown セクターは制約対象外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマップ、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - position sizing の純粋関数 calc_position_sizes を実装。allocation_method（risk_based / equal / score）に対応し、lot_size（単元株）、max_position_pct、max_utilization、cost_buffer 等を考慮した株数算出と aggregate cap スケーリング処理を行う。端数処理では lot 単位での再配分ロジックを実装。
  - portfolio パッケージの __init__.py で上記関数群をエクスポート。
- DuckDB 統合
  - DuckDB 接続を扱うために各スクリプトで duckdb.connect を利用（duckdb_path は Settings.duckdb_path）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB を読み、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）等を集計してレポートを出力する CLI を追加。閾値に基づく PASS/FAIL 判定を出力。P95 の計算・期間フィルタ（--from/--to）対応。
- パッケージメタ情報
  - __init__.py に初期バージョン __version__ = "0.1.0" を設定。

### 変更 (Changed)
- ログ出力の標準ストリームを stderr ではなく stdout に統一（logging_setup）。cron 等で stdout/stderr を一本化してリダイレクトする運用を想定。

### 修正 (Fixed)
- ログハンドラの多重登録防止: setup_logging() が既存ハンドラを flush/close 後に削除してから再設定するように改善。
- .env 読み込みの取り扱いを堅牢化: export プレフィックス、クォート文字とエスケープ、コメントの取り扱いに対応。

### 注意事項 / 破壊的変更 (Potentially breaking)
- Settings と validate_config による環境変数の厳密なバリデーションを導入。既存の環境で無効な値（例: KABUSYS_ENV に未知の値、PAPER_FILL_MODE に未対応値）がある場合、起動時に ValueError を投げるか validate でエラー/警告が出力されます。導入時は .env を見直してください。
- run_monitoring が「環境にかかわらず本番 sqlite_path を使用する」点は設計上の挙動です。テスト/開発環境で別 DB を使いたい場合は Settings の環境変数を適切に設定してください。
- process_priority / set_cpu_affinity は実行環境の権限に依存します。権限不足時は警告が出て設定がスキップされます。

### ドキュメント / メモ
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup のヘッダにも明記）。
- config/*.yaml（system_config.yaml など）は存在しない場合や PyYAML がインストールされていない場合に警告が出ます。サンプル生成用のスクリプトやドキュメントを参照して設定ファイルを用意してください。
- ログディレクトリ作成に失敗した場合でもコンソールログは継続するため、まずは標準出力でのログを確認してください。

---

今後の予定（例）
- research/factor_research.py の完全実装（ファクター計算の SQL/処理の完成）。
- 戦略・実注関連モジュールのテストカバレッジ拡充、CI ワークフローの導入。
- 銘柄ごとの lot_size をマスタデータから読み込む拡張等。
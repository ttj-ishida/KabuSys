# Changelog

すべての注目すべき変更をここに記録します。  
形式は「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買フレームワークの基本コンポーネントを追加しました。

### 追加 (Added)
- 基本パッケージのエントリポイントとバージョンを追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 環境設定管理
  - Settings クラスを追加（src/kabusys/config.py）。環境変数から各種設定（J-Quants / kabu API / DB パス /監視閾値 等）を取得。
  - 自動 .env ロード機構を実装（.env / .env.local、OS 環境変数の保護付き。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値チェックとデフォルト処理を実装。
- .env ウィザード CLI
  - src/kabusys/config_setup.py を追加。対話式で .env の生成・更新を支援（複数設定項目、シークレットマスク表示、保存確認）。
- 設定検証 CLI
  - src/kabusys/validate_config.py を追加。必須環境変数・パス・YAML ファイルの存在や本番環境用ガードのチェックを実行。--strict オプションで警告も失敗扱いに可能。
- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで起動。stop flag（data/stop_requested.flag）および pid ファイル処理を実装。
    - RiskManager 用デフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を追加。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - stop flag 検知でループ終了。例外はログ出力して次回ポーリングへ。
- モニタリング DB 初期化ユーティリティ（init_monitoring_db の使用箇所を追加）。
- ツール: Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH）から集計し、稼働率 / 注文成功率 / 送信率 / レイテンシ（P95 等）を出力。既定の合否閾値（稼働率 99%、成立率 90%、送信率 95%、P95 ≤200ms）を設定。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装（スコア基準でのフォールバック処理を含む）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター集中上限を満たす候補除外）、calc_regime_multiplier（bull/neutral/bear の乗数）を実装。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score 配分ロジック、lot_size（単元）丸め、aggregate cap によるスケールダウンと端数再配分ロジックを実装。
  - ポートフォリオ API のエクスポートを追加（src/kabusys/portfolio/__init__.py）。
- 研究モジュール
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR、avg turnover、volume ratio）などの計算を DuckDB 上の prices_daily テーブルから行う設計。
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - psutil を利用して Windows/Linux/macOS に対応。優先度レベル("high","normal","low") と CPU コア固定機能を提供。アクセス権限等で失敗した場合は警告でスキップ。
- パッケージ化のためのツールモジュール初期化ファイルを追加（tools/__init__.py、utils/__init__.py）。

### 変更 (Changed)
- .env 読み込み動作
  - 自動ロードの優先順位を OS 環境変数 > .env.local > .env とし、OS 環境変数は protected として上書きされないように実装。
- 起動時のプロセス優先度設定を各起動スクリプトの最初で実行するよう統一（run_execution, run_monitoring）。
- 実行エンジンと監視で DuckDB と SQLite の接続処理を明確化（両 DB のクローズを finally で保証）。

### 修正 (Fixed)
- .env 解析の堅牢化（src/kabusys/config.py）
  - export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープの正しい処理、インラインコメントの取り扱い、空行・コメント行の無視などを実装。
  - 無効行や未設定キーの扱いを改善。
- MONITOR_POLL_INTERVAL の不正値に対してデフォルト値へフォールバックするように実装。0 以下や非整数入力での time.sleep の例外を回避。
- run_execution の paper_trading 用 DB 分離を実装し、paper_trading 環境で本番 DB に書き込まれないよう保護。
- Paper 検証レポート
  - レイテンシの P95 計算、Null 値取り扱い、データ欠損時のフォールバック（OperationalError 時）を追加。
- process_priority の例外ハンドリングを強化。プラットフォーム未対応時や権限不足時に実行を継続できるように警告ログでフォールバック。

### ドキュメント (Documentation)
- 各 CLI スクリプトおよびモジュール内に使用方法や設計意図を示すモジュールドキストリング・コメントを追加。
  - run_monitoring.py, run_execution.py, config_setup.py, validate_config.py, paper_verification_report.py, portfolio/*, research/factor_research.py 等。

### 注意事項 / 既知の挙動 (Notes)
- monitoring は設計上、KABUSYS_ENV にかかわらず settings.sqlite_path（本番監視 DB）を使用します。paper_trading の監視を完全に分離したい場合は別途設定を用意してください。
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。無効値は ValueError を発生させます。
- config/ 以下の YAML 検証は PyYAML インストール時のみ有効。未インストール時はスキップして警告を出します。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告が出て設定は適用されない可能性があります。

---

今後の予定:
- stocks マスタを用いた銘柄別 lot_size 対応（position_sizing の拡張）。
- 監視・実行コンポーネント間のメトリクス連携強化（duckdb / monitoring DB のスキーマ拡張）。
- 更なる単体テストおよび CI 統合。

（必要であればリリース日や細かいコミット ID を追記します。）
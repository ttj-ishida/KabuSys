# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはコードベースの現在状態から推測して作成しています。

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 実行/監視用エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（既定: data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を設定し、PID ファイル / stop フラグによる安全な起動・停止をサポート。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop フラグ検知／KeyboardInterrupt による安全な終了処理。
- 設定管理・ヘルパー
  - config.py
    - .env ファイルの自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
    - .env の読み込み順序: OS 環境 > .env.local > .env。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 環境変数のパース改善: export プレフィックス、クォート内のエスケープ、インラインコメント処理などに対応。
    - Settings クラスを提供し、アプリ全体で環境変数を型付きで取得可能（DB パス、paper trading パス、しきい値等）。
  - config_setup.py
    - .env を対話形式で作成・更新するウィザード。
    - 必須項目のマスク表示、既存値の再利用、保存前の確認を実装。
  - validate_config.py
    - .env や config/*.yaml の事前検証 CLI を追加。
    - --strict オプションで警告も失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML がある場合）や本番時のガードチェックを実装。
- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークによる候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分の計算（全スコアが 0 の場合は等分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）と候補の除外。`unknown` セクターは除外対象外。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull/neutral/bear のマップ、未知レジームはフォールバック＋警告）。
  - position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - 単元株 (lot_size)、max_position_pct、max_utilization、コストバッファを考慮した aggregate cap とスケールダウンロジック。
    - ロット単位で丸め、残余キャッシュで大きな fractional 残差順に追加割当するフェアネス処理を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティ（StreamHandler→stdout、TimedRotatingFileHandler→日次ローテーション）。
    - ログレベルとログディレクトリの解決順を実装。既存ハンドラのクリア処理やファイルハンドラ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - 権限不足時や未サポート OS の場合は警告を出して安全にスキップ。
- Tools
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを抽出して判定（PASS/FAIL）。
    - P95 計算、日付フィルタ（--from / --to）、DB パス解決（引数 / 環境変数 / デフォルト）を実装。
- 研究用モジュール（下書き）
  - research/factor_research.py を追加（ファクター計算機能: モメンタム/Value/Volatility/Liquidity 設計の骨子。DuckDB を使った prices_daily/raw_financials 参照設計を開始）。

### 変更 (Changed)
- なし（初期リリース想定）

### 修正 (Fixed)
- .env パースの堅牢化
  - export プレフィックス対応、クォート内でのバックスラッシュエスケープ処理、インラインコメントの取扱い、無効行や空行・コメント行の無視など細かなパースルールを実装。
- ログ設定の堅牢化
  - ログディレクトリ作成に失敗した場合のフォールバック（コンソール出力のみ）と既存ハンドラの適切なクローズ処理を追加。

### 内部 (Internal)
- sqlite3 / duckdb 接続の扱いを統一
  - run_execution / run_monitoring で SQLite（監視・ペーパートレード用の分離）と DuckDB（分析用）をそれぞれ接続・クローズするライフサイクルを明確化。
- PID/stop フラグ / kill flag の運用
  - run_execution と run_monitoring で data/*.pid / stop_requested.flag を用いる運用設計を導入。

### セキュリティ (Security)
- なし

---

注記:
- 本 CHANGELOG は提示されたソースコードから機能や振る舞いを推測して作成したものです。実際の変更履歴やコミット履歴とは異なる可能性があります。実際のリリースやユーザー向けドキュメントを作成する際は、コミットログ・リリースノートを参照してください。
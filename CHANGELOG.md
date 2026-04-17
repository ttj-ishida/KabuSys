# Changelog

すべての変更は "Keep a Changelog" の形式に従い、慣習的にセマンティックバージョニングを用いています。  
日付はリリース日を示します。

## [Unreleased]
（現状なし）

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能・ユーティリティ・CLI を含みます。

### 追加 (Added)
- 全体
  - パッケージ初版リリース。バージョンは kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）。
  - DuckDB と SQLite を併用するローカル分析／監視基盤の構成を導入（デフォルトパス: data/kabusys.duckdb / data/monitoring.db）。
- 設定管理
  - Settings クラスを導入し、環境変数経由で設定を取得（src/kabusys/config.py）。
  - .env 自動ロード機能を追加（プロジェクトルートの .env/.env.local を読み込み）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パース機能の強化: export 構文、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - 必須設定の検査や環境別フラグ（is_live / is_paper / is_dev）をサポート。
  - Paper Trading 用の専用設定:
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
    - PAPER_FILL_MODE（instant|partial|never|reject のバリデーション）
- CLI / ユーティリティ
  - 設定検証 CLI: python -m kabusys.validate_config
    - .env と config/*.yaml の存在・基本整合性チェック、--strict モードで警告を failure として扱う（src/kabusys/validate_config.py）。
  - 設定ウィザード: python -m kabusys.config_setup
    - 対話式に .env を初期生成・更新するウィザードを実装（src/kabusys/config_setup.py）。
- 実行 / 監視スクリプト
  - 実行エンジン起動スクリプト run_execution.py を追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して paper_trading.db に記録し、本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) および PID ファイルの取り扱いを実装。
    - コンポーネント組み立て: BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を統合。
  - 監視ループ起動スクリプト run_monitoring.py を追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 環境にかかわらず monitoring は本番 sqlite_path を使用（監視 DB を保証的に初期化）。
    - 停止フラグ検知で安全にループ終了。
- 実行周辺ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux(macOS 等 POSIX) の差分を吸収。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクターキャップ・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有比率から新規候補を除外）、calc_regime_multiplier（bull/neutral/bear のマッピング）。
  - 株数算出・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）丸め、max_position_pct、max_utilization、aggregate cap（available_cash に収めるためのスケーリング）を実装。
    - cost_buffer を用いた保守的なコスト試算と残差配分ロジック。
  - ポートフォリオ API を簡易エクスポート（src/kabusys/portfolio/__init__.py）。
- リサーチ / ファクター計算
  - DuckDB を用いたファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum: 1M/3M/6M リターン、MA200 乖離
    - Volatility / Liquidity: ATR20、20日平均売買代金、出来高比率 など
    - データ不足時は None を返す設計。SQL + Python の混成で実装。
- Paper Trading 検証レポート
  - paper_verification_report ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定（閾値はファイル内定義）。
    - --from / --to / --db オプションで期間・DB を指定可能。
- 監視 DB 初期化
  - init_monitoring_db 関数利用による監視テーブルの冪等初期化呼び出しを導入（run_execution/run_monitoring から呼出しを実施）。

### 変更 (Changed)
- 設定読み込み順序の明確化:
  - 読み込み優先順位は OS 環境変数 > .env.local > .env（既存 OS 環境変数は保護され、.env.local で上書き可能）。
- デフォルト値:
  - DUCKDB_PATH, SQLITE_PATH 等のデフォルトパスをコード上で明示（data/ 以下）。

### 修正 (Fixed)
- .env パースの堅牢化:
  - 引用符内のバックスラッシュエスケープ対応や、コメント判定ルールの改善により .env のパース精度を向上（src/kabusys/config.py）。
- ポーリング間隔のバリデーション:
  - MONITOR_POLL_INTERVAL が 0 以下または不正な文字列の場合はデフォルト（60 秒）にフォールバックし警告を出す（src/kabusys/run_monitoring.py）。
- CPU affinity / priority 設定の例外ハンドリング強化:
  - 権限不足や未サポート環境での失敗をログ警告に変換して起動継続（src/kabusys/utils/process_priority.py）。

### 既知の注意点 / マイグレーション
- .env ファイルは絶対に Git にコミットしないでください（config_setup が注意喚起を行います）。
- 本番（KABUSYS_ENV=live）での運用時は LINE 通知（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず設定することを推奨。validate_config は本番向けの追加チェックを実行します。
- Paper Trading は本番 DB と分離されるよう設計されていますが、運用前に PAPER_TRADING_SQLITE_PATH の値を確認してください。
- calc_position_sizes の lot_size は現状全銘柄共通の想定。将来的に銘柄別単元対応に拡張予定（TODO コメントあり）。
- factor_research 等は DuckDB のテーブルスキーマ（prices_daily / raw_financials）が前提。データ投入が必要です。

### セキュリティ (Security)
- 環境変数に機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を直接置く設計のため、運用環境では適切なシークレット管理（ファイルパーミッション / シークレットマネージャ）の使用を推奨します。

---

今後の予定（例）
- ユニットテスト・CI の整備
- 銘柄別 lot_size 対応、手数料/スリッページモデルの拡張
- SystemMonitor / ExecutionEngine の詳細なログ・メトリクス拡張
- factor_research の追加ファクター・正規化ユーティリティを kabusys.data.stats と統合

（必要であれば、個別ファイルの変更点や想定されるバグ修正履歴をさらに詳述します。）
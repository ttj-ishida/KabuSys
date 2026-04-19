# Changelog

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。  

※本リポジトリのバージョンは src/kabusys/__init__.py の __version__ に合わせて記載しています。

## [Unreleased]
- 現在なし

## [0.1.0] - 2026-04-19
初回リリース。

### 追加 (Added)
- 基本パッケージ
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
- 環境/設定管理
  - Settings クラス（src/kabusys/config.py）を実装。
    - 環境変数や .env から各種設定を取得するプロパティを提供（J-Quants, kabu API, DB パス, ログ設定、監視閾値など）。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実施（無効値は例外）。
    - paper_trading 用の paper_sqlite_path、paper_fill_mode（有効値検証）をサポート。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
- 環境設定ウィザード
  - 対話式 .env 作成/更新ツール（src/kabusys/config_setup.py）を追加。
    - 複数の設定項目を対話形式で入力可能。既存 .env の読み込み・再利用に対応。
    - .env ファイルの書き出しテンプレートを提供。
- 設定検証 CLI
  - validate_config（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在/パースチェック（PyYAML があれば検証）を実行。
    - --strict オプションで警告も失敗扱いにできる。
- 起動スクリプト
  - 実行エンジン起動スクリプト run_execution（src/kabusys/run_execution.py）を追加。
    - 起動時にプロセス優先度を高く設定。
    - paper_trading 環境では paper_trading 専用 SQLite DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立て。
    - ストップフラグ（data/stop_requested.flag）と PID ファイル管理に対応。スレッドでエンジンを実行し、停止フラグ検知で安全に停止。
  - 監視ループ起動スクリプト run_monitoring（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視専用 DB 初期化を実行）。
    - check_once() 呼び出しの例外を捕捉して次のポーリングへ移行。
- ロギング/プロセスユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト logs/, 日次ローテーション、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗やファイルハンドラ作成失敗は適切に扱い、コンソール出力にフォールバック。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > デフォルト。
  - プロセス優先度/CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX を吸収する set_process_priority、set_cpu_affinity を実装。権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順・タイブレークロジック）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分でフォールバック）を実装。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクターエクスポージャーを計算し、新規候補をフィルタリング、"unknown" セクターは制限を適用しない）を実装。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく投下資金乗数、未知値は警告して 1.0 にフォールバック）を実装。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。単元株（lot_size）丸め、per-position と aggregate のキャップ、cost_buffer を考慮したスケールダウンアルゴリズムを実装。
    - price 欠損時のスキップやログ出力を備える。
  - ポートフォリオモジュールの public API を __init__ でエクスポート。
- Paper Trading 検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加。
    - 指定期間の system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計してレポート出力。
    - P95 計算、しきい値（稼働率 99% 等）による PASS/FAIL 判定を実装。
    - CLI 引数 --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数に対応。
- 監視 DB 初期化
  - init_monitoring_db（import 経路あり、monitoring_db モジュール）を run 系スクリプトから呼び出して監視テーブルが存在することを保証（冪等）。
- 研究系モジュール（未完／設計のみ）
  - ファクター計算用モジュール（src/kabusys/research/factor_research.py）を追加（モメンタム・MA200・ATR 等の計算ロジックを実装する方針が記載、DuckDB を利用）。一部実装が途中（ファイル末尾で途切れ）。

### 変更 (Changed)
- ログ出力設計
  - 全起動スクリプトで共通の logging_setup を使用することでログ設定を統一。
- DB パス取り扱い
  - paper_trading と本番で SQLite の分離を明確化（run_execution が紙取引用 DB を選択するロジックを持つ）。
- エラーハンドリング強化
  - ログディレクトリ作成失敗、ファイルハンドラ生成失敗、プロセス優先度設定失敗などで警告を出してフェイルしない動作に統一。

### 修正 (Fixed)
- 環境変数読み込みの堅牢化
  - .env パースのクォート内エスケープ、インラインコメント処理、export プレフィックス対応を導入し、一般的な .env 表記の互換性を向上。
- ポーリング間隔の妥当性チェック
  - MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合に警告を出しデフォルトにフォールバックする処理を追加。time.sleep に渡して ValueError になるのを防止。

### 注意事項 / 既知の制約 (Known issues)
- research/factor_research.py はファイル末尾で実装が途切れており、一部関数の完成が必要。
- position_sizing の価格欠損時の扱いについて TODO コメントあり（price が 0 の場合のフォールバックを将来的に検討）。
- 実際のブローカ接続や ExecutionEngine の内部挙動・テストは別モジュール（execution/*）に委ねられており、外部依存（kabu API 等）の動作確認が必要。
- .env は意図的に Git にコミットしないこと（config_setup の出力ヘッダでも注意喚起）。

---

履歴の粒度や分類について修正希望があれば指示ください。必要ならば各モジュールごとの詳細な変更点（関数ごとの説明、引数/戻り値）を追記します。
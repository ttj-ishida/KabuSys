# CHANGELOG

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠しています。  
リリースの日付はリポジトリの __version__ に基づく初期公開として記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース。

### Added
- 基本アプリケーション構成
  - パッケージ基本情報 (src/kabusys/__init__.py, __version__ = 0.1.0)
- 環境設定・管理
  - Settings クラスによる環境変数アクセスラッパー（src/kabusys/config.py）
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のパス、各種閾値、KABUSYS_ENV 検証などを提供
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env ロードの抑止
  - 自動 .env ロード機能
    - プロジェクトルートを .git / pyproject.toml から探索して .env / .env.local を自動読み込み
    - .env のパースは export 形式、クォート、エスケープ、インラインコメント等に対応
    - OS 環境変数を保護する protected オプションで上書きを制御
- 対話式環境設定ウィザード
  - config_setup CLI（src/kabusys/config_setup.py）
    - .env の初期作成・更新を対話式で支援するウィザード
    - J-Quants / kabuAPI / DB パス / ログレベル / Kill Switch 設定等を入力・保存
- 設定検証ツール
  - validate_config CLI（src/kabusys/validate_config.py）
    - 必須環境変数・KABUSYS_ENV の妥当性・DB パスの親ディレクトリ・config/*.yaml の存在とパース（PyYAML 任意）等を検査
    - --strict モードで警告を失敗扱いにできる
- 起動スクリプト
  - Execution 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離
    - BrokerClientFactory を用いたブローカークライアント生成、OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行
    - 停止フラグ (data/stop_requested.flag) による安全停止、PID ファイル管理
  - Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - Monitoring は環境にかかわらず本番の sqlite_path を使用して監視情報を記録
    - プロセス優先度を起動時に High に設定
- ユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - すべての起動スクリプトで共通のログ設定を提供（stdout StreamHandler + 日次ローテート FileHandler）
    - LOG_LEVEL / LOG_DIR の解決順をサポート、ログディレクトリ作成失敗時はコンソールのみで継続
  - プロセス優先度 / CPU Affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収し、nice 値や Windows 優先度クラスを設定
    - psutil を利用、権限不足や未対応環境での失敗は警告でフォールバック
- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/）
  - portfolio_builder
    - select_candidates: スコア降順で候補抽出（タイブレークは signal_rank）
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全 0 の場合は等配分にフォールバック）
  - risk_adjustment
    - apply_sector_cap: セクター集中上限を考慮して候補を除外（unknown セクターは除外対象外）
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear + フォールバック）
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出
      - 単元株（lot_size）丸め、1 銘柄上限、総投資額の aggregate cap、cost_buffer（スリッページ・手数料見積）を考慮
      - available_cash を超える場合はスケーリングして再配分（端数は lot 単位で再配分）
- Paper Trading 検証ツール（src/kabusys/tools/paper_verification_report.py）
  - SQLite（paper_trading DB）からシステム安定性・注文成功率・送信率・レイテンシ等を集計してレポート出力
  - P95 計算、閾値（稼働率 99%、成功率 90% など）による PASS/FAIL 判定
  - 日付範囲指定 (--from / --to)、DB パスはオプションまたは環境変数で指定可能
- リサーチ（未完のモジュールを含む）
  - research/factor_research.py: DuckDB を用いたファクター計算の枠組み（モメンタム等）。関数インターフェースと設計方針を実装

### Changed
- 初回公開のため変更履歴なし（新規追加のみ）

### Fixed
- .env パーサーの堅牢化（クォート・エスケープ・export 形式・インラインコメントの取り扱いを改善）
- ログディレクトリ作成に失敗した場合にファイルハンドラをスキップしてコンソール出力にフォールバックする安全策を実装
- プロセス優先度設定・CPU affinity の失敗（権限不足や未対応プラットフォーム）を例外で止めず警告で継続するようにした
- Execution 起動時に監視用テーブルが存在しない場合でも init_monitoring_db() で冪等に作成する処理を追加

### Known Issues / Notes
- research/factor_research.py の一部（calc_momentum 関数の実装開始）はファイル末尾で途切れており、完全実装が必要です。
- position_sizing の価格フォールバックについて TODO コメントあり（価格欠損時の取り扱い改善予定）。
- config/*.yaml のパース検証は PyYAML に依存（未インストール時は警告を出して検証をスキップ）。
- .env はセキュリティ上 Git にコミットしないこと。config_setup でもその旨の注意を出力。

### Security
- .env ファイルに機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を含むため、絶対にリポジトリにコミットしない旨の注意を README / .env ヘッダに明記。

---

今後の予定:
- research/factor_research の完成とテスト追加
- Execution / Monitoring 周りの E2E テスト整備
- 銘柄毎の lot_size 対応（stocks マスタの導入）や手数料見積の改善

(本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時には追加のドキュメントやコミット履歴の確認を推奨します。)
# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット:
- 追加: 新機能や新しいファイル/CLI
- 変更: 既存の振る舞いの変更
- 修正: バグ修正
- 非推奨 / 削除 / セキュリティ: 該当する場合に記載

なお、リリース日にはこの CHANGELOG 作成時点の日付 (2026-04-22) を使用しています。

## [Unreleased]

- なし（初回リリースに向けての未リリース項目はありません）。

## [0.1.0] - 2026-04-22

### 追加
- 基本アプリケーションパッケージを追加。
  - src/kabusys/__init__.py にバージョン情報（0.1.0）とエクスポート設定を追加。

- 起動スクリプト / 実行運用関連
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager（RiskConfig を含む）、Reconciler、ExecutionEngine の組み立てと起動処理を実装。
    - デーモンスレッドでエンジンを走らせ、 data/stop_requested.flag による外部停止監視を実装。
    - 起動時にプロセス優先度を「high」に設定するユーティリティ呼び出しを行う。
    - DuckDB と SQLite 接続処理を追加（監視テーブル初期化を保証）。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用するように実装。
    - stop flag の検知、例外時のログ出力、KeyboardInterrupt ハンドリングを実装。
    - 起動時にプロセス優先度を「high」に設定。

- 環境設定 / 検証 CLI
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 複雑な .env パースロジック（export プレフィックス、クォート内のエスケープ、インラインコメント処理等）を実装。
    - 必須/任意設定のプロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, PAPER_FILL_MODE など）。
    - KABUSYS_ENV/LOG_LEVEL のバリデーションを実装。
    - settings = Settings() のインスタンスをエクスポート。

  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 複数の設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連等）。
    - 既存 .env の読み込み、対話プロンプト、確認後の .env 保存機能を実装。
    - 書式化されたヘッダを持つ .env 出力を行う。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL のバリデーション、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース検証（PyYAML がある場合）を実施。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで選別。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率に応じた重みを計算（全スコアが 0 の場合は等金額にフォールバックし警告）。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限のチェックと候補除外ロジックを実装（"unknown" セクターは上限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（未定義レジームは 1.0 にフォールバックし警告）。

  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいた発注株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した安全なスケーリング、残差処理による追加配分ロジックを実装。

  - portfolio/__init__.py: 上記関数群をエクスポート。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一ロギング設定ユーティリティを追加。
    - コンソール出力（stdout）用 StreamHandler と 日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装し、既存ハンドラのクリア処理を行う。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

  - utils/process_priority.py:
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加（Windows / POSIX 対応）。
    - カレントプロセスの優先度設定（high/normal/low）と CPU affinity を設定する関数を実装。
    - 権限不足や未対応環境でのフォールバックログを出力。

- ツール / レポート
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（fill_rate）・送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を集計・表示。
    - 日付フィルタ (--from / --to) 対応、P95 の計算ロジック、閾値に基づく PASS/FAIL 判定を実装。

- リサーチ / ファクター計算（骨子）
  - research/factor_research.py:
    - ファクター計算モジュールの骨子を追加（モメンタム、Value、Volatility、Liquidity の設計方針と定数定義）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する方針を定義。
    - calc_momentum の docstring と定数が追加（実装は続く / 未完の箇所あり）。

### 変更
- なし（初回リリースのため既存からの変更はありません）。

### 修正
- なし（初回リリース）。

### 注意点 / 既知の制限
- .env 自動ロード:
  - プロジェクトルートが検出できない場合は自動ロードをスキップします。テストや特定環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- paper_trading 実行時:
  - Paper Trading は本番 DB と分離される設計だが、paper 環境用の DB が未作成の場合は起動時に親ディレクトリの存在チェックで警告が出る可能性があります（validate_config の挙動参照）。
- research/factor_research.py は一部未完（calc_momentum の実装途中）です。将来的に DuckDB クエリと計算ロジックの完成が必要です。
- position_sizing の lot_size は現在全銘柄共通で固定 (デフォルト 100)。将来的に銘柄別の単元対応を検討。

### セキュリティ
- 機密情報（API トークン等）は .env として管理する設計です。.env を絶対に Git にコミットしないよう README 等で周知してください（config_setup.py のヘッダにも注意書きあり）。

---

今後のリリースでは research モジュールの完成、Execution/Monitoring の追加ロギングやエラー耐性強化、テスト・ドキュメントの拡充を予定しています。
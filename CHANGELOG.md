# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

<!-- NOTE: 初回公開リリースとして 0.1.0 を記載します -->
## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションパッケージ `kabusys` を追加。
  - バージョン情報: src/kabusys/__init__.py にて `__version__ = "0.1.0"` を公開。

- 実行用エントリスクリプト
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine をスレッドで起動し、data/execution.pid を用いる。
    - 停止処理はプロジェクトルートの `data/stop_requested.flag` を監視して行う。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用するよう分離。
    - BrokerClientFactory と各種コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立てて実行。
    - RiskManager のデフォルト設定値をコード内で定義（max_position_pct 等）。初期 available cash は broker.get_available_cash() を利用。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor を定期的に poll（デフォルト 60 秒）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能。不正値はデフォルトにフォールバック。
    - 監視は環境に依らず本番 sqlite_path（data/monitoring.db）を使用して監視テーブルを初期化。
    - 停止フラグファイルを検知して優雅に終了。

- 設定管理
  - Settings クラス: src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順とオーバーライド挙動（OS 環境変数保護）を実装。
    - 各種設定プロパティ（DB パス、LINE、kabu/J-Quants トークン、監視閾値、環境判定フラグ等）を提供。
    - `PAPER_FILL_MODE` のバリデーション（instant/partial/never/reject）。
  - 設定ウィザード CLI: src/kabusys/config_setup.py
    - 対話式で .env を生成・更新。シークレット項目はマスク表示。
    - デフォルト値と説明を含むテンプレートで .env を書き出すユーティリティを提供。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 環境変数や config/*.yaml の存在・基本妥当性を検査。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加チェック（LINE 通知設定や Kill Switch の設定など）。

- ロギング/プロセスユーティリティ
  - ログ設定ユーティリティ: src/kabusys/utils/logging_setup.py
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR の作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル解決（引数 > 環境変数 > デフォルト）。
  - プロセス優先度 / CPU affinity 設定: src/kabusys/utils/process_priority.py
    - Windows/Linux/macOS などの差分を吸収して優先度を設定（high/normal/low）。
    - CPU affinity 固定機能を提供（利用不可時は警告を出してスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - 銘柄選定 / 重み計算: src/kabusys/portfolio/portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコア全てが 0 の場合は等金額配分へフォールバック。
  - セクター集中制限 / レジーム乗数: src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を考慮してセクター制限を適用（unknown セクターは制限除外）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" に対する乗数を提供。未知レジームは警告を出して 1.0 にフォールバック。
  - 株数決定 / リスク制限 / 単元丸め: src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数算出。
    - ロット単位（lot_size）で丸め、ポジション上限や aggregate cap（available_cash）を考慮してスケーリング。
    - cost_buffer（手数料・スリッページ推定）を考慮した保守的見積り、残余キャッシュを用いた端数配分ロジックを実装。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - SQLite（paper_trading DB）を読み、稼働率・注文成功率・送信率・レイテンシ（平均、最大、P95）などを集計して簡易レポートを標準出力に生成。
    - CLI: --from/--to/--db オプション対応、閾値に基づく PASS/FAIL 判定。
    - P95 計算と日付フィルタの実装。

- リサーチ（ファクター計算）骨格
  - src/kabusys/research/factor_research.py
    - モメンタム / ボラティリティ等の計算方針、定数と calc_momentum の骨組みを追加（DuckDB を利用）。ファイル途中までの実装であり、以降の実装は今後拡張予定。

### Changed
- .env 読み込み挙動
  - .env のパースを堅牢化（引用符付き値のエスケープ、export 形式、行末コメントの扱い等に対応）。
  - 自動ロードを環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト利便性向上）。

- ログ出力の取り扱い
  - logging_setup: ファイル出力に失敗しても落ちないようにし、代わりに stdout のみで継続するよう変更。

### Fixed
- run_monitoring のポーリング間隔取得で不正な環境変数値（0、負数、非整数）を検出してデフォルトにフォールバックするよう修正。
- process_priority/set_cpu_affinity: サポート外プラットフォームや権限不足時に例外で停止せず警告ログを出すよう修正。
- run_execution: 停止フラグが既に立っている場合はエンジンを起動せず終了するガードを追加（誤起動防止）。
- config_setup: 既存 .env を読み込み、Enter で既存値を再利用できるように変更。シークレットはマスクして表示。

### Notes
- 初期リリースのため、一部機能（例: research.factor_research の詳細実装、外部 BrokerClient 実装の差分や strategy 実装）は骨格または参照実装に留まります。今後のリリースで順次拡張予定です。
- DB のデフォルトパスや挙動（monitoring は本番 sqlite_path を使用、paper_trading は専用 DB を使用）はコード内ドキュメントを参照してください。
- .env ファイルには機密情報（API トークン等）が含まれるため、絶対にバージョン管理システムにコミットしないでください（config_setup も同旨を警告して書き出します）。

--- 

今後のリリースでは以下を予定しています（例）:
- strategy / execution の詳細実装と統合テスト
- research モジュールの完成（ファクター計算の最終化）
- 監視/アラート（LINE）連携の実装とテスト
- ドキュメント整備・サンプル設定ファイルの追加

もし CHANGELOG に加えて、特定ファイルの差分説明やリリースノート用の英語版が必要であれば教えてください。
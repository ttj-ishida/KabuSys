# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に従って記載しています。  
フォーマット: 追加 (Added) / 変更 (Changed) / 修正 (Fixed) / 非推奨 (Deprecated) / 削除 (Removed) / セキュリティ (Security)。

## [Unreleased]
- 今後のリリースに向けたマイナー改善・テストの予定。  

## [0.1.0] - 2026-04-21
初回公開リリース。

### Added
- パッケージメタ
  - パッケージバージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。

- 設定管理
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装（src/kabusys/config.py）。
    - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
    - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` のサポート。
    - 各種プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境判定等）。
    - 環境値／ログレベルのバリデーション（有効な値チェック）。
    - Paper Trading 用設定（paper_sqlite_path, paper_fill_mode など）。

- 設定ウィザード / 検証ツール
  - 対話式 .env 作成・更新ウィザード実装（src/kabusys/config_setup.py）。
    - 必須/任意項目の定義、既存値の読み込み、シークレットマスク表示、保存機能。
  - 起動前設定検証 CLI 実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML がある場合）。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行スクリプト
  - 実取引／ペーパートレード用 ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（MockBrokerClient と実クライアントの切替を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行制御（PID ファイル、stop flag による終了）。
    - デフォルトの RiskConfig パラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。
  - システム監視用ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、0以下は無効扱いしてフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視テーブル初期化含む）。
    - 停止フラグファイルによる安全停止、例外発生時のロギングとリトライ継続処理。

- ロギング / プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定、30 日分保持。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - プロセス優先度 / CPU アフィニティ設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応した優先度設定（nice/Windows 優先度クラスを使用）。
    - CPU アフィニティ固定機能（最初の N コアに固定）。
    - 権限不足や未対応プラットフォームは警告ログでスキップ。

- 監視 DB 初期化
  - 監視用 DB スキーマ初期化呼び出しのための init_monitoring_db (呼び出し元あり) を参照している（run_monitoring/run_execution で使用）。※実装ファイルは monitoring パッケージ内に存在を想定。

- ポートフォリオ構築モジュール（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: score 降順＋signal_rank タイブレークで選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重計算。全スコアが 0 の場合は等金額にフォールバックして警告。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有セクター暴露が閾値を超える場合に候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market レジームに応じた資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金）を超える場合のスケーリングと端数配分ロジックを実装。
    - cost_buffer による保守的なコスト見積もりの適用。

- Paper Trading 検証ツール
  - ペーパートレード検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計。
    - デフォルトの基準値（稼働率 >= 99%、注文成功率 >= 90% 等）に基づく PASS/FAIL 判定を出力。
    - DB パスはコマンドライン --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- リサーチ（骨組み）
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 系の計算方針と定数を定義。
    - DuckDB を使い prices_daily / raw_financials を参照して計算する設計（関数 calc_momentum の実装開始あり、途中までのソースを含む）。

- パッケージエクスポート
  - portfolio パッケージの __all__ を整備して関数群を公開（src/kabusys/portfolio/__init__.py）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記:
- 実運用にあたっては .env に機密情報を含めないよう注意してください（config_setup でも警告あり）。
- run_monitoring は監視データに本番 sqlite_path を使用する設計になっているため、テスト環境で監視を走らせる場合はパスに注意してください。
- 一部のモジュール（monitoring_db、execution.* の詳細実装、DuckDB スキーマ、BrokerClient 実装など）は本 changelog の時点で別ファイルに分かれている想定です。必要に応じてそれらの実装・テストを参照してください。
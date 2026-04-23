# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」規約に準拠します。  

最新リリース: 0.1.0（初回公開）

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-23
初回リリース。自動売買フレームワークの基盤機能を追加。

### Added
- 起動スクリプト / 実行制御
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV に応じて本番／ペーパートレードを切り替え。
    - ペーパートレード時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）、OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせてエンジンを起動。
    - ストップフラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の取り扱いを実装。
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は本番用 sqlite_path を使用して起動（環境に依存しない監視 DB の使用）。
    - stop フラグ検出・例外保護・リソースクリーンアップを実装。

- 設定管理 / ユーティリティ
  - config.py
    - .env 自動ロード（.env, .env.local）機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env のパースロジック（export 形式、クォート、コメント処理など）を細かく実装。
    - Settings クラスを追加し、環境変数アクセスをプロパティ化（DB パス、ログレベル、環境種別、各種閾値など）。
    - paper trading / live / development の環境判定ユーティリティを提供。
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 各設定項目の説明や既存値の再利用、シークレットマスク表示、保存確認を実装。
    - .env の書式テンプレートを提供（.env を Git にコミットしない旨のヘッダを含む）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース等をチェック。
    - --strict オプションで警告も失敗扱いにできる。
    - live 環境向けの追加ガード（LINE通知設定、KILL_FLAG_CLEAR_ON_START の確認）を実装。

- ログ・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化を提供。コンソール（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を定義。ディレクトリ作成失敗時はファイル出力を無効化して継続。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity 設定を提供。
    - psutil を使って安全に実行。アクセス権限不足時は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）・等配分（calc_equal_weights）・スコア加重（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用（apply_sector_cap）と市場レジームに基づく資金乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出（allocation_method: risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限・集計キャップ（aggregate cap）・コストバッファ考慮、スケーリング／端数割当ロジックを実装。
  - portfolio/__init__.py にて公開 API をまとめてエクスポート。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等の集計と Pass/Fail 判定を実装。
    - P95 計算、日付フィルタ、DB ファイル存在チェックを実装。閾値はソース内定数で定義（例: 稼働率 99% 等）。
  - tools パッケージ初期化ファイル追加。

- リサーチ（ファクター計算）
  - research/factor_research.py（部分実装）
    - DuckDB 接続を受けてモメンタム・ボラティリティ・流動性等の定量ファクターを計算する方針を実装。関数インターフェース（calc_momentum 等）を準備。
    - 設計方針に従い prices_daily / raw_financials を参照し、結果を (date, code) キーの dict リストで返すことを想定（実装途中）。

### Changed
- パッケージメタ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

### Fixed
- （なし）

### Security
- .env ファイルは機密情報を含む可能性が高いため、README 等で Git にコミットしないことを強く推奨（config_setup.py にも警告ヘッダを付与）。

### Notes / Known issues / TODO
- position_sizing.calc_position_sizes
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性あり。将来的に前日終値や取得原価をフォールバック価格として使用する拡張を検討する TODO コメントあり。
  - 将来的な拡張として銘柄別の lot_size を stocks マスタで管理する想定（現在は全銘柄共通の lot_size）。
- research/factor_research.py は一部未完（ファイル終端が切れている/実装継続中）。
- ログディレクトリ作成やプロセス優先度設定は環境依存で失敗する場合がある（アクセス権限不足等）。その場合は警告ログを出してフォールバック処理を行うよう設計。
- run_monitoring / run_execution は stop フラグファイルや PID 管理に依存するため、運用ルールに従ったファイル管理が必要。

---

参考:
- 環境自動読み込み: .env / .env.local をプロジェクトルート基準で探索（.git または pyproject.toml を起点）
- CLI:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

バージョン方針
--------------
- バージョン情報はパッケージの __version__（src/kabusys/__init__.py）で管理しています（現状: 0.1.0）。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 初回リリース
-------------------

追加 (Added)
- 基本実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。起動時にプロセス優先度を設定し、環境に応じて本番 DB または Paper Trading 用 DB を使い分ける。停止フラグ（data/stop_requested.flag）検出による安全停止、実行用 PID ファイルのサポートを実装。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用（監視 DB 初期化処理含む）。

- 設定・環境変数管理
  - config.py: Settings クラスを導入し、環境変数（.env ファイルを自動ロードする仕組みを含む）をラップ。必須値のチェック、環境（development/paper_trading/live）やログレベルのバリデーション、各種パス（DuckDB/SQLite/Paper Trading 用 SQLite）や監視閾値等のプロパティを提供。
  - .env 自動ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動的にロード。OS 環境変数は保護され、必要に応じて上書きの挙動を制御可能（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。
  - .env パースの強化: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、コメントの取り扱い等に対応。

- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。各設定項目の説明、デフォルト値、シークレットフィールドのマスキング等をサポート。
  - validate_config.py: 起動前に環境変数や config/*.yaml の存在・基本文法を検証する CLI を追加。--strict モードで警告を失敗扱いに変更可能。KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の不足や Kill Switch の設定確認）も含む。

- ロギング／プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定関数 setup_logging を追加。stdout へ StreamHandler を出力しつつ、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を logs/<app_name>.log に出力（デフォルト 30 日保持）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（high/normal/low）と CPU affinity 設定用ユーティリティを追加。権限不足や未サポート環境では安全に警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコアでソートして候補を選定。
    - calc_equal_weights: 等金額配分を算出。
    - calc_score_weights: スコア加重配分を算出。全スコアが 0 の場合は等金額配分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を抑えるための候補フィルタリング。既存保有のセクター別エクスポージャを計算し、閾値超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を計算。未知レジームはフォールバック（1.0）し警告を出力。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に応じて発注株数を計算。損切り率／risk_pct に基づく risk-based 計算、単元株（lot_size）での丸め、1 銘柄上限・総投下資金上限（aggregate cap）の適用、コストバッファ (cost_buffer) を考慮したスケーリングと残余分の優先配分ロジックを実装。

- DuckDB / SQLite 統合
  - Settings でのデフォルトパス（data/kabusys.duckdb, data/monitoring.db 等）を採用し、run_* スクリプトやツールで DuckDB / SQLite を接続して使用。
  - monitoring_db 初期化呼び出しを run_monitoring/run_execution の起動時に実行し、監視テーブルの存在を保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から各種指標を集計して検証レポートを生成する CLI を追加。評価指標・閾値:
    - 稼働率（uptime） >= 99.0%
    - 注文成功率（fill rate） >= 90.0%
    - 送信率（send rate） >= 95.0%
    - P95 レイテンシ <= 200 ms
  - 日付フィルタ（--from / --to）、DB パス上書き（--db）をサポート。データ不足やテーブル未作成時の安全なフォールバック処理あり。

- 研究用ファクター計算基盤（骨組み）
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算するための基盤を追加。モメンタム計算（1M/3M/6M、MA200 乖離等）向けの定数と関数設計が含まれる（実装はこのリリースで一部含まれる／継続開発予定）。

変更 (Changed)
- パッケージ初版のため、既存コードの大規模な差分はなし（初期実装群）。

修正 (Fixed)
- 初期リリースのため、既知の問題は特になし（ただし将来的に config ファイル検証、DB パス存在チェック、欠損価格のフォールバック等の改善を予定）。

注記 (Notes)
- run_monitoring は監視 DB に常に本番 sqlite_path を使用する設計です。開発環境とペーパートレードで監視データを分離したい場合は設定を調整してください。
- .env の自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。
- process_priority と CPU affinity の設定は権限や OS に依存するため、失敗した場合は警告ログを出力して処理を継続します。
- config/*.yaml の内容検証は PyYAML に依存します。PyYAML 未インストール時は YAML の検証はスキップされます（validate_config.py が警告を出します）。

今後の予定
- factor_research の完全実装（全ファクターの計算と正規化）。
- strategy / execution の実装拡張・テストカバレッジの追加。
- ファイル入出力や DB 初期化処理の堅牢化（権限や同時実行に対する耐性向上）。
- 銘柄毎の単元株管理や手数料モデルの反映。

--- 
（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に合わせて調整してください。）
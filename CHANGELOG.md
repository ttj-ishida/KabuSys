# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
（注: 以下の項目は提示されたソースコードから推測して作成した要約です。）

## [Unreleased]

### Added
- research モジュールのファクター計算基盤を追加（calc_momentum 等の実装開始）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して各種ファクターを算出する設計。
- ログ出力周りの改善案・デバッグ情報を追加（logging_setup のロガー初期化で詳細ログ出力）。

### Changed
- いくつかの TODO / 注釈を追記（価格欠損時のフォールバック処理など）。将来の拡張点を明示。

### Known issues / Work in progress
- research/factor_research.py が途中で切れており（実装途中の状態）、完全なファクター計算パイプラインは未完成。

---

## [0.1.0] - 2026-04-20

初回リリース。

### Added
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - 停止フラグ（data/stop_requested.flag）検知時の安全停止処理を実装。pid ファイル管理（data/execution.pid）対応。
    - ExecutionEngine を別スレッドで起動し、フラグ検知で engine.stop() を呼ぶ仕組みを採用。
- 監視エントリスクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可（デフォルト 60 秒）。不正値入力時の警告とフォールバック実装。
    - 監視用 DB 初期化（init_monitoring_db）および DuckDB 接続確立。
    - 停止フラグによりループを中断し、接続を確実にクローズする安全な終了処理を実装。
    - Monitoring は環境に関わらず本番 sqlite_path を用いる旨の設計（意図的な分離）。
- 環境設定管理
  - config.py:
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）を実装。OS 環境変数を保護する仕組みあり。
    - 複雑な .env 行パーサ（export 対応、クォート／エスケープ処理、行内コメント処理）を実装。
    - Settings クラスを導入し、各種環境変数（J-Quants トークン、kabu API パスワード、DB パス、Paper Trading 関連、監視しきい値、KABUSYS_ENV 等）をプロパティとして取得・バリデーション。
    - PAPER_FILL_MODE 等の有効値チェックを実装。
- 設定関連ツール
  - config_setup.py: 対話式 .env ウィザードを追加。既存 .env 読み込み、入力プロンプト、シークレットマスク、保存機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL のバリデーション、DB パスや config/*.yaml の存在・パース確認、KABUSYS_ENV=live 時の追加ガードを実装。--strict オプションで警告をエラー扱いに変更可能。
- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通初期化関数を実装。
    - LOG_DIR / LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py:
    - プラットフォーム差分（Windows / POSIX）を吸収したプロセス優先度設定（high/normal/low）を追加。psutil を用いた実装で、権限不足時は警告を出してスキップ。
    - CPU affinity 設定ヘルパー set_cpu_affinity を追加（先頭 N コアにピン留め）。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: リスクベース / 等配分 / スコア配分に基づく株数算出ロジックを実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。cost_buffer を考慮した保守的見積りと残差分配アルゴリズムあり。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）のデータから検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数を算出し PASS/FAIL を判定。閾値はコード内で定義（稼働率 99% 等）。
- モジュール公開
  - portfolio パッケージの __init__ を整備し、主要関数を公開。
- パッケージ情報
  - kabusys/__init__.py: バージョンを "0.1.0" に設定。

### Fixed
- .env 読み込み時の I/O エラーを警告（warnings）で扱い、プロセスを停止させないように改善。
- ロガー再初期化時に既存ハンドラを安全に flush/close してから削除することで二重出力を防止。

### Security
- .env ファイルの取り扱いに関する注意書きを config_setup に明記（.env を絶対に Git にコミットしないこと）。

### Documentation
- 各モジュールに docstring / 使用例を充実させ、設計意図（DB 分離、Paper Trading の取り扱い、レジーム乗数の意味など）を明記。

---

## Deprecated

なし

## Removed

なし

## Notes / TODO
- research/factor_research.py は途中で実装が途切れており、完全なファクター計算ロジックの追加が必要。
- position_sizing の価格欠損時のフォールバック（前日終値など）や銘柄別 lot_size のサポートは将来的に拡張する旨の TODO が存在。
- Monitoring は意図的に本番 sqlite_path を参照する仕様だが、将来的には構成で制御できるように変更する余地あり。

もし既存の変更履歴（コミットログやリリースノート）が別途存在すれば、それに合わせて日付・バージョン・記述を調整できます。必要であれば、より詳細な項目（各関数の引数仕様の変更点や内部アルゴリズムの説明）を追記します。
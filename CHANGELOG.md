# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
フォーマット: 変更はセクション（Added, Changed, Fixed, Deprecated, Removed, Security）ごとに分類しています。

なお、本 CHANGELOG はリポジトリ内のコードを解析して機能・設計上の差分を推測して作成したものであり、コミット履歴ではありません。

## [Unreleased]

- （現在リリース済みバージョン: 0.1.0。将来の変更はここに記載します）

---

## [0.1.0] - 2026-04-24

Initial release — 日本株自動売買システム「KabuSys」の初期実装。

### Added
- 実行スクリプト / デーモン類
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止用フラグファイル data/stop_requested.flag を検出してループを終了。
    - 監視用 DB は KABUSYS_ENV にかかわらず production の sqlite_path を使用して接続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアントのファクトリを利用して実行環境に応じたクライアントを生成。
    - 停止フラグと PID ファイル管理、スレッドでのエンジン実行と安全停止処理を実装。

- 設定管理 / 検証 / ウィザード
  - config.py
    - 環境変数の読み込みロジックを実装（.env/.env.local の自動読み込み、OS 環境変数の保護）。
    - .git / pyproject.toml からプロジェクトルートを探索して自動ロードを行う仕組み。
    - Settings クラスを実装し、各種設定項目（DB パス、API トークン、閾値、Paper Trading 設定等）をプロパティ化。
    - 設定値のバリデーション（enum 値チェックや 型変換）を組み込み。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数やパス、config/*.yaml の存在・パース検証を実施。
    - --strict オプションで警告も失敗（exit 1）として扱うモードを提供。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定や Kill Switch の警告）を実装。
  - config_setup.py
    - .env の対話式ウィザードを提供。既存 .env の読み込み・編集、項目ごとの説明やデフォルト値を提示。
    - 書き込み時にテンプレート形式で .env を出力（Git にコミットしない旨の注意を挿入）。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - setup_logging を提供。コンソール出力（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保存）をルートロガーに設定。
    - ログレベル/ログディレクトリの解決順を明示（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム抽象化されたプロセス優先度設定を追加（set_process_priority）。
    - CPU affinity を設定する set_cpu_affinity を追加（必要時に最初 N コアに固定）。
    - Windows / POSIX の差分を吸収し、アクセス権限不足時は警告を出してフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄除外、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数を返す calc_regime_multiplier を実装（bull/neutral/bear およびフォールバックの挙動）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based"/"equal"/"score"）に基づく株数算出ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap スケーリング、cost_buffer（手数料・スリッページ見積もり）を考慮した配分を実装。
    - ログ出力や価格欠損時のスキップなど堅牢性を確保。

- 監視 / モニタリング
  - monitoring モジュール向け初期化フック（init_monitoring_db 参照）を利用して、実行スクリプトから監視テーブルが存在することを保証。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加。
    - 指定期間（--from / --to）で以下を評価:
      - 稼働率（uptime, system_status テーブル）
      - 注文成功率 / 送信率（trade_logs）
      - リスク却下数（risk_logs）
      - レイテンシ指標（avg, max, P95）
    - PASS/FAIL 判定基準を定義（稼働率 >= 99%、成立率 >= 90% 等）し、レポート表示を行う。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。

- 研究（Research）
  - research/factor_research.py
    - モメンタム等のファクター計算モジュールを追加（DuckDB 接続を受け、prices_daily / raw_financials を参照して計算する設計）。
    - モメンタム関連定数（1M/3M/6M、MA200 乖離、ATR など）と計算方針を実装（部分実装の可能性あり）。

- パッケージメタ
  - __init__.py にてパッケージバージョンを "0.1.0" として定義。

### Changed
- n/a（初期リリースのため該当なし）

### Fixed
- n/a（初期リリースのため該当なし）

### Deprecated
- n/a

### Removed
- n/a

### Security
- n/a

---

補足 / 実装上の注意点（ドキュメント的なメモ）
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。テスト実行時に便利。
- run_monitoring は監視 DB に対して常に production 相当の sqlite_path を使用するため、paper_trading 環境でも監視は本番 DB を参照する設計になっています（意図的な分離が必要な場合は設定の見直しを推奨）。
- run_execution は paper_trading 環境では paper_sqlite_path を使用し、発注系データを本番 DB と分離します。
- process_priority や CPU affinity は権限や OS に依存するため、実行環境によっては警告が出力され設定が反映されない場合があります。
- portfolio の位置決めロジックは現状共通 lot_size（デフォルト 100）を想定しており、将来的に銘柄別単元対応の拡張を想定する TODO コメントがあります。

もし他にリリース履歴の分割（マイナー/パッチリリース分け）や、各ファイルごとのより詳細な変更点（関数レベルの変更履歴）を希望される場合は、その方針を教えてください。コード差分（git のコミットログ等）を提供いただければ、より正確な CHANGELOG を生成できます。
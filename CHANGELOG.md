# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-12

初回リリース。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys.__version__ = 0.1.0）。
  - プロジェクトルート（.git / pyproject.toml）を探索して .env/.env.local を自動読み込みする仕組みを追加（自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。読み込み時に OS 環境変数を保護する機能を実装。
  - 環境変数のパースを強化（クォートやエスケープ、inline コメント処理に対応）。

- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番用の sqlite_path を使用する設計を明記。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB から完全分離して実行。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。

- 設定管理
  - kabusys.config.Settings を実装。環境変数経由で各種設定（J-Quants / kabu / LINE / DB パス /監視閾値 /プロセス関連パス等）を取得可能に。
  - PAPER_FILL_MODE の検証を追加（"instant" | "partial" | "never" | "reject" のみ許可）。
  - 各種閾値 (CPU/MEM/DISK) や pid/kill flag 関連パス、paper_sqlite_path 等のプロパティを追加。

- モジュール群（ポートフォリオ / リサーチ / ユーティリティ / AI）
  - ポートフォリオ構築:
    - select_candidates, calc_equal_weights, calc_score_weights（kabusys.portfolio.portfolio_builder）。
    - apply_sector_cap, calc_regime_multiplier（kabusys.portfolio.risk_adjustment）。
    - calc_position_sizes（kabusys.portfolio.position_sizing）: risk_based / equal / score の配分方式、lot サイズ丸め、aggregate cap によるスケールダウン、コストバッファ考慮などを実装。
  - リサーチ:
    - factor_research: calc_momentum, calc_volatility, calc_value（DuckDB を用いたファクター計算）。
    - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（将来リターン・IC・統計サマリー等）。
    - research パッケージの __init__ にて主要関数をエクスポート。
  - ツール:
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力。
  - AI:
    - ai/news_nlp.py: ニュース記事を OpenAI (gpt-4o-mini) に送りセンチメントを計算し、ai_scores テーブルへ書き込む処理を追加。バッチ処理、チャンクサイズ上限、トークン肥大対策、429/5xx/ネットワークエラーに対するリトライ（指数バックオフ）を備える。
  - ユーティリティ:
    - utils/process_priority.py: クロスプラットフォームでプロセス優先度（Windows と POSIX の nice）を設定する set_process_priority と、CPU affinity を設定する set_cpu_affinity を追加。権限不足や未対応環境では警告を出してスキップするフェイルセーフを実装。

### Changed
- DB 初期化
  - run_execution/run_monitoring 起動時に監視用テーブルの存在を保証するため init_monitoring_db を呼び出すようにした（冪等に実行可能）。

- ロギング / 起動ログ
  - 起動環境（KABUSYS_ENV）やポーリング間隔、処理件数等の informative なログ出力を追加。

### Fixed / Robustness
- 環境値の検証とフォールバック
  - MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）を検出しデフォルト値（60 秒）にフォールバックするよう安全化。ログで警告を出す。
  - PAPER_FILL_MODE の不正値に対して ValueError を投げて早期検知。
  - KABUSYS_ENV / LOG_LEVEL の不正値に対する検証を追加（不正値で ValueError）。
  - .env ファイル読み込み失敗時は warnings.warn で通知して処理を継続。

- 計算の頑健性
  - research / factor 計算や前方リターン計算でデータ不足時に None を返すなど安全に扱う実装。
  - calc_score_weights: 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックし WARNING を出す。
  - calc_position_sizes: 価格欠損や価格 <= 0 の場合はスキップ、lot_size による丸めや aggregate cap によるスケーリング時の端数処理を整備。
  - apply_sector_cap: sector_map に存在しないコードは "unknown" 扱いにし、unknown セクターは上限チェックの対象外とする。

- AI スコアリング
  - OpenAI API キーが未設定の場合に ValueError を発生させる明確なチェックを追加。
  - 空データ（記事なし）時は処理を短絡して 0 を返す。

### Security
- OpenAI API キー等機密情報は環境変数から取得する設計。自動 .env 読み込み時には OS 環境変数を保護し、.env.local による上書きは OS 環境変数を侵さないように実装。

### Breaking Changes / 注意点
- run_monitoring は「環境にかかわらず」本番 sqlite_path を使用する設計になっています。開発／テスト環境で監視データを分離したい場合は設定（SQLITE_PATH）を明示的に変更してください。
- 自動的に .env/.env.local をプロジェクトルートから読み込む挙動はテスト環境で意図しない影響を与える可能性があります。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### Notes / 今後の改善候補（TODO）
- position_sizing: price 欠損時のフォールバック（前日終値や取得原価の利用）を検討中（TODO コメントあり）。
- 将来的に銘柄ごとの lot_size を stocks マスタで保持する拡張を想定。
- news_nlp の部分失敗時に既存スコアを保護するための DB 更新ロジック（コード絞り込み DELETE/INSERT）等は既に設計に含まれているが、運用確認と堅牢化の継続が必要。

---
この CHANGELOG はコード内のコメント・設計ノート・関数実装から推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は適宜修正してください。
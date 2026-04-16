# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの現在の状態から機能追加・設計意図・修正点を推測して作成した概要です。

全般的な注意
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。
- 重要な設計判断や既知の問題点については「Known issues / Notes」節で明記しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-16
初回公開相当のリリース。自動売買システムのコア機能群（設定管理、実行エンジン起動、監視、ポートフォリオ構築、リサーチ、ニュースNLPのスコアリング基盤、ユーティリティ、検証ツール等）を実装。

### Added
- 基本パッケージメタ情報
  - kabusys パッケージのバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理（kabusys.config）
  - .env ファイル自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
  - .env パーサを実装（export プレフィックス対応、クォート・エスケープ、行内コメント処理）。
  - 環境変数取得ユーティリティ `Settings` を提供（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 用設定など）。
  - 設定値検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の妥当性チェック）。

- 実行エンジン起動スクリプト（run_execution.py）
  - ExecutionEngine の起動ロジックを提供。
  - paper_trading 環境時は専用の SQLite（data/paper_trading.db など）を使用して本番DBと完全に分離。
  - BrokerClientFactory 経由でブローカークライアントを生成。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をデーモン的に実行。
  - 停止フラグ（data/stop_requested.flag）と PID 管理を実装。
  - RiskManager のデフォルト設定（最大ポジション比率、利用率、レートリミット、サーキットブレーカー、初期ポートフォリオ値を broker.get_available_cash() で取得）。

- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor のポーリングループ起動。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒、無効値は警告してデフォルトへフォールバック）。
  - 監視用 DB テーブルの初期化を実行（init_monitoring_db）。
  - 監視では KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（明示的に実装）。

- 監視 DB 初期化フック（monitoring_db 参照コードは本体外だが、呼び出しポイントを確立）

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - プロセス優先度設定 API `set_process_priority(level)` を追加（Windows と POSIX の差分吸収、権限エラーは警告してスキップ）。
  - CPU アフィニティ設定関数 `set_cpu_affinity(cpu_count)` を追加（利用不可時は警告してスキップ）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 等配分 `calc_equal_weights`、スコア重み `calc_score_weights`（全スコアが 0 の場合は等配分へフォールバックと WARNING）。
  - position_sizing:
    - `calc_position_sizes` 実装（risk_based / equal / score の allocation_method をサポート）。
    - 単元（lot_size）、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap スケーリング。
    - per-position 上限・aggregate キャップ、端数処理（lot_size 単位）および残余分配のロジックを実装。
    - price 欠損時のスキップ・ログ出力。
  - risk_adjustment:
    - セクター集中上限チェック `apply_sector_cap`（既存保有を元に算出、"unknown" セクターは除外しない仕様）。
    - レジーム乗数 `calc_regime_multiplier`（bull/neutral/bear マップ、未知レジームは 1.0 へフォールバックかつ警告）。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム `calc_momentum`（1M/3M/6M リターン、MA200 乖離、必要行数不足時は None を返却）。
    - ボラティリティ `calc_volatility`（ATR20、ATR 比率、20日平均売買代金、出来高比）。
    - バリュー `calc_value`（最新財務データと当日株価から PER / ROE を計算）。
    - DuckDB を用いた SQL ベース実装で大規模データ対応。
  - feature_exploration:
    - 将来リターン計算 `calc_forward_returns`（任意ホライズンの一括計算）。
    - IC（Spearman）計算 `calc_ic`、ランク付けユーティリティ `rank`。
    - ファクター統計サマリー `factor_summary`。
  - research パッケージレベルで zscore_normalize を外部の kabusys.data.stats からエクスポートする想定。

- ニュース NLP スコアリング基盤（kabusys.ai.news_nlp）
  - ニュースウィンドウ計算 `calc_news_window`（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）。
  - OpenAI 使用を前提としたスコアリング関数 `score_news` の骨格（API キー解決、ウィンドウ計算、記事集約、バッチ化、リトライ方針・レスポンス検証・スコアクリッピング等を設計）。
  - バッチサイズ、モデル、リトライ等の定数が定義され、APIエラーに対するバックオフ戦略が想定されている。
  - （注）ファイル末尾が途中で切れているため、記事フェッチ部分以降の実装（DB 集計・API 呼び出し・書き込み）は継続が必要。

- 検証ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用検証レポート生成スクリプトを追加。
  - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標計算を実装。
  - P95 計算、日付フィルタ、SQLite 接続時の例外ハンドリング、CLI 引数（--from/--to/--db）を提供。
  - 判定基準（閾値）を定義し PASS/FAIL 形式で出力。

- その他ユーティリティ
  - DuckDB / sqlite3 を同時利用する設計（分析系は DuckDB、監視/注文/取引ログは SQLite を使用する想定）。
  - ロギングを各モジュールで適切に出力。

### Changed
- なし（初回公開相当の実装を一括追加として扱うため変更履歴は省略）。

### Fixed
- 環境変数パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理など、多くの .env 書式をサポートするように実装。
- process_priority の例外処理強化
  - 権限エラー・未実装例外などを捕捉して警告ログを出し、動作継続できるようにした。

### Removed
- なし

### Security
- OpenAI API キーなどの機密情報は Settings/環境変数経由で取得する設計。直接ハードコーディングは行っていない。

---

Known issues / Notes
- news_nlp モジュールの未完了箇所
  - ファイル末尾が途中で切れており（"if not articl" で終端）、記事取得・API 呼び出し・DB 書き込みの処理が未完です。実運用前に残りの実装とエラーハンドリングの追加が必要です。
- price 欠損時の扱い
  - position_sizing / apply_sector_cap の一部ロジックでは price が 0.0（取得できない場合）だとエクスポージャー過小見積りやスキップが発生する旨の TODO コメントあり。前日終値や取得原価を用いたフォールバックを将来検討する必要があります。
- テストカバレッジ
  - 現在のコードは関数単位での純粋関数設計が多く、ユニットテストが書きやすい構造になっているが、実装ベースではテストコードは付属していません。CI による自動テスト追加を推奨します。
- デプロイ時の DB パス扱い
  - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使う仕様（設計上の明示）。テスト環境や検証用途で別 DB を使いたい場合は実行スクリプト側の挙動を変更する必要あり。

もし希望があれば、以下の対応も行えます：
- 実際のコミット履歴（git log）に基づく正確な CHANGELOG の生成
- news_nlp の未実装部の続き（記事集計・API 呼び出し・DB 書込）の実装案の作成
- 各機能ごとの利用手順 / 環境変数ドキュメントの作成

必要な出力形式（ファイルとして保存、詳細レベル、特定のバージョン差分など）があれば指示してください。
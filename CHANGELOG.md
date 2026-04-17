# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
本リポジトリはバージョン情報を `kabusys.__version__ = "0.1.0"` として提供しています。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 初回リリースとして日本株自動売買システム "KabuSys" のコア機能を追加。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ `data/stop_requested.flag` による安全な終了処理を実装。
    - 起動時にプロセス優先度を "high" に設定（utils に依存）。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は専用の paper-trading SQLite を使用し、MockBrokerClient を経由して本番 DB と完全分離。
    - 停止フラグや PID ファイル管理、バックグラウンドスレッドでの実行制御を実装。
- 設定管理
  - config.py
    - プロジェクトルート（.git / pyproject.toml）を自動検出して `.env` / `.env.local` を読み込み（自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` 行パーサーの強化（export プレフィックス対応、クォートとエスケープ、インラインコメント処理）。
    - Settings クラスを実装し、各種環境設定（API トークン、DB パス、paper_trading 用設定、監視閾値、環境/ログレベル検証など）をプロパティとして提供。
    - `PAPER_FILL_MODE` 等の値検証を実装。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と配分重み計算（calc_equal_weights, calc_score_weights）。スコアが全て 0 の場合は等金額配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（売却予定銘柄除外、"unknown" セクターは除外対象外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" のマッピング、未知レジームはログ警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株丸め（lot_size）、銘柄別上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積りをサポート。
- リサーチ / ファクター計算
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリュー（calc_momentum, calc_volatility, calc_value）を DuckDB を用いて実装。prices_daily/raw_financials を参照し、データ不足に対する安全処理を実装。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリ（factor_summary）、ランク関数（rank）を実装。外部依存を避け標準ライブラリのみで実装。
  - research パッケージのエクスポートを整理（zscore_normalize など）。
- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を追加。
    - バッチ処理（最大 20 銘柄 / コール）、トークン肥大化対策（記事数・文字数トリム）、リトライ（429/5xx/ネットワーク断に対する指数バックオフ）、レスポンス検証、スコアクリッピングを実装。
    - タイムウィンドウ計算（JST ベース→UTC 変換）を calc_news_window として提供。
    - API キー未設定時は ValueError を送出する安全設計。
- 監査・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加（--from/--to/--db オプション）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定（閾値はソース内定義）。
    - P95 計算、SQLite クエリの堅牢化（テーブル未存在時のフォールバック）を実装。
- ユーティリティ
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定ユーティリティを追加。未対応 OS や権限不足時は警告を出して安全にスキップする実装。
- パッケージ基礎
  - kabusys/__init__.py にバージョンと公開 API を追加。

### Changed
- .env 読み込みの挙動を明確化
  - OS 環境変数を保護する仕組み（protected set）を導入し `.env.local` の上書きを制御。
  - 自動読み込みをプロジェクトルート検出により CWD に依存せず実行できるように改善。
- 実行コンポーネントの DB 挙動
  - Monitoring は常に本番 sqlite_path を参照する設計（環境に依存しない監視の一貫性を確保）。
  - Execution は paper_trading モード時に専用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。

### Fixed / Improved
- 環境変数・パラメータの堅牢性向上
  - MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合、警告を出してデフォルト値にフォールバック。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL など設定値のバリデーションを追加し、不正値は明示的な例外を発生させる。
- 例外耐性の強化
  - run_monitoring のポーリングループで monitor.check_once() が例外を投げてもループを継続し、ログ出力して次回ポーリングへ移行する安全設計。
  - process_priority や CPU affinity の権限不足 / 非対応プラットフォーム時に警告を出して継続。
  - research / tools モジュールでデータ不足やテーブル未存在時に安全にフォールバックする try/except を追加。
- アルゴリズム面の保護
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合、等金額配分にフォールバックしてゼロ除算を回避。
  - position_sizing: price が欠損・ゼロの銘柄はスキップして発注数量計算の安全性を担保。aggregate cap のスケーリングと lot_size 単位での再配分ロジックを実装。
  - risk_adjustment.apply_sector_cap: 売却対象銘柄をエクスポージャー計算から除外するオプションを追加。
- レポート・統計処理
  - paper_verification_report の P95 計算と各指標取得クエリを堅牢化。データ欠落時は N/A 表示にフォールバック。
- AI ニュース処理の信頼性
  - score_news: OpenAI エラー（429/5xx/タイムアウト等）に対するリトライ実装、API 応答のバリデーション、書き込み時の部分失敗を避けるための限定 DELETE/INSERT ロジックを設計（部分更新で既存スコアを保護）。

### Removed
- なし

### Security
- OpenAI API キー・各種シークレットは環境変数経由でのみ取得。`.env` 自動ロードは保護された OS 環境変数を上書きしない設計となっており、テスト用途に自動ロードを無効化する仕組み（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

---

注記:
- 各モジュールは「外部 API 呼び出しを行わない」方針の部分（research モジュール等）と、外部 API を利用する部分（ai/news_nlp, execution の BrokerClient）とが明確に分離されています。
- 一部ファイル（例: monitoring_db や execution 内の細かな実装、ai.news_nlp の続きを示す部分）はこの差分により追加・実装されていますが、ここではコードから推測可能な主要変更点を要約しています。
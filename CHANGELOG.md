# Changelog

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

リリースに関する方針:
- セマンティックバージョニングを採用しています（現行バージョン: 0.1.0）。
- 日付はリリース日を表します。

## [Unreleased]
- （現在未リリースの変更なし）

## [0.1.0] - 2026-04-13
初回公開リリース。本リポジトリに含まれる自動売買システムのコア機能群を追加しました。
主な追加内容、改善点、バグ修正を以下にまとめます。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き対応（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用して実行。
    - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを組み立て、OrderRepository / OrderManager / RiskManager / Reconciler を接続して ExecutionEngine を実行。

- 設定・環境変数管理
  - config.Settings クラスを追加。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - .env / .env.local の読み込みルール（OS 環境変数の保護、.env.local による上書き）。
    - export KEY=val 形式、クォート付き値（エスケープ処理）およびインラインコメントの取り扱いを実装。
    - 各種設定プロパティ（DB パス、PID/KILL フラグパス、しきい値、PAPER_FILL_MODE 等）を提供。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値検証を実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順／タイブレークロジック。
    - calc_equal_weights, calc_score_weights（スコア合計0のとき等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限による候補除外ロジック（売却予定銘柄の除外など）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear を想定）。
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の各配分方式、単元株丸め、per-stock および aggregate cap、cost_buffer を含めたスケーリング。残差処理による lot 単位での追加配分ロジックを実装。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1m/3m/6m リターン、MA200 乖離率を DuckDB 上で計算。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を参照して PER/ROE を計算（target_date 以前の最新財務データを採用）。
  - research.feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得するクエリ実装（入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算（欠損値除外、十分なサンプル数チェック）。
    - factor_summary / rank: 基本統計量とランク変換（同順位は平均ランク）を実装。
  - research.__init__ で主要 API をエクスポート。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_scores を生成・書き込み。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 範囲）機能を提供（calc_news_window）。
    - API キー解決、バッチサイズ、トークン軽減用の article/char 制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリッピング（±1.0）等を実装。
    - DuckDB を用いた読み取り／部分的な置換書き込み戦略（失敗時に既存スコアを保護）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成 CLI を追加（--from / --to / --db オプション対応）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標計算および PASS/FAIL 判定ロジック（しきい値は定数化）。
    - P95 の算出、NULL 安全なフォーマット関数、SQL の日付フィルタ組立を実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX を吸収して nice または HIGH_PRIORITY_CLASS を設定。アクセス拒否などは警告でフォールバック。
    - set_cpu_affinity(cpu_count): 指定コアにプロセスをピン留め（未対応環境では警告でスキップ）。

- DB 初期化サポート
  - monitoring.monitoring_db.init_monitoring_db が起動スクリプトで呼ばれ、監視用テーブルの存在を保障（冪等）。

### Changed
- 設定の自動ロード
  - .env/.env.local の読み込み順と override の挙動を明確化（OS 環境変数は保護され、.env.local は上書きする）。
- ExecutionEngine 用 DB 選択ロジック
  - paper_trading 環境時は paper_sqlite_path を使用して本番 DB と完全分離するように変更。
- ロギング
  - 起動スクリプトで基本的な logging.basicConfig(level=logging.INFO) を設定し、各モジュールは適切に logger を利用。

### Fixed
- 各種防御的処理の追加
  - MONITOR_POLL_INTERVAL の不正値（0 以下や変換不能）に対して警告しデフォルトにフォールバックする処理を追加（run_monitoring）。
  - portfolio.calc_score_weights で全銘柄のスコア合計が 0 の場合に等配分へフォールバックし WARNING を出すように修正。
  - research.calc_forward_returns / other: 引数検証（horizons の範囲チェック等）とデータ不足時の None ハンドリングを実装。
  - ai.news_nlp の API キー未設定時に ValueError を投げ、明確なエラーメッセージを返すようにした。
  - .env パーサのクォート処理（バックスラッシュエスケープ）やコメント認識の不具合を修正。

### Security
- 環境変数の自動ロード時に OS 環境変数を保護する仕組みを導入（.env/.env.local による上書きを制御）。

### Documentation / Comments
- 各モジュールに詳細な docstring と設計方針、仕様説明を追加。特に研究・ポートフォリオ・AI モジュールは設計ノート（参照ドキュメントや想定データソース）を明記。

### Internal / Misc
- パッケージメタ情報
  - kabusys.__init__ に __version__ = "0.1.0" を設定。
- DuckDB / SQLite 両方を併用する設計を採用（分析用 DuckDB、永続化用 SQLite）。

## Deprecated
- （現時点では無し）

## Removed
- （現時点では無し）

注: 本 CHANGELOG はコードベース（src/ 以下）の内容から推測して作成しています。実際の変更履歴（コミットやリリースノート）と若干表現が異なる可能性があります。必要であれば、各項目についてより詳細（影響範囲・使用方法・互換性注意点など）を追記します。
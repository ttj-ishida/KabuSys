# CHANGELOG

すべての注目すべき変更点を記載します。本ファイルは Keep a Changelog 準拠の形式でまとめています。

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買フレームワークのコア機能群を追加しました。主な追加／改善点は以下の通りです。

### 追加 (Added)
- 実行・監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。実行中はプロセス優先度を "high" に設定します。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite DB（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と完全分離する仕組みを導入。
    - BrokerClientFactory を介してブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててエンジンを起動します。
    - 停止フラグ（data/stop_requested.flag）を監視して安全に停止する仕組みを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト: 60秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録します（監視 DB 初期化は idempotent）。
    - 停止フラグでループを終了する挙動を実装。

- 設定管理モジュールを追加
  - config.py
    - .env / .env.local の自動読み込み（OS 環境変数を保護する仕組みを含む）。
    - .env パーサはクォート、エスケープ、コメント（インラインコメント含む）を考慮した堅牢な実装。
    - Settings クラスに各種プロパティを実装（DB パス、PID パス、閾値、環境判定、paper_fill_mode のバリデーション等）。

- ポートフォリオ構築（純粋関数群）を追加
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋同点タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を評価して候補を除外（unknown セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告の上フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した株数算出。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer による保守的見積り、残余キャッシュを使った端数処理（lot 単位での配分）を実装。

- リサーチ／ファクター計算モジュールを追加
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value：DuckDB の prices_daily / raw_financials テーブルを用いたファクター計算を実装。
    - 各関数はウィンドウサイズや不足データ時の None ハンドリングを考慮。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターン取得（入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算（同順位の平均ランク処理、データ不足判定）。
    - rank / factor_summary: ランク変換と基本統計量（count/mean/std/min/max/median）を実装。
  - research パッケージは外部ライブラリに依存せず、DuckDB 接続を用いる設計。

- ニュース NLP スコアリングを追加（AI モジュール）
  - ai/news_nlp.py
    - raw_news から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む処理を設計。
    - タイムウィンドウ計算（JST 基準→UTC 変換）ユーティリティ calc_news_window を実装。
    - バッチ送信（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx のエクスポネンシャルバックオフリトライを考慮。
    - API キー未設定時には ValueError を送出する安全策を導入。
    - 出力の JSON バリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（該当コードのみ削除→挿入）などの設計方針を明示。

- 解析・検証ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。CLI (--from / --to / --db) をサポート。
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計して PASS/FAIL を判定する閾値を設定（デフォルト閾値はソース内で定義）。
    - P95 計算、各種 SQL クエリ、欠損テーブルに対する耐性（OperationalError をキャッチして N/A を扱う）を実装。

- ユーティリティを追加
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（high/normal/low）を提供。
    - CPU affinity のピンニング機能（set_cpu_affinity）を提供。権限不足や未対応 OS の場合は警告を出してスキップ。

- パッケージ初期化
  - kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - portfolio / research / tools / utils の __all__ やエクスポートを整理。

### 変更 (Changed)
- 環境変数の自動読み込みの優先順位を明確化
  - 優先度: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env.local は override=True により OS 環境変数以外を上書き可能としています（protected により OS 環境変数の保護を実現）。

- 監視ループのデフォルトポーリング間隔と取り扱い
  - MONITOR_POLL_INTERVAL 環境変数を導入し、整数での上書きが可能（デフォルト: 60 秒）。不正な値（非整数、0 以下など）は警告を出してデフォルトにフォールバックするように変更。

### 修正 (Fixed)
- .env パーサの堅牢化
  - export キーワード対応、クォート内でのバックスラッシュエスケープ、インラインコメントの取り扱い等を細かく実装し、一般的な .env フォーマット差異に耐性を持たせました。

- ファクター / リサーチ計算の安定性
  - momentum / volatility / value / forward returns 等において、データ不足時には None を返す、ウィンドウ集計で行数確認を行うなど、NULL 伝播やカウント不足による誤計算を防ぐ実装。

- position sizing のスケーリング処理の改善
  - aggregate cap 適用時に lot_size 単位で端数処理を行い、残余キャッシュで fractional 残差の大きい順に追加配分するロジックを導入（再現性のため二次キーに code を使用）。

### 既知の制限 / 注意事項 (Known issues / Notes)
- ai/news_nlp.py は API 呼び出し周りの実装（_fetch_articles 等の一部ロジック）は継続実装が必要な箇所がある可能性があります（スニペットは一部で切れているため、実際の運用前に完全実装とテストを推奨します）。
- 一部の機能はプラットフォーム依存（プロセス優先度・CPU affinity）で、権限不足時は警告を出してスキップする設計です。運用環境での権限確認を推奨します。
- position_sizing の price の欠損時の扱いに TODO コメントあり（将来的に前日終値や取得原価をフォールバックすることが検討されています）。

### セキュリティ (Security)
- 現時点で特別なセキュリティ修正はありません。API キー等の機密情報は環境変数経由で供給する設計です。.env 自動ロードは無効化可能です。

---

今後のリリースでは、AI スコアリングの完全な実装、ExecutionEngine 周りの細かい運用ロギング・回復処理、テストおよびドキュメントの拡充を予定しています。問題・改善要望があれば issue を作成してください。
CHANGELOG
=========

すべての重要な変更点をここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

既知のバージョン
----------------

### [0.1.0] - 2026-04-16
初回リリース。

概要
- 日本株自動売買システム "KabuSys" のコア機能群を実装。
- 以下の主要サブシステムを提供:
  - 実行エンジン（ExecutionEngine）とブローカー抽象化（paper/live 切替）
  - 監視ループ（SystemMonitor）起動スクリプト
  - ポートフォリオ構築（候補選定・重み付け・ポジションサイズ）
  - リスク調整（セクター上限・レジーム乗数）
  - リサーチ（ファクター計算・特徴量探索）
  - ニュース NLP（OpenAI を用いた記事センチメント集約）
  - 開発用ツール（Paper Trading 検証レポート）
  - 環境変数/.env 管理とプロセス制御ユーティリティ

Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用して本番 DB と完全分離。
    - 起動前に stop フラグを検査し、フラグが立っている場合は起動を回避。
    - 実行中は stop フラグ検知でエンジンを安全停止。
    - プロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計コメントを明示。
    - stop フラグファイル検知でループ終了。KeyboardInterrupt による終了をハンドリング。

- 環境・設定管理
  - config.py
    - .env/.env.local の自動読み込みを実装（プロジェクトルート検出: .git/pyproject.toml 基準）。
    - 読み込み順: OS環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート。
    - .env パーサを実装: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、無効行のスキップなどに対応。
    - Settings クラスで多数の設定プロパティを提供（DB パス、PID/kill フラグパス、閾値、env 判定、paper_trading の各種設定）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - env/log_level の妥当性チェックを実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・タイブレークでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額／スコア比率での重み計算（スコア全てが 0 の場合は等配分にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。
    - 単元株（lot_size）丸め、ポジション上限（max_position_pct）、投下上限（max_utilization）、コストバッファ（cost_buffer）を考慮。
    - aggregate cap 超過時のスケールダウンと端数処理（fractional remainder に基づく lot 単位での追加配分）を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）と未知レジームのフォールバック（1.0）を実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を参照して各種ファクター（モメンタム、MA200乖離、ATR、平均売買代金、PER/ROE 等）を計算。
    - データ不足時の None 処理やウィンドウサイズに関するガードを実装。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターンを一括で計算。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）の場合は None。
    - factor_summary / rank: 基本統計量・ランク計算ユーティリティを実装。
  - research/__init__.py
    - 公開 API を整備（z-score 正規化の再エクスポート含む）。

- ニュース NLP（AI）
  - ai/news_nlp.py
    - raw_news を記事集約して OpenAI（gpt-4o-mini）に送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み。
    - 処理はバッチ（最大 20 銘柄/コール）、記事数と文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実施。
    - API 失敗（429/5xx/接続タイムアウト等）に対する指数バックオフリトライを実装。
    - レスポンスの厳密な JSON 検証とスコアクリップ（±1.0）。
    - タイムウィンドウ計算ユーティリティ calc_news_window を提供（JST を UTC に変換して DB 検索に使用）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を計算し、閾値に基づく PASS/FAIL 判定を標準出力に表示。
    - CLI オプション --from/--to/--db をサポート。
    - P95 計算、NULL 値ハンドリング、テーブル欠損時のフォールバックを実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装（Windows と POSIX を吸収）。
    - set_cpu_affinity(cpu_count) を実装（指定が None の場合は操作しない）。
    - 権限不足や未対応 OS の場合は warning を出して安全にスキップ。

Changed
- パッケージ初期化
  - kabusys/__init__.py にバージョン 0.1.0 を設定。

Fixed / Behavior notes
- MONITOR_POLL_INTERVAL の取り扱い
  - 環境変数からの読み取り実装で不正な値（非整数・0/負数）の場合は警告ログを出しデフォルト（60秒）にフォールバックするようにした（time.sleep への不正値渡しを防止）。
- .env パーサ
  - export プレフィックス、クォート内部のバックスラッシュエスケープ、インラインコメント処理など現実の .env 形式に即した取り扱いを実装し、誤解析を低減。
- DB 分離（paper_trading）
  - paper_trading 環境は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番監視 DB と分離して動作するようにした（実行スクリプトでの明示）。
- セーフティ
  - ニュース NLP と ExecutionEngine の処理は API／外部依存の失敗時にフェイルセーフ（スキップ・ログ）になるよう実装。データベース更新は部分失敗時に既存データを不必要に上書きしない工夫（ai_scores の部分置換方針）を設計方針として明示。
- 計算マイナー修正
  - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし警告ログを出す。
  - position_sizing の aggregate スケール処理で lot 単位の端数処理と残余キャッシュの再配分を実装。

Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY から取得し、未設定時は ValueError を返す（安全な失敗）。

Notes / Limitations / TODO
- 一部関数で外部データ欠損（価格欠損など）により保守的にスキップする実装がある（price が 0 の場合等）。将来的に前日終値や取得原価などのフォールバック価格を導入する余地あり（コメントで指摘）。
- news_nlp.py の処理フローの末尾が未表示のため、実装詳細の一部（記事集約から API 呼び出し・DB 書き込みの完全な実装）については追加実装が想定される（現在ある設計コメントに基づく挙動は記載の通り）。
- DuckDB / SQLite スキーマ変更やマイグレーションは別途ドキュメント化を推奨。

今後
- テストカバレッジの充実（特に .env パーサ、position sizing の端数処理、AI レスポンス検証）。
- 銘柄別単元株情報（lot_size）を銘柄マスタへ移し、銘柄ごとに調整可能にする。
- ニュース NLP のロギング・メトリクス強化と失敗時の再実行戦略の改善。
- ExecutionEngine / SystemMonitor の監視メトリクスを Prometheus 等に露出する案の検討。

-----------
（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノート作成時は差分コミットや PR コメントを参照して適切に調整してください。）
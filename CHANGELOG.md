CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

[Unreleased]
-------------

（現状のコードスナップショットは初期リリース相当の機能群を含むため、主要なリリースは下記 0.1.0 として記載しています。
以降の開発で差分が出た場合はここに追記してください。）

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能を追加。
  - 実行系 / 監視系のエントリポイント
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite DB（data/paper_trading.db（環境変数で上書き可））に記録する仕組みをサポート。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視処理は環境に依らず本番 sqlite_path を使用する挙動を明示。
  - 設定・環境変数管理
    - kabusys.config.Settings クラスを実装。
      - .env 自動読み込み（プロジェクトルートの .env / .env.local、OS 環境変数優先）。
      - 多数の設定プロパティを提供（DB パス、PID/KILL ファイルパス、監視閾値、PAPER_FILL_MODE のバリデーション等）。
      - 環境変数未設定時は明確な例外を投げるヘルパーを用意（_require）。
    - .env ファイルパーサを実装（コメント行、export プレフィックス、クォート／エスケープ、インラインコメント処理に対応）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder
      - シグナルの候補選定（score 降順・タイブレークの安定化）。
      - 等金額配分 / スコア加重配分（スコアが全て 0 の場合は警告を出して等配分へフォールバック）。
    - portfolio.position_sizing
      - allocation_method（risk_based, equal, score）に基づく株数決定ロジック。
      - 単元株丸め（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリング実装。
      - scale 割合に基づく残余配分ロジック（fractional remainder による lot 単位の再配分）。
    - portfolio.risk_adjustment
      - セクター集中上限（apply_sector_cap）: 既存保有のセクター別エクスポージャーを計算し、上限超過セクターは候補から除外。
      - レジームに応じた投下資金乗数（calc_regime_multiplier）："bull"/"neutral"/"bear" に対応。未知レジームは警告後フォールバック。
  - リサーチ／特徴量計算
    - research.factor_research
      - モメンタム（1m/3m/6m リターン、MA200 乖離）、ボラティリティ（ATR20、相対 ATR、出来高関連指標）、バリュー（PER/ROE）を DuckDB 上で計算する関数を提供。
      - データ不足時の None 処理やウィンドウサイズの安全設計を実装。
    - research.feature_exploration
      - 将来リターン（forward returns）計算、IC（Spearman の rank correlation）計算、ファクターの統計サマリ機能を追加。
      - ties（同順位）を平均ランクで扱うランク関数を実装し、安定した Spearman 計算を行う。
  - AI ニュース NLP（OpenAI 統合）
    - ai.news_nlp
      - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチで投げて銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込むワークフローを実装。
      - バッチサイズ、トークン肥大化対策（最大記事数／文字数）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）等の設計を採用。
      - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
  - ユーティリティ
    - utils.process_priority
      - Windows / POSIX（Linux, macOS, FreeBSD）に対応したプロセス優先度設定（high/normal/low）。
      - CPU affinity 固定機能（最初の N コアにピン留め）を提供。権限不足や未対応 OS 時は警告を出してスキップ。
  - 運用ツール
    - tools.paper_verification_report
      - Paper Trading 用検証レポート生成スクリプトを追加（コマンドライン引数により期間指定可）。
      - 指標: 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を出力。閾値はソース内で定義（稼働率 99% 等）。
  - パッケージ情報
    - kabusys.__version__ を "0.1.0" として定義。

Changed
- DB 関連の実行方針を明示
  - 監視系は環境に関係なく本番 sqlite_path を使用する設計に変更（監視データは実環境と同じ DB を参照する意図）。
  - ExecutionEngine は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離。
- .env 自動ロードの挙動
  - OS 環境変数を保護する protected 機構を導入し、.env.local は .env を上書き可能にした（優先順位: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。

Fixed
- 環境変数の耐障害性向上
  - MONITOR_POLL_INTERVAL の不正（非整数や 0 以下）を検出し、デフォルト値へフォールバックする挙動を追加。ログで警告を出力。
  - PAPER_FILL_MODE のバリデーションを追加し、不正な値時は ValueError を送出して早期検出。
  - .env パーシングでクォートやバックスラッシュエスケープ、インラインコメントを正しく処理するよう改善。
- 安全な DB 初期化
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。Execution 系でも起動時に呼ぶことでスキーマ不足による起動失敗を回避。

Security
- なし

Notes / Known limitations
- 一部関数（例: position_sizing の price フォールバック、apply_sector_cap の price 欠損時の過少見積り）は TODO コメントで将来的な改善を示唆。現在は簡易実装のため運用上の注意が必要。
- ai.news_nlp は OpenAI との通信やモデルのレスポンス形式に依存するため、API 仕様変更に伴う修正が必要になる可能性がある。
- CPU affinity / プロセス優先度の設定は権限や OS に依存し、失敗時は警告を出して処理を継続する設計。

参考: 実行例
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用 DB に記録
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

（以降の変更はこのファイルの [Unreleased] セクションに追記してください。）
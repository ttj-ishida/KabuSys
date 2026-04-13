CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （現在無し）

0.1.0 - 2026-04-13
------------------

Added
- パッケージ初期リリース。
- 実行エントリ/監視エントリ:
  - run_execution.py を追加。ExecutionEngine の起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db 既定）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動（engine.run_session()）。
    - プロセス優先度を起動時に "high" に設定するユーティリティ呼び出しを実行。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を "high" に設定、SQLite / DuckDB 接続確立、SystemMonitor.check_once() を定期実行。Ctrl+C (KeyboardInterrupt) による安全終了処理あり。
- 設定／環境読み込み:
  - kabusys.config の Settings クラスを追加。
    - .env / .env.local の自動ロード（OS 環境変数 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml で検出。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサは export 形式、クォート、バックスラッシュエスケープ、インラインコメントを考慮した堅牢な実装。
    - 各種設定プロパティを提供（J-Quants / kabu API トークン、LINE、DuckDB/SQLite パス、paper_trading のパス/モード、監視関連パス（pid/kill flag）、閾値、環境判定・ログレベル検証など）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）を実装。
- ポートフォリオ構築（純粋関数群）:
  - portfolio.portfolio_builder: シグナル選定 select_candidates、等重み calc_equal_weights、スコア重み calc_score_weights（全銘柄スコア 0 の場合は等重みへフォールバック）。
  - portfolio.position_sizing: calc_position_sizes を実装。
    - risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した計算。
    - aggregate cap によるスケーリングと端数処理（lot 単位での切捨てと残差に基づく追加配分ロジック）を実装。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中上限による候補除外）、calc_regime_multiplier（市場レジームに応じた乗数）を実装。
- リサーチ／ファクター計算:
  - research.factor_research: DuckDB（prices_daily / raw_financials）を用いた定量ファクター計算を実装。
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、20日平均売買代金、出来高比率）、バリュー（PER, ROE）の計算を提供。
    - SQL ウィンドウ関数を活用した効率的実装。
  - research.feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（スピアマン順位相関）計算、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリに依存しない実装。
  - research パッケージ __init__ で主要関数をエクスポート（zscore_normalize は data.stats から利用）。
- AI / ニュース NLP:
  - ai.news_nlp モジュールを追加（OpenAI を利用したニュースのセンチメントスコアリング）。
    - ニュース取得ウィンドウ（JST 基準、前日 15:00 〜 当日 08:30）を厳密に計算。
    - raw_news + news_symbols を銘柄ごとに集約し、1 銘柄あたりの最大記事数 / 最大文字数でトリム。
    - 最大 20 銘柄ずつのバッチで OpenAI（gpt-4o-mini）へ送信し、JSON Mode で結果を期待。
    - 429・ネットワーク・タイムアウト・5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアを ±1.0 にクリップ。
    - 一括処理後、ai_scores テーブルへ影響範囲を限定して置換（部分失敗時に既存スコアを保護する戦略）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決、未設定時は ValueError。
- ユーティリティ:
  - utils.process_priority: set_process_priority（Windows / POSIX を吸収して優先度設定）、set_cpu_affinity（最初の N コアに固定）を実装。
    - psutil の例外（AccessDenied 等）を捕捉して警告ログに落とし、実行継続するフェイルセーフ。
- ツール:
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs などの集計から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を算出し、しきい値に基づく PASS/FAIL 判定を出力。
    - CLI サポート（--from, --to, --db）。DB ファイル不在やテーブル不備に対する堅牢なハンドリング（OperationalError をキャッチして N/A を返す）。
- パッケージ情報:
  - kabusys.__init__.py に __version__ = "0.1.0" を設定。

Changed
- （この初版リリースにおける既存コードの変更履歴はありません。初回リリースのため "Added" にすべてを含めています。）

Fixed
- （この初版リリースにおけるバグ修正履歴はありません。）

Notes / Breaking changes
- Monitoring（run_monitoring）は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番 DB）を使用するため、本番 DB を監視用途で参照する点に注意してください。
- Paper Trading 実行時は run_execution が paper_trading 用の専用 SQLite を使用する設計で、本番 DB とデータ分離が行われます。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされるため、配布後やインストール環境では明示的に環境変数を設定してください。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

Security
- 外部 API（OpenAI, ブローカークライアント等）に関わる API キーは環境変数から読み込む設計です。キーや機密情報は .env に保存する場合アクセス権に注意してください。

Reference
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に合わせて修正してください。
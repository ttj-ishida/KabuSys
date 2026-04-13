CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードから推測したリリース時期（ドキュメント作成時点）を使用しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 実行・監視ランナーを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。環境変数 KABUSYS_ENV により paper_trading モード時はモックブローカーを使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db をデフォルト）へ記録する。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。

- 環境設定管理（.env 自動ロード・堅牢化）
  - config.py: .env/.env.local の自動読み込みを実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - export KEY=val 形式やクォート／エスケープを考慮した .env パーサを実装。
  - OS 環境変数は保護され、.env.local は override（上書き）可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 各種設定プロパティを追加／厳密化（例: PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の有効値チェック、各種パスのデフォルト）。

- モニタリング DB 初期化ユーティリティ
  - monitoring_db の初期化呼び出しをランナーで行い、テーブルが存在することを保証（冪等）。

- Paper Trading ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ等。
    - コマンドライン引数 --from/--to/--db に対応。
    - P95 計算や日付フィルタの実装、閾値による PASS/FAIL 判定を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークロジック
    - calc_equal_weights / calc_score_weights: 重み計算（スコア全て 0 の場合は等金額にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のエクスポージャー計算、sell_codes の除外対応）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマップとフォールバック）
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based/equal/score）に基づく株数決定、lot_size（単元）丸め、aggregate cap によるスケーリング、cost_buffer を加味した保守的見積り

- 研究用ファクター計算・探索モジュール（DuckDB ベース）
  - research/factor_research.py: モメンタム・ボラティリティ・バリュー系ファクター計算（prices_daily / raw_financials を参照）
    - calc_momentum, calc_volatility, calc_value を実装（MA200、ATR20、各ホライズンのリターン等）
  - research/feature_exploration.py: 将来リターン計算、IC（スピアマン）計算、ファクター統計要約、ランク変換ユーティリティの実装
    - calc_forward_returns, calc_ic, factor_summary, rank を提供
  - research/__init__.py で主要 API を公開（zscore_normalize は data.stats から再利用）

- AI ニュース NLP スコアリング
  - ai/news_nlp.py: raw_news / news_symbols を集約し OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores に書き込む処理を実装。
    - 処理フロー: タイムウィンドウ計算（JST→UTC 変換）、銘柄ごと記事トリム、20 銘柄バッチ、JSON モード厳格化、リトライ（429/5xx/ネットワーク系）とエラーハンドリング、スコアの ±1.0 クリップ、部分更新による安全な DB 書き換え。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得（未設定時は ValueError）。

- プロセス優先度・CPU affinity ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows / POSIX 差分を吸収して nice / HIGH_PRIORITY_CLASS 等を設定。アクセス拒否時は警告でスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアへピン留めするユーティリティを追加（引数 None で無効化）。

Changed
- モジュール構成・エクスポート
  - portfolio.__init__ にて portfolio API を明示的に再エクスポート。
  - research.__init__ で主要関数を公開。

- DB 接続ポリシー
  - run_monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path」を使用する実装（監視は常に本番データを参照する意図）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を優先して接続（本番 DB と完全分離）。

- ロギング・初期化
  - 各ランナーで logging.basicConfig(level=logging.INFO) を呼び出し、起動環境情報やポーリング間隔等を INFO ログで出力。

Fixed
- .env 読み込みの堅牢化
  - クォート内のバックスラッシュエスケープやインラインコメントの取り扱いを改善。
  - export プレフィックス対応やコメント処理の微調整。

- 報告・集計ロジックの安定化
  - paper_verification_report の各クエリでテーブル未存在時の例外処理（sqlite3.OperationalError をキャッチしてデフォルト値を返す）を追加。
  - P95 計算実装（数学的に適切なインデックス計算）を追加。

Security
- OpenAI API キーの取り扱いは明示的に環境変数/引数から取得し、未設定時はエラーを投げるようにして誤った無効呼び出しを防止。

Notes / Migration
- KABUSYS_ENV の有効値は development / paper_trading / live の 3 種類に制限されるため、既存の任意文字列を使用している場合は修正が必要です。
- PAPER_FILL_MODE の値は instant / partial / never / reject に限定され、不正値は例外になります。
- run_monitoring が常に本番 sqlite_path を使用する点は運用上重要です。モニタリング先を切り替えたい場合はコードまたは環境設計を見直してください。
- process_priority の設定は OS 権限に依存します。AccessDenied 等が発生した場合は警告ログでスキップされます。
- ai/news_nlp の OpenAI 呼び出し部は API 課金・レート制限に注意してください。未設定の API キーでは例外となります。
- .env 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgements
- 初回リリース（v0.1.0）として、実行・監視・ポートフォリオ構築・研究・AI スコアリング・ユーティリティ群を含む包括的な機能群をまとめて提供します。今後のリリースではテスト追加・例外条件の網羅・パフォーマンスチューニングに注力予定です。
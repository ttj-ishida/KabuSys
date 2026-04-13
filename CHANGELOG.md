CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠し、重要な変更のみを記載します。

Unreleased
----------

- なし（次回リリースに向けた変更を反映してください）

[0.1.0] - 2026-04-13
-------------------

Added
- 初回公開: KabuSys コードベースの基礎機能を実装
  - 実行エントリ
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告のうえデフォルトにフォールバック。
      - プロセス優先度を起動時に "high" に設定。
      - 監視用 SQLite（monitoring DB）と DuckDB に接続し、監視テーブルを初期化してループ実行。
      - KeyboardInterrupt による正常終了処理と DB クローズを実装。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用（本番 DB と分離）。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の実行。
      - Execution 起動時にプロセス優先度を "high" に設定し、DB クローズを確実に行うように finally を使用。
  - 設定管理
    - config.py
      - プロジェクトルート（.git または pyproject.toml）を基準に .env 自動読み込みを実装（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env パーサ実装: export プレフィックス、クォート文字列（バックスラッシュエスケープ対応）、行内コメント処理などをサポート。
      - override / protected の概念により OS 環境変数の保護や .env.local の上書きを制御。
      - Settings クラスを実装し、各種設定プロパティ（パス、API トークン、PID/KILL ファイル、閾値、環境選択等）とバリデーションを提供。PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL の検証を実装。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py
      - シグナルから候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全部 0 の場合は警告して等分配にフォールバック。
    - portfolio/risk_adjustment.py
      - セクター集中上限の適用 apply_sector_cap を実装（当日売却予定銘柄の除外や "unknown" セクター扱いの仕様あり）。
      - マーケットレジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバック）。
    - portfolio/position_sizing.py
      - allocation_method（risk_based / equal / score）に対応した株数決定ロジックを実装。
      - 単元株（lot_size）への丸め、個別上限（max_position_pct）、aggregate cap（available_cash を超える場合のスケールダウン）および残余キャッシュを用いた再配分ロジックを実装。
      - 手数料・スリッページ見積り用 cost_buffer を考慮。
  - ユーティリティ
    - utils/process_priority.py
      - psutil を使ったプロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定を実装。権限不足や未対応環境では警告して安全にスキップ。
  - リサーチ / ファクター計算
    - research/factor_research.py
      - DuckDB を用いたファクター計算モジュールを提供（momentum: 1M/3M/6M、ma200乖離、volatility: ATR/avg turnover/volume ratio、value: PER/ROE）。
      - ウィンドウスキャンや欠損データ時の None 扱い等、実運用を意識した実装。
    - research/feature_exploration.py
      - 将来リターン calc_forward_returns、IC 計測 calc_ic（スピアマンのランク相関）、統計サマリー factor_summary、ランク変換 rank を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - AI / ニュース NLP
    - ai/news_nlp.py
      - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコア（-1.0〜1.0）を算出し ai_scores テーブルへ更新する処理を実装。
      - 扱う時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を明示しており、ルックアヘッドバイアスを避ける設計。
      - バッチサイズ、記事数・文字数上限、429/5xx/接続エラーに対する指数バックオフリトライ、レスポンス検証、スコアクリッピング、部分成功時の部分更新（既存スコア保護）等を考慮。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成ツールを追加。コマンドライン引数 --from/--to/--db に対応。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定する閾値（稼働率 99%、成功率 90% 等）を実装。
  - パッケージ情報
    - __init__.py によるバージョン定義 __version__ = "0.1.0" と主要サブパッケージの __all__ を追加。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Known issues / Notes
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価等のフォールバックが検討される。
- position_sizing:
  - 現状は全銘柄共通の lot_size を想定。将来的には銘柄別 lot_map を受け取る拡張が想定されている（TODO）。
- ai/news_nlp.score_news:
  - OpenAI API キー未設定時は ValueError を送出する設計。API 呼び出し失敗時はフェイルセーフでスキップして継続する方針だが、運用時の監視が推奨される。
- .env 自動ロード:
  - プロジェクトルートが特定できない環境では自動ロードをスキップする（テストやパッケージ配布後の挙動に配慮）。
- 一部の設計は将来的な拡張（銘柄別 lot_size、価格フォールバック、さらなるエラーハンドリング等）を想定した TODO コメントを含む。

Security
- なし（初回リリース）

参考
- 各モジュールはデータベース（SQLite / DuckDB）、外部 API（kabu/station、OpenAI）へのアクセスを想定しています。運用前に環境変数（API トークン、パス等）の設定およびアクセス権限の確認を行ってください。
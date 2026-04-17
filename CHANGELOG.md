Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。  
本ファイルは "Keep a Changelog" に準拠しています。

フォーマット:
- 重要な変更はバージョンごとに分類（Added, Changed, Fixed, Deprecated, Removed, Security）
- 日付はリリース日

Unreleased
---------

（次回リリースに向けた変更をここに記載します）

0.1.0 - 2026-04-17
-----------------

初回公開リリース。KabuSys のコア機能群を実装・公開しました。以下は主な追加点と注意事項です。

Added
- 基本パッケージメタ情報
  - パッケージバージョン: __version__ = 0.1.0
- 環境設定 / ロード
  - Settings クラスを実装。環境変数および .env / .env.local ファイルから設定を読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - .env ファイルのパーサを実装（export 形式・クォート・エスケープ・コメント処理対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを抑制可能。
  - 必須環境変数チェック用 _require() を提供（未設定時は ValueError）。

- 実行/監視エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) と実行 PID ファイル (data/execution.pid) の取り扱いをサポート。
    - RiskConfig のデフォルト設定例を含む（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ実行スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、負値や 0 はデフォルトにフォールバックし警告）。
    - 監視は環境にかかわらず production sqlite_path を使用する旨を明示。
    - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority を使用）。
    - stop フラグ検知で安全にループ終了。
    - sqlite3 / duckdb 接続の初期化とクローズ処理を実装。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しにより監視テーブルの存在を保証（冪等）。

- ポートフォリオ構成モジュール（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates（スコア降順・signal_rank によるタイブレーク）
    - calc_equal_weights（均等配分）
    - calc_score_weights（スコア加重、スコア総和が 0 の場合は等分にフォールバック）
  - risk_adjustment.py
    - apply_sector_cap（セクター集中制限、sell_codes を考慮）
    - calc_regime_multiplier（market regime に応じた乗数: bull/neutral/bear、未知レジームは警告の上 1.0 でフォールバック）
  - position_sizing.py
    - calc_position_sizes（risk_based / equal / score の各 allocation method を実装）
    - 単位株（lot_size）で丸め、aggregate cap のためのスケーリングと端数配分ロジックを実装
    - cost_buffer を使い手数料・スリッページを保守的に見積もる

- 研究（research）モジュール
  - factor_research.py
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比）
    - calc_value（PER、ROE; raw_financials から最新レコードを取得）
    - DuckDB 経由で prices_daily / raw_financials を参照する設計
  - feature_exploration.py
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman ランク相関による IC 算出。データ不足時は None）
    - factor_summary（count/mean/std/min/max/median を算出）
    - rank（同順位は平均ランクを与える実装）
  - research パッケージの __all__ に各公開 API を追加

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から銘柄ごとに記事を集約し OpenAI API（gpt-4o-mini、JSON Mode）でセンチメントスコアを生成・ai_scores テーブルへ書込むロジックを実装。
  - バッチサイズやトークン肥大化対策（記事・文字数制限）、最大リトライ、指数バックオフ、レスポンス検証、スコアの ±1.0 クリップなどを実装。
  - ニュース時間ウィンドウ計算（JST → UTC 変換）ユーティリティを提供。
  - API キー未設定時の明確なエラー（ValueError）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート出力ツールを追加。コマンドライン引数で期間指定可能。
    - 指標: 稼働率・注文成功率・送信率・P95 レイテンシ等。閾値による PASS/FAIL 判定を行う。
    - DB が存在しない場合のエラーメッセージ。
    - SQLite のテーブル欠如に対して安全にハンドリング（OperationalError を捕捉して N/A を返す）。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority（Windows / POSIX を吸収。psutil を利用）
    - set_cpu_affinity（最初の N コアに固定、値検証）
    - 権限不足や未サポートプラットフォームでは警告を出し処理をスキップ

- その他
  - duckdb をデータ解析用に利用（research / ai モジュールなど）
  - sqlite3 を永続化（監視・paper_trading ログ等）に利用

Changed
- （初回リリースのため該当なし）

Fixed
- MONITOR_POLL_INTERVAL の不正値（非正整数など）に対して警告を出しデフォルトにフォールバックする保護処理を追加。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- サードパーティ API キー（OpenAI など）と機密情報は環境変数から取得する設計。必須の環境変数が未設定の場合は即座に例外を発生させる箇所があるため、運用時は .env の整備と適切なプロセス環境管理を行ってください。

Known issues / Notes / TODOs
- ai/news_nlp の処理は外部 API（OpenAI）に依存するため、API のレート制限や料金に注意が必要。429/ネットワーク/5xx は再試行するが、半永久的失敗時は該当チャンクをスキップする設計（フェイルセーフ）。
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する TODO を残しています。
- position_sizing:
  - lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map を導入する予定。
- utils.process_priority:
  - 一部の機能は OS/権限に依存し、権限不足や非対応環境では設定をスキップして警告を出力します。
- run_monitoring は「監視用途の DB」として settings.sqlite_path（本番パス）を常に使用します。監視を別 DB にする運用を検討する場合は設定を変更してください。
- DuckDB executemany 周りや各クエリは DuckDB のバージョン互換性に依存する箇所があります（ex. executemany のパラメータ空チェックの扱いなど）。
- 各モジュールは現状ユニットテストが同梱されていないため、運用前にローカル検証を推奨します。

依存関係（主なもの）
- python >= 3.10 以上を想定（型注釈に Path | None 等を使用）
- duckdb
- psutil
- openai (AI 機能使用時)
- sqlite3（標準ライブラリ）

実行例
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を指定可能
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading DB を使用
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

貢献 / 開発メモ
- .env パーサはプロジェクトルートを .git または pyproject.toml で自動検出するため、配布後も CWD に依存せず動作します。
- 開発中の拡張候補:
  - 銘柄別 lot_size 管理、価格フォールバックロジック、より詳細な監視メトリクス、ユニットテストの整備。

----- End of CHANGELOG -----
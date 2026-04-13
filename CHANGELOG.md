CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

フォーマット:
- 追跡対象: Unreleased / バージョンタグ（例: 0.1.0） - 日付（YYYY-MM-DD）
- セクション: Added, Changed, Fixed, Deprecated, Removed, Security

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本アプリケーションの初期実装を追加。
  - パッケージメタ情報:
    - kabusys.__version__ = "0.1.0"
- 実行エントリ / デーモン系
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を設定し（set_process_priority("high")）、SQLite / DuckDB に接続して実行セッションを開始する。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使い、本番 DB と完全に分離する設計。
    - BrokerClientFactory により実行環境に合わせてブローカークライアント（モック含む）を選択。
    - RiskManager のデフォルト設定（max_position_pct など）と Reconciler / OrderManager の組み立てを含む。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB を常に本番と同一に保つ方針）。
    - poll ループ内で check_once() の例外を捕捉してログ出力し、ループを継続するフェイルセーフを実装。
- 設定・環境変数管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - 読み込み順は OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export 形式、クォート値（エスケープ対応）、インラインコメントの扱いなどを実装。
    - Settings クラスを提供し、多数の設定プロパティ（DB パス、PID ファイル、閾値、紙トレード設定、LOG_LEVEL 検証など）を環境変数から取得するユーティリティを実装。
    - PAPER_FILL_MODE の有効値検証（instant/partial/never/reject）を実装。
- ポートフォリオ構築モジュール
  - kabusys.portfolio
    - portfolio_builder: シグナル選別（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights。全スコア0のときは等配分にフォールバック）を実装。
    - risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。レジームが未知の場合はフォールバック挙動を定義。
    - position_sizing: 各配分方式（risk_based / equal / score）に基づく発注株数算出ロジックを実装。単元株（lot_size）丸め、per-stock / aggregate キャップ、cost_buffer を考慮したスケーリング処理を実装。
- 研究・ファクター系
  - kabusys.research
    - factor_research: momentum / volatility / value ファクター計算関数（DuckDB 接続を受け取り prices_daily / raw_financials を参照）を実装。MA200、ATR20、リターン等を SQL + Python で算出。
    - feature_exploration: 将来リターン（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク計算（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
- AI ニュース NLP
  - kabusys.ai.news_nlp
    - raw_news から銘柄ごとに集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores に書き込む設計を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST → UTC に変換）を提供する calc_news_window。
    - バッチ処理・チャンク（最大 20 銘柄 / チャンク）、記事文字数上限・記事数上限のトリム、スコアを ±1.0 にクリップする仕様を実装。
    - API の 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを設計（上限回数・初期待機秒数を定義）。
    - OpenAI API キーの解決（引数または環境変数 OPENAI_API_KEY）と未設定時の ValueError を実装。
- ユーティリティ
  - utils.process_priority
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を実装。CPU affinity を設定する補助関数も追加。
    - 権限不足や未対応プラットフォーム時は警告を出して安全にスキップする。
- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成ツール（コマンドライン）を追加。DB（デフォルト: data/paper_trading.db）を読み、稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して PASS/FAIL 判定を行う。
    - レポートの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 latency 200ms）を定義。
    - CLI オプション --from/--to/--db をサポート。
- DB 初期化
  - monitoring_db.init_monitoring_db を用いて、監視用テーブルが存在することを保証する冪等な初期化呼び出しを run_*.py で行う。

Changed
- （初版のため過去の変更はなし）

Fixed
- （初版のため過去の修正履歴はなし）

Notes / Implementation details（注記）
- 監視ループの MONITOR_POLL_INTERVAL は環境変数から読み取り、不正値（非数値や 0 以下）はデフォルト 60 秒にフォールバックして警告ログを出す仕様。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後にプロジェクトルートが見つからない場合は自動ロードがスキップされる。
- apply_sector_cap は "unknown" セクター（sector_map に未登録）をセクター上限の対象外とする設計。price が欠損（0.0）の場合の過少見積りについて TODO コメントあり。
- position_sizing の scaling ロジックは lot_size 単位で再配分するアルゴリズムを実装しており、端数の追加配分は残差の大きい順に行うことで再現性を確保している。
- research モジュールは DuckDB に格納された prices_daily/raw_financials テーブルのみを参照し、本番口座や発注 API へアクセスしないよう設計されている（安全なオフライン計算）。
- news_nlp の AI 呼び出し処理はレスポンスの検証・部分失敗時の既存データ保護（更新対象コードで絞って置換）など、フェイルセーフを意識した実装方針が明記されている。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。コード内でハードコーディングはしていない。

今後の TODO（コード中の注記から推測）
- position_sizing: 銘柄別の lot_size をサポートするための拡張（stocks マスタ参照）。
- apply_sector_cap: price 欠損時のフォールバック価格（前日終値や取得原価）を使った改善。
- news_nlp: API レスポンス処理後の ai_scores 書き込みロジックの堅牢化・部分ロールバック戦略の追加。

ライセンスや貢献方法についてはプロジェクトルートのドキュメント（README / CONTRIBUTING 等）を参照してください。
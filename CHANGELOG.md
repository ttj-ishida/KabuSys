CHANGELOG
=========

すべての顕著な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

テンプレートの日付は YYYY-MM-DD 形式です。

Unreleased
----------

（未リリースの変更はここに記載します）

0.1.0 - 2026-04-12
------------------

Added
- 基本パッケージ構成
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として導入。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定（utils のユーティリティを利用）。
    - SQLite / DuckDB 接続を初期化し、監視ループ中は例外を捕捉して次のポーリングに継続するフェイルセーフを実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite DB（`PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - BrokerClientFactory により環境に応じたブローカークライアント（Mock を含む）を生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動。
    - RiskConfig のデフォルトパラメータ（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を導入。

- 設定管理
  - config.py
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）に基づく .env ファイル自動ロード機能を追加。
    - `.env` / `.env.local` 読み込みの優先順位と保護キー（OS 環境変数の保護）を実装。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - `.env` 行パーサーは export 形式、クォート文字列、バックスラッシュエスケープ、インラインコメント処理などに対応する堅牢な実装。
    - Settings クラスで各種設定プロパティを提供（パス、FLAG、閾値、PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証など）。

- ポートフォリオ構築ライブラリ
  - portfolio_builder.py
    - select_candidates: BUY シグナルのソートと上位 N 抽出。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分（全銘柄スコアが 0 の場合は等配分へフォールバックして警告）。

  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を満たすよう候補を除外するロジック。sell_codes（当日売却予定）を考慮してエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す関数（未知レジームは警告ログを出して 1.0 にフォールバック）。

  - position_sizing.py
    - calc_position_sizes: 複数の allocation_method（risk_based / equal / score）に対応した発注株数算出ロジック。
    - lot_size（単元株）丸め、per-position および aggregate cap の適用、cost_buffer（手数料・スリッページの見積）を考慮したスケーリング、端数補正ロジックを実装。

- リサーチ機能（DuckDB ベース）
  - research/factor_research.py
    - モメンタム (1M/3M/6M)、MA200 乖離、ATR20、相対 ATR、平均売買代金、出来高比率、PER/ROE（raw_financials 結合）等のファクター計算関数を追加。DuckDB 接続を受け取り SQL ベースで高速に算出。
    - データ不足時には None を返す安全設計。

  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（スピアマンのランク相関）計算、ファクター統計サマリ、ランク化ユーティリティを追加。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

  - research/__init__.py
    - 主要関数群をエクスポート（zscore_normalize は kabusys.data.stats からインポートして公開）。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込む機能を追加。
    - バッチ（最大 20 銘柄）、チャンクトリム（記事数・文字数制限）、JSON Mode を利用した堅牢なレスポンスパース、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライなどの堅牢化を実装。
    - API キー未設定時に明確な ValueError を送出。
    - DB への置換書き込み（部分失敗時に既存データを保護する方式）を採用。

- ユーティリティ
  - utils/process_priority.py
    - Windows/Linux/Mac（POSIX）に対応したプロセス優先度設定ユーティリティ（set_process_priority）を実装。未サポート OS やアクセス権限不足時は警告を出してスキップ。
    - set_cpu_affinity: 指定したコア数にプロセスをピン留めする機能を追加（引数検証あり）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成 CLI を追加（--from/--to/--db オプション）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを算出して PASS/FAIL 判定を出力するレポートを実装。
    - DB テーブル欠如（OperationalError）に対してはフォールバックしてレポートを生成する耐障害性を実装。

Changed
- （初回リリース）広範な機能群を新規導入。各モジュールはデフォルトで安全な動作を行うよう設計（データ欠損時に None を返す、例外をロギングして継続する等）。

Fixed
- 実行時の堅牢性向上
  - 監視ループ内で monitor.check_once() が例外を投げた場合にループを継続するように例外捕捉を追加（ログ出力のうえ待機継続）。
  - .env 読み込みでファイルが開けない場合に warnings.warn で通知して処理を継続。

Security
- OpenAI API キーは環境変数または明示的引数で渡す設計。未設定時は明示的なエラーを返すことで、キー未設定のまま秘密情報が漏れることを防止。
- .env 自動ロード時に既存 OS 環境変数を保護する仕組みを導入（.env の上書きを制限）。

Deprecated
- なし

Removed
- なし

Notes / 実行例
- 監視プロセス起動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - 実行例: python -m kabusys.run_monitoring

- 実行エンジン起動:
  - KABUSYS_ENV を `paper_trading` にすると paper_trading 用 DB を使用して Mock ブローカーで実行される。
  - 実行例: python -m kabusys.run_execution

- Paper Trading 検証レポート:
  - 実行例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

今後の改善余地（例）
- position_sizing の lot_size を銘柄別に指定できるよう stocks マスタ連携の検討。
- price 欠損時のフォールバック（前日終値や取得原価）の採用。
- ai/news_nlp の部分失敗時のリトライ粒度向上やメトリクス出力の追加。
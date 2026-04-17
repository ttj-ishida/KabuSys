CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョンと日付はコードベースの現状から推測して記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-17
-----------------

Added
- 基本パッケージ初期実装を追加
  - パッケージ情報: kabusys v0.1.0（src/kabusys/__init__.py）
- 実行/監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てとスレッドでのエンジン実行。
    - 停止フラグ（data/stop_requested.flag）による安全停止、実行 PID ファイル管理（data/execution.pid のパスは Settings 経由）。
    - デフォルトログレベル INFO。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 監視 DB は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループ終了、KeyboardInterrupt 対応。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
- 設定/環境変数管理の実装（src/kabusys/config.py）
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env/.env.local の読み込みルール（OS 環境変数保護、override の挙動）。
  - .env パーサ: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラス（settings オブジェクト）を提供。主要プロパティ:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（未設定時は ValueError）
    - DB 関連: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（paper_trading 用）
    - paper_fill_mode（PAPER_FILL_MODE）: instant / partial / never / reject の検証
    - 監視関連: pid_file_path, kill_flag_path, kill_flag_clear_on_start, CPU/MEM/DISK の閾値
    - 環境: KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL 検証
- ポートフォリオ構築モジュール（src/kabusys/portfolio）
  - portfolio_builder.py
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選択
    - calc_equal_weights / calc_score_weights（スコア全0 の場合は等配分にフォールバック）
  - risk_adjustment.py
    - apply_sector_cap: 既存保有を考慮したセクター集中制限。sell_codes（当日売却予定）を除外可能。unknown セクターは制限対象外とする仕様。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく乗数を返す。未知値は 1.0 でフォールバックし警告出力。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数算出を実装。
    - リスクベース算出、単元株（lot_size）丸め、per-position および aggregate cap、cost_buffer（手数料・スリッページ見積り）考慮、available_cash に応じたスケーリングと端数処理（残余で lot 単位追加配分）を実装。
    - 価格未取得時のスキップやログ出力など耐障害性を考慮。
- 研究 / ファクター計算モジュール（src/kabusys/research）
  - factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を参照して各種ファクター（モメンタム、ATR、平均売買代金、PER, ROE 等）を計算。
    - 長期移動平均や ATR のウィンドウの行数チェックを行い、データ不足時は None を返す設計。
  - feature_exploration.py
    - calc_forward_returns: 将来リターンを一度のクエリでまとめて取得する実装（horizons 引数あり、入力検証有り）。
    - calc_ic: スピアマンのランク相関（IC）を実装（同順位は平均ランクで処理）。
    - rank / factor_summary: ランク算出・基本統計量を標準ライブラリのみで実装。
  - research.__init__ によるエクスポート（zscore_normalize を含む）。
- AI ニュース NLP モジュール（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI （gpt-4o-mini）でセンチメント化し ai_scores テーブルへ書き込む処理を設計・実装。主な仕様:
    - ニュース時間ウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC へ変換）: calc_news_window を提供。
    - 1 銘柄当たりの記事数・文字数上限（記事トリム）と、銘柄バッチ（_BATCH_SIZE）で API へ送信。
    - レート制限・ネットワークエラー・5xx 等に対する指数バックオフリトライ実装（共通パターン）。
    - レスポンスの厳格な JSON バリデーションとスコアクリップ（±1.0）。
    - API キー未設定時は ValueError を送出。
- ユーティリティ（src/kabusys/utils）
  - process_priority.py
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）差分吸収。権限不足などの例外をキャッチして警告を出す設計。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定するユーティリティ。検証と例外処理あり。
- ツール（src/kabusys/tools）
  - paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。コマンドラインから期間指定でレポート出力可能。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。
    - 閾値（PASS/FAIL 基準）を定義: uptime >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms。
    - データ不足やテーブル欠損時にフォールバックしてレポートを生成。
- DuckDB と SQLite 両対応のデータアクセス設計を導入
  - DuckDB は主に時系列・研究データ（prices_daily 等）用、SQLite はランタイム監視/トレードログ用に利用する想定。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キー取り扱い
  - news_nlp.score_news は API キーが未設定の場合に ValueError を送出して安全に失敗する設計。環境変数 OPENAI_API_KEY で設定可能。

Notes / Known issues / TODO
- news_nlp は堅牢な設計で実装されていますが（バッチ・リトライ・レスポンス検証等）、将来的な拡張や実際の運用での微調整が必要です（トークン・料金対策、プロンプト改良など）。
- position_sizing.calc_position_sizes:
  - price が 0 / 欠損のときはスキップするが、将来的には前日終値や取得原価でのフォールバックを検討（TODO コメントあり）。
  - lot_size の銘柄別対応は将来的な拡張ポイント（現在は共通 lot_size）。
- apply_sector_cap:
  - "unknown" セクターは上限適用の対象外。必要に応じて扱いを変更することを検討してください。
- .env パーサは多数のケースに対応していますが、非常に複雑な .env フォーマット（複数行クォート等）では意図しない挙動をする可能性があります。
- run_monitoring の挙動:
  - 環境によらず監視 DB として sqlite_path を使う仕様のため、paper_trading 環境で監視のみを分離したい場合は運用ルールでの制御が必要です。
- ドキュメント参照:
  - 一部ソースコード内に PortfolioConstruction.md / StrategyModel.md 等の参照があるため、それらのドキュメントが存在することを前提とします（リポジトリに同梱されていることを推奨）。

開発者向けメモ
- 実行スクリプトは直接実行可能（python -m kabusys.run_execution / python -m kabusys.run_monitoring）を想定。
- 自動 .env 読み込みはプロジェクトルートを基準に行います。テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- LOG_LEVEL / KABUSYS_ENV 等の環境変数は Settings 経由の検証が入るため、不正値を与えると起動時に例外が発生します。

お問い合わせ・貢献
- バグ報告・改善提案は issue を通じてお願いします。今後のリリースではユニットテストの追加・ドキュメント整備・エンド・トゥー・エンドの検証を優先して進める予定です。
CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」フォーマットに従って記載しています。  
セマンティックバージョニングを採用しています。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 初回公開リリース (0.1.0)。
- 実行スクリプト／プロセス制御
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) の検知による安全なシャットダウン。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用 DB は環境に関わらず本番 sqlite_path を利用する設計。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のバックグラウンド実行（スレッド）を実装。
    - 停止フラグにより実行中エンジンを安全停止。
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル管理を行う（data/execution.pid 等）。
- 設定管理
  - kabusys.config
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - 読み込みは OS 環境変数を保護（.env.local は override）し、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 複雑な .env パースを実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等）。
    - Settings クラスを提供（J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境判定など）。必須変数に対しては未設定時に ValueError を送出する安全設計。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
- ポートフォリオ構築ロジック（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソートと上位選定（スコア降順、同点は signal_rank 昇順）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化配分（全スコアが 0 の場合は等分にフォールバックし WARNING）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェックにより候補を除外（"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームはログ警告後 1.0 にフォールバック）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算。単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に収まるようスケーリング）、cost_buffer を考慮した保守的見積りを実装。
    - スケーリング時の残差処理（fractional remainder）を実装し再現性を確保。
- リサーチ / ファクター計算
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（DuckDB を用いた SQL 実装）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金/出来高変化率の計算。
    - calc_value: raw_financials からの財務データ取得と PER/ROE の計算（target_date 以前の最新レコードを取得）。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターンを一括クエリで取得。
    - calc_ic: Spearman（ランク相関）ベースの IC 計算（レコード数が不足する場合は None を返す）。
    - factor_summary / rank: 基本統計量とランク処理ユーティリティ（ties は平均ランク）。
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。
- AI / ニュース NLP（OpenAI 連携設計）
  - kabusys.ai.news_nlp
    - ニュース集約ウィンドウ計算（JST ベースで前日 15:00 〜 当日 08:30 を UTC に変換する calc_news_window）。
    - OpenAI API（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコアリング設計（バッチ処理、最大トークン削減策、リトライ/指数バックオフ、レスポンス検証、スコアクリップ ±1.0、DB 書き込み戦略：対象コードのみ置換）。
    - API キー未提供時はエラーとするバリデーション。
    - （注）実装は設計上多くのフェイルセーフを備える一方、提供されたコードは一部で切れているため本番利用前に残りの実装（記事フェッチ／バッチ送信／DB 書き込み）を完了する必要あり。
- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority: Windows/POSIX の差分を吸収してプロセス優先度を設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値をマッピング）。失敗時は警告ログを出してスキップ。
    - set_cpu_affinity: 指定コア数に CPU affinity を固定するユーティリティ（引数検証、許可のない環境でのフォールバック処理）。
- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 検証レポート生成 CLI を追加（--from / --to / --db オプション対応）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出して PASS/FAIL 判定を実施。閾値はソースに定義（稼働率 99%、成立率 90% 等）。
    - P95 計算ユーティリティ、欠損データに対する安全処理、SQLite の存在チェックを実装。
- パッケージ情報
  - kabusys.__init__.py に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ でエクスポート。

Changed
- 初版のため「変更」はありません（新規追加のみ）。

Fixed
- 初版のため「修正」はありません。

Deprecated
- なし

Removed
- なし

Security
- 必須のシークレット系環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings の各プロパティで未設定時に ValueError を送出するため、起動時に明示的に検出されます。
- OpenAI 連携は API キーを必須とし、キー未設定では例外を投げる設計です。

Notes / Known issues / TODO
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーを過少見積りする可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨が TODO として残っています。
- position_sizing.calc_position_sizes:
  - 単元株（lot_size）の将来的な拡張（銘柄別 lot_map）について TODO コメントあり。
- ai/news_nlp.py:
  - 提供ソースは途中で切れている（_fetch_articles 呼び出し以降の実装が未完）。OpenAI API 呼び出し、DB の最終書き込み実装は完了させる必要あり。
- process priority / cpu affinity:
  - 実行環境の権限や OS に依存して設定に失敗する可能性があるため、失敗時は警告を出してスキップする設計になっています。
- .env 自動ロード:
  - プロジェクトルート検出に依存するため、配布後や特殊な配置では自動読み込みがスキップされることがあります。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して挙動を切替可能。

作者／貢献
- 初回リリース: 開発者チーム（リポジトリ内コードベースに基づく初回パッケージ化）

ライセンス
- ソース内に明示的なライセンス表記は含まれていません。配布時に LICENSE を添付してください。

(注) 本 CHANGELOG は提供されたコード内容から機能・設計を推測して作成しています。実際のリポジトリのコミット履歴やドキュメントと差異がある場合があります。
CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。
リリース日付はコミット時点の想定日付を使用しています。

[Unreleased]
------------

- （現在なし）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本パッケージ構成を追加（初期リリース）。
  - パッケージバージョン: kabusys.__version__ = 0.1.0
- 実行用エントリスクリプトを追加。
  - run_execution.py
    - ExecutionEngine の起動ロジック、スレッド駆動のセッション管理、停止フラグ（data/stop_requested.flag）検知、PID ファイル出力の統合。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db を既定）を使用する設計と分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - RiskConfig によるデフォルト制約（max_position_pct, max_utilization, rate_limit 等）を適用。
- 監視用エントリスクリプトを追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するという明示的設計。
    - プロセス優先度を最初に設定（high）。
    - 監視ループ中の例外は捕捉してログ出力のうえ次サイクルへ継続するフェイルセーフを実装。
- 設定管理モジュールを追加。
  - config.py
    - .env/.env.local の自動読込機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。OS 環境変数の保護と上書きルールをサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑制可能。
    - 複雑な .env 行パーサを実装（export 対応、クォートとバックスラッシュエスケープ、コメント処理など）。
    - Settings クラスを提供。JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、paper_trading 用 DB パス、PID / KILL フラグのパス、閾値やモードの検証を含むプロパティを備える。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の値検証を実装。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ計算）。
  - portfolio.portfolio_builder
    - select_candidates（スコア降順、signal_rank によるタイブレーク）
    - calc_equal_weights、calc_score_weights（全スコアが 0 の場合は等金額配分へフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap（セクターごとの既存エクスポージャー計算と候補除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（regime に応じた乗数: bull/neutral/bear、未知レジームは警告して 1.0 フォールバック）
  - portfolio.position_sizing
    - calc_position_sizes（risk_based / equal / score 配分方式、lot_size 単位丸め、単銘柄上限・aggregate cap、cost_buffer による保守的見積り、スケーリングと残余配分ロジック）
- 研究・ファクター計算モジュールを追加（DuckDB 接続を前提）。
  - research.factor_research
    - calc_momentum（1M/3M/6M リターン、MA200 乖離率。ウィンドウ不足時は None ハンドリング）
    - calc_volatility（ATR20、相対 ATR、平均売買代金、出来高比率）
    - calc_value（PER, ROE を raw_financials + prices_daily から計算）
  - research.feature_exploration
    - calc_forward_returns（任意ホライズンの将来リターンを一括クエリで計算。horizons の入力検証あり）
    - calc_ic（Spearman ランク相関による IC 計算、必要件数未満は None）
    - rank（同順位は平均ランクで処理。丸めで ties の誤検出を抑止）
    - factor_summary（count/mean/std/min/max/median）
  - research パッケージの __all__ を整備して外部公開関数を定義
- AI ニュース NLP スコアリングの下地を追加。
  - ai.news_nlp
    - ニュース収集ウィンドウ計算（JST→UTC 変換）、OpenAI API（gpt-4o-mini）を用いた銘柄ごとのバッチスコアリング設計を記述。
    - バッチサイズ、文字数上限、記事数上限、リトライ/バックオフ戦略、レスポンス検証、スコアの ±1.0 クリップ、部分更新（code を限定して DELETE→INSERT）などの方針を実装予定。
    - 実装は API キー解決、ウィンドウ算出、記事集約までのロジックを含む（ファイル末尾が途中で終わっているため一部未実装／継続中）。
- CLI ツールを追加。
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成ツール（--from, --to, --db オプション）。稼働率、注文成功率、送信率、P95 レイテンシなどの指標算出と Pass/Fail 判定を行う。
    - DB 存在チェック、テーブル欠如時の安全ハンドリング、P95 算出、各指標の閾値（稼働率 99%、Fill率 90%、Send率 95%、P95 レイテンシ 200ms）を含む。
- ユーティリティを追加。
  - utils.process_priority
    - set_process_priority（Windows / POSIX を吸収してプロセス優先度を設定。許可エラー時は警告出力してスキップ）
    - set_cpu_affinity（最初の N コアに固定、引数検証と許可不足時のフェイルセーフ）

Changed
- ログ設定をデフォルトで INFO レベルに設定するエントリポイントが追加（run_execution, run_monitoring の main 内）。
- 環境変数の自動ロード動作を明確化:
  - 読込優先順位: OS 環境変数 > .env.local > .env
  - OS 環境変数は protected として .env による上書きを防止（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

Fixed
- run_monitoring の MONITOR_POLL_INTERVAL 取り扱い:
  - 0 以下や非整数入力時にデフォルト（60 秒）へフォールバックし、警告を出すように強化（time.sleep に渡す不正値回避）。
- paper_verification_report:
  - 空データやテーブル存在しないケースでの例外を捕捉して N/A 表示や安全なデフォルトを返すように改善。
  - P95 計算実装を追加（P95 が存在しない場合は N/A）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの取り扱いは明示的に api_key 引数または環境変数 OPENAI_API_KEY を要求するように設計（未設定時は明示的なエラーを発生）。

Breaking Changes / 注意事項
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用 sqlite_path）を利用する設計です。監視 DB を分離したい場合は、設定側（SQLITE_PATH）で明示的に分けてください。
- run_execution は paper_trading モード時に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB との完全分離を行います。paper_trading 動作の際はデータ書き込み先に注意してください。
- ai/news_nlp.py は途中までの実装状態（ファイル末尾が途中で切れている）です。AI スコアリング機能を本番で利用する前に残りの実装レビューとテストを推奨します。

Notes / TODO
- position_sizing の価格欠損時（price が 0.0）における前日終値や取得原価のフォールバックは将来的な改善ポイントとして TODO コメントを残しています。
- 将来的な拡張として、単元株サイズ（lot_size）を銘柄別に持たせる設計（stocks マスタの導入）が想定されています。
- ai.news_nlp の完全実装（API 呼び出しループ、リトライ、DB 書込のトランザクション化、部分更新の最終実装）が必要です。

---

注: 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴が存在する場合は、そちらの差分に基づいて更新してください。
# CHANGELOG

この CHANGELOG は Keep a Changelog のフォーマットに準拠します。  
（コードベースの内容から推測して作成した変更履歴です）

全般的な注記
- 日付・バージョン・説明はソースコードの内容を元に推測しています。
- 一部に TODO や未実装/途中の箇所が含まれている可能性があります。該当箇所は「注意事項 / 既知の問題」として下段に記載しています。

## [Unreleased]
（次回リリースに向けた作業中の変更点／注目ポイント）
- ai/news_nlp.py におけるスコアリング処理の集約・API 呼び出し・リトライ設計が導入済み。バッチ処理・トークン対策・JSON レスポンスバリデーション・部分更新の方針が実装方針として明示されているが、処理途中と思われる箇所が存在するため、完了・統合が必要。
- DuckDB を利用したリサーチ・ファクター計算モジュール（calc_momentum / calc_volatility / calc_value）および特徴量探索ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）を前提とした改善・パフォーマンス最適化の余地がある。
- ポートフォリオ構築関連（選定・重み付け・セクターキャップ・レジーム補正・単元丸め・リスクベース配分）のユニットを整理・ドキュメント化済み。将来的な拡張（銘柄別 lot_size、前日終値フォールバック等）の TODO がある。
- 実行系（ExecutionEngine）・監視系（SystemMonitor）ランナーの運用周り（停止フラグ・PID・プロセス優先度設定）に関する運用テストが推奨される。

---

## [0.1.0] - 2026-04-16 (初回リリース: 推定)
初期リリース。以下の主要機能・モジュールを含む。

Added
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による運用制御をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視は本番 DB を参照する想定）。
    - 停止フラグ検知でループ終了、例外はログに出力して次回ループへフォールバック。

- 環境設定
  - config.py: Settings クラスを実装。環境変数から設定を取得するユーティリティを提供。
    - .env/.env.local の自動ロード（プロジェクトルート検出に .git / pyproject.toml を使用）。OS 環境変数を保護するオプションを実装。
    - 環境変数パーサの実装: export 形式、クォート文字列、インラインコメント、エスケープシーケンスに対応。
    - 各種設定項目をプロパティとして提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）。
    - 入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を追加。

- ポートフォリオ構築ライブラリ
  - portfolio_builder.py:
    - select_candidates: スコア降順・タイブレークに signal_rank を使用して候補選定。
    - calc_equal_weights / calc_score_weights: 等額配分・スコア正規化配分（スコア全0 の場合は等分にフォールバック）を実装。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中の上限チェック（max_sector_pct）に基づく候補除外。
    - calc_regime_multiplier: 市場レジームに応じた乗数（bull/neutral/bear）を計算。未知レジームは警告して 1.0 にフォールバック。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。単元株（lot_size）丸め、per-stock 上限・aggregate cap、コストバッファによる保守的見積りを実装。利用可能現金を超える場合のスケーリングと端数配分ロジックを提供。

- 研究・リサーチツール
  - research/factor_research.py:
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を用いたファクター計算を実装（MA200, ATR20, リターン等）。
    - データ不足時に None を返す安全な設計。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（複数ホライズン）計算を実装。ホライズン引数の検証あり。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、ランク付け、統計サマリーを純 Python（標準ライブラリのみ）で実装。
  - research パッケージ __all__ に主要関数をエクスポート。

- ニュース NLP（AI）スコアリング（設計・大部分実装）
  - ai/news_nlp.py:
    - raw_news を銘柄別に集約し、OpenAI（gpt-4o-mini）を用いて -1.0〜1.0 のセンチメントスコアを算出し ai_scores テーブルへ書き込む設計。
    - バッチサイズ、最大記事数・文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、JSON Mode レスポンス検証、スコアクリップ（±1.0）を導入。
    - ニュース収集ウィンドウ計算ユーティリティ calc_news_window を提供（JST を UTC に変換）。
    - API キー未設定時の例外チェックあり。

- 運用・ユーティリティ
  - utils/process_priority.py:
    - set_process_priority: Windows / POSIX の差を吸収してプロセス優先度を設定。権限不足等は警告してスキップ。
    - set_cpu_affinity: カレントプロセスの CPU affinity を設定するユーティリティ（引数検証・権限エラーをハンドリング）。
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成ツールを追加。コマンドライン引数（--from / --to / --db）に対応。
    - システム稼働率、注文成功率、送信率、リスク却下数、平均・最大・P95 レイテンシ等を集計し PASS/FAIL 判定を表示。閾値はソース内定義（稼働率 99% など）。
    - P95 計算、日付フィルタ生成、SQLite からの抽出処理を実装。

- パッケージメタ
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- DB 初期化処理:
  - init_monitoring_db(sqlite_conn) を run_monitoring/run_execution の起動時に呼び出し、監視用テーブルの存在を保障（冪等）。

Fixed
- 環境変数パーサの堅牢化:
  - _parse_env_line が export プレフィックス、クォート中のエスケープ、インラインコメント等に対応。自動ロード時に OS 環境変数を保護する仕組みを追加。

Security
- OpenAI API キーと各種シークレットは環境変数を通じて取得する設計。API キー未設定時は明確なエラーを出す。

---

注意事項 / 既知の問題
- ai/news_nlp.py の score_news 関数の途中でコードが切れている（スニペット終端が不完全）。実際に動作させる前に残りのロジック（記事集約取得関数、API 呼び出しループ、DB 書き込み部分）の実装・テストが必要。
- position_sizing.apply_sector_cap における価格欠損（price が 0.0）時の挙動について TODO コメントあり。現在は価格が欠損している銘柄が過小評価される可能性があるため、将来的にフォールバック価格（前日終値等）を導入する予定。
- run_monitoring は「環境にかかわらず本番 sqlite_path を使用する」仕様となっているため、開発/テスト環境で誤って本番 DB を参照しないよう運用上の注意が必要。
- set_process_priority / set_cpu_affinity は権限によっては設定に失敗する（AccessDenied 等）。その場合は警告でスキップする設計のため、期待通りの優先度が設定されない可能性がある。
- research モジュールは DuckDB のスキーマ（prices_daily, raw_financials 等）前提のため、実データ投入・スキーマ準備が必須。

ライセンス・貢献
- 本 CHANGELOG はソースコードの現状から推測して生成したものであり、実際のコミット履歴とは差異があり得ます。リリースノート化する際は git の履歴・著者情報を元に調整してください。
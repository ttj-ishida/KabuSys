# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

フォーマット:
- Unreleased: 将来の変更（現在は空または注記）
- 各リリース: 追加（Added）、変更（Changed）、修正（Fixed）、削除（Removed）、セキュリティ（Security）等のカテゴリで記載

## [Unreleased]
- 特になし（初期リリース相当の状態）

## [0.1.0] - 2026-04-13
初回公開リリース。KabuSys のコア機能（実行、監視、ポートフォリオ構築、リサーチ、ニュースNLP、ユーティリティ類）を実装。

### Added
- 実行エンジン起動スクリプト
  - run_execution.py を追加。ExecutionEngine の起動ロジックを実装。
  - BrokerClientFactory により本番/ペーパー（paper_trading）環境で適切なブローカークライアントを生成。
  - paper_trading 環境では専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
  - RiskManager / OrderManager / Reconciler を組み合わせてセッションを実行。

- 監視ループ起動スクリプト
  - run_monitoring.py を追加。SystemMonitor をポーリングで実行するメインループを提供。
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の挙動を明記。

- 設定管理
  - config.py を追加。.env ファイルの自動ロード（.env → .env.local の順、OS 環境変数を保護）を実装。
  - .env パーサに対応:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - クォートなしの行でのインラインコメント処理（直前がスペース/タブのみ）
  - Settings クラスを提供し、各種環境変数（J-Quants / kabuAPI / DB パス / 監視閾値 / env 判定 等）をプロパティ経由で取得・バリデーション。

- ポートフォリオ構築
  - portfolio モジュールを追加（pure functions、DB 参照なし）。
  - 候補選定: select_candidates（スコア降順、同点は signal_rank でブレーク）。
  - 重み計算: calc_equal_weights, calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - リスク調整: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに応じた乗数）。
  - ポジションサイズ: calc_position_sizes（risk_based / equal / score 対応、lot 単位丸め、aggregate cap スケールダウン、cost_buffer を考慮）。

- リサーチ / ファクター計算
  - research モジュールを追加。
  - factor_research: calc_momentum, calc_volatility, calc_value — DuckDB の prices_daily/raw_financials を用いたファクター計算を実装。
  - feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）、factor_summary, rank — パフォーマンス注意点と入力バリデーションを実装。
  - DuckDB 接続を受け、外部 API に依存しない設計。

- ニュース NLP（AI スコアリング）
  - ai/news_nlp.py を追加。raw_news と news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込み。
  - スコアリングの設計:
    - ジャパン時間ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）
    - 1 銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - バッチサイズ制御（最大 20 銘柄/コール）
    - 429/タイムアウト/5xx に対する指数バックオフリトライ
    - レスポンスバリデーションと ±1.0 でのクリップ
    - OpenAI API キーの引数/環境変数による指定（未設定の場合は ValueError）

- ツール
  - tools/paper_verification_report.py を追加。Paper Trading DB を解析して稼働率、注文成功率、送信率、レイテンシ等の検証レポートを生成。閾値を定義して PASS/FAIL 判定を出力。
  - CLI 引数 --from / --to / --db サポート、DB 存在チェック、テーブル未存在時のフォールバック処理を実装。

- ユーティリティ
  - utils/process_priority.py を追加。プラットフォーム差分を吸収してプロセス優先度設定（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値）と CPU affinity 固定機能を提供。アクセス権限不足や未対応 OS の場合は警告を出してスキップ。

- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を設定し、主要モジュールを __all__ で公開。

### Changed
- DB 周りの挙動明確化
  - 監視プロセスは環境に依存せず本番 sqlite_path を使用（安全性/運用上の意図に合わせた仕様）。
  - Paper Trading 実行は paper_sqlite_path を使用して本番 DB と分離。

- ロギング・堅牢性
  - 各種モジュールで logging を利用し、デバッグ/情報/警告を適切に出力。
  - 実行ループや API 呼び出しで例外発生時にログを残して次サイクルへ継続するフェイルセーフを導入。

### Fixed
- .env パースの頑強化
  - クォート内のエスケープや export プレフィックス、インラインコメントの取り扱い不備を修正。
- weight 計算のフォールバック
  - calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックして警告を出すように修正。
- position sizing のスケールダウン
  - aggregate cap 超過時のスケーリング処理で lot_size 単位での端数処理と残余キャッシュを考慮する実装を追加（整数丸めによる公平性向上）。

### Removed
- なし

### Security
- OpenAI API キーなど機密情報は Settings / 環境変数で管理。自動 .env ロードは OS 環境変数を protected として上書きを防止。

---

注記（設計上の重要点 / 既知の注意事項）
- 必須環境変数が未設定の場合、Settings のプロパティアクセスは ValueError を送出します（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
- MONITOR_POLL_INTERVAL に 0 以下や数値以外を指定するとデフォルト 60 秒にフォールバックし、警告ログを出力します。
- process_priority の設定はプラットフォーム/権限によって失敗することがあり、その場合は警告を出してスキップします。
- ニュース NLP の処理は OpenAI API に依存するため、API 利用料やレート制限に注意してください。
- DuckDB を用いたファクター計算・リサーチ関数は外部ライブラリ（pandas 等）に依存しない設計ですが、DuckDB 側のテーブル（prices_daily, raw_financials 等）が所定のスキーマで存在することが前提です。

もし CHANGELOG の粒度（リリース日付、カテゴリ分け、さらに古いバージョン履歴の推定など）を調整したい場合は、希望するフォーマットや想定リリース日を教えてください。コードから推測して追加・修正できます。
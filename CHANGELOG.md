# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

全般的な注記:
- 初期リリースではデータ収集（J-Quants / RSS）、DuckDB スキーマ、研究用ファクター計算、環境設定ユーティリティなどの基盤機能を実装しています。
- ロギングや入力検証、冪等性・エラー耐性（リトライ・トランザクション巻き戻し等）に配慮した設計です。

## [Unreleased]

- 今後の予定: モニタリング・実行（kabuステーション連携）実装、追加の特徴量・戦略モジュール、テストカバレッジの拡充。

## [0.1.0] - 2026-03-18

Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にバージョン "0.1.0" と公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数読み込みユーティリティ（kabusys.config）
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み。
    - .env パースロジックは export 形式、クォートやインラインコメント、エスケープ等に対応。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスで J-Quants / kabu API / Slack / DB パス等のプロパティを提供。必須設定は未設定時に ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の検証（有効値チェック）、is_live/is_paper/is_dev ヘルパーを実装。
- データ取得・保存（J-Quants）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - API レート制御（固定間隔スロットリング）を実装（120 req/min 相当）。
    - HTTP リクエストに対するリトライ（指数バックオフ、最大 3 回）、429 の Retry-After 優先処理、408/429/5xx の再試行対応。
    - 401 発生時にリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ。
    - ページネーション対応を実装（pagination_key の処理）。
    - 取得データを DuckDB に冪等的に保存する save_* 関数（raw_prices/raw_financials/market_calendar）を実装。INSERT ... ON CONFLICT で重複更新。
    - 数値変換ユーティリティ _to_float / _to_int を実装し、不正値や空文字に対して安全に None を返す。
- ニュース収集（RSS）
  - RSS ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィードの取得・パース（defusedxml を利用）と記事整形を実装。デフォルトソースに Yahoo Finance を追加。
    - URL 正規化（トラッキングパラメータ削除、ソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 先頭32文字）を実装して冪等性を保証。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームと最終ホストのプライベートアドレス判定を行うカスタム RedirectHandler を導入。
      - ホスト名の DNS 解決後にプライベート/ループバック/リンクローカル/マルチキャストを拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ確認（Gzip bomb 対策）。
    - XML パース失敗時は警告ログを出し空リストを返す堅牢な振る舞い。
    - raw_news テーブルへの一括保存（チャンク分割、トランザクション、INSERT ... RETURNING による新規挿入ID取得）と、news_symbols への紐付け保存機能を実装。重複排除・トランザクション管理を行う。
    - 記事本文の前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、既知コードフィルタ）を実装。
    - run_news_collection により複数ソースの収集を独立して実行・集計。
- DuckDB スキーマ
  - スキーマ初期化定義（kabusys.data.schema）
    - Raw 層のテーブル定義（raw_prices, raw_financials, raw_news, raw_executions の DDL を定義）。
    - 各テーブルに型チェック・制約（NOT NULL / CHECK / PRIMARY KEY）や fetched_at タイムスタンプを含む設計。
- 研究（Research）モジュール
  - feature_exploration（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL による LEAD 利用）。
    - Information Coefficient（IC）計算 calc_ic（スピアマンの ρ をランク換算で実装、データ不足時は None を返す）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸め処理で ties 検出対策）。
    - ファクター統計 summary を計算する factor_summary（count/mean/std/min/max/median）。
    - feature_exploration は標準ライブラリのみで実装（pandas 等非依存）。
  - factor_research（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を計算する calc_momentum。200日移動平均の必要行数チェックを実装。
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）を計算する calc_volatility。true_range の NULL 伝播制御やカウント判定を実装。
    - Value（per, roe）を計算する calc_value。raw_financials から最新の target_date 以前の開示を取得して price と組み合わせる。
  - 研究モジュールのエクスポート（kabusys.research.__init__）で主要ユーティリティを公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- 設計上の注意点（ドキュメント・ログ）
  - Look-ahead bias を避けるため fetched_at を UTC で記録する方針。
  - API 呼び出しや RSS 取得時に詳細なログ（info/warning/exception）を出力する実装。

Security
- RSS モジュールで SSRF 対策（スキーム検証、プライベート IP フィルタ、リダイレクト検査）を導入。
- defusedxml を利用して XML 関連の攻撃を軽減。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated / Removed
- 初期リリースのため該当なし。

Upgrade / Migration notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須とされます。未設定の場合は ValueError が発生します。
- 自動 .env ロードはデフォルトで有効です。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ定義は schema モジュール内の DDL に従います。既存 DB を変更する場合はバックアップを推奨します。

問い合わせ / 貢献
- バグや改善提案があれば issue を作成してください。今後、発注・モニタリング・戦略実行部の実装を優先して進める予定です。
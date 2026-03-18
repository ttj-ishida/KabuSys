# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本リポジトリの初期バージョンは v0.1.0 としてリリースされています。

## [0.1.0] - 2026-03-18
Initial release

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__、バージョン "0.1.0"）。
  - モジュール分割: data, strategy, execution, monitoring（空の __init__ を含む）を準備。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル／環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して見つけたルートの .env/.env.local を読み込む。
    - 読み込み優先順は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env 読み込み時にファイルが読めない場合は警告を出力。
  - .env パーサーは export KEY=val 形式、クォート、インラインコメント、エスケープをサポート。
  - 必須設定取得用の _require を実装（未設定時は ValueError を送出）。
  - 各種設定プロパティを提供:
    - J-Quants / kabu API / Slack トークンやチャネル、DB パス（duckdb/sqlite）、環境（development/paper_trading/live）、ログレベルの検証機能など。
  - 設定値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の限定値チェック）を導入。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（認証、ページネーション、取得関数、保存関数）。
  - レート制限対応（固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装）。
  - リトライロジック（最大 3 回、指数バックオフ）を実装。対象はネットワークエラーや特定の HTTP ステータス（408/429/5xx）。
  - 401 Unauthorized 受信時は自動でトークンをリフレッシュして 1 回だけリトライする仕組みを実装（無限再帰防止のため get_id_token 呼び出し時は allow_refresh=False）。
  - fetch_* 系関数により日次株価（fetch_daily_quotes）、財務情報（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）をページネーション対応で取得。
  - DuckDB への保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - fetched_at に UTC タイムスタンプを付与。
    - PK 欠損行はスキップして警告を出力。
    - 冪等性を考慮して INSERT ... ON CONFLICT DO UPDATE を使用。
  - ユーティリティ関数 _to_float / _to_int を実装し、安全な型変換を行う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集し raw_news / news_symbols に保存するモジュールを実装。
  - セキュリティ対策:
    - defusedxml による XML パースで XML Bomb 等に対策。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前検査、プライベートアドレス判定（IP/ホスト名の DNS 解決で A/AAAA をチェック）により内部アドレスアクセスを拒否。
    - リダイレクト時に _SSRFBlockRedirectHandler でスキーム/ホスト検査を実施。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後サイズ検査（Gzip bomb 対策）。
  - URL 正規化（utm_* 等トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント削除）を実装し、正規化 URL の SHA-256（先頭32文字）で記事 ID を生成。
  - テキスト前処理: URL 除去・空白正規化を行う preprocess_text を提供。
  - RSS パース:
    - fetch_rss で RSS を取得し、content:encoded があれば description より優先して採用。
    - pubDate のパース（RFC 2822）と UTC への正規化（失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news はチャンク化して一括 INSERT を行い、INSERT ... RETURNING id により実際に挿入された記事 ID を返す。トランザクションを用いてロールバック可能。
    - save_news_symbols / _save_news_symbols_bulk により (news_id, code) ペアを一括保存。INSERT ... RETURNING を使用して実際の挿入件数を返す。
  - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes によるフィルタリング（重複除去）を行う extract_stock_codes を実装。
  - デフォルト RSS ソース定義（例: Yahoo Finance のカテゴリフィード）を提供。
  - run_news_collection により複数ソースから独立して収集と保存を実行し、各ソースごとの成功件数を返す。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を想定したスキーマ準備モジュールを追加。
  - raw_prices / raw_financials / raw_news / raw_executions 等の DDL を用意（raw_executions は一部がファイル内に含まれる）。
  - 各テーブルに適切な型・チェック制約・PRIMARY KEY を付与。

- 研究（research）モジュール（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev を DuckDB の prices_daily を参照して計算。データ不足時は None を返す。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials の最新財務データと当日の株価から PER / ROE を計算。
    - 各関数は DuckDB 上で SQL ウィンドウ関数を活用し効率的に集計。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 指定日から翌日/翌週/翌月（デフォルト 1/5/21 営業日）までの将来リターンを一度のクエリで計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。レコード不足（<3）や分散ゼロ時は None を返す。
    - rank: 同順位は平均ランクで扱う安定したランク関数（丸め誤差対策あり）。
    - factor_summary: 各カラムについて count/mean/std/min/max/median を計算（None を除外）。
  - 研究用ユーティリティを kabusys.research.__init__ でエクスポート（calc_momentum/calc_volatility/calc_value/calc_forward_returns/calc_ic/factor_summary/rank と zscore_normalize を連携）。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- ニュース収集での SSRF、XML インジェクション、レスポンスサイズ攻撃（DoS）などを考慮した安全対策を導入。
- J-Quants API クライアントでトークン管理と自動リフレッシュの実装により、認証失敗時の安全な回復をサポート。

---

今後の予定（未実装 / 想定ワーク）
- schema の残りテーブル・インデックス・ユーティリティの完成。
- strategy / execution / monitoring モジュールの実装（発注ロジック、ポジション管理、監視・アラート）。
- 単体テスト・統合テストの充実（特にネットワーク・DB 周りのモックを使ったテスト）。
- パフォーマンス最適化（大規模データでのクエリチューニング、バルク処理の改善）。
- ドキュメント（Usage / Deployment / DataSchema / StrategyModel）の整備。
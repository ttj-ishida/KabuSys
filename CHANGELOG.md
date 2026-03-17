CHANGELOG
=========

すべての重要な変更は Keep a Changelog の規約に従って記載しています。  
（注）以下は提示されたコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴ではありません。

Unreleased
----------
- 既知の問題 / 今後対応予定（コードから推測）
  - run_prices_etl の戻り値が仕様どおり (fetched_count, saved_count) になっていない（現在は fetched のみを返す形になっている）。ETL の呼び出し側が期待する戻り値と不整合になる可能性があるため修正予定。
  - strategy/execution パッケージの __init__.py が空であり、戦略・発注ロジックの実装が未完了（プレースホルダ）。
  - pipeline モジュールは差分取得や品質チェックの設計を含むがファイル末尾が途中で切れており、完全実装は要確認。
  - 単体テスト・統合テストの存在は確認できず、ネットワーク周りや DB 周りのエラーケースを網羅するテスト追加が望ましい。

[0.1.0] - 2026-03-17
--------------------
Added
- パッケージ基盤
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env / .env.local または OS 環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルート特定は .git または pyproject.toml を探索する。
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）に対応。
  - .env パーサを実装（コメント、export プレフィックス、クォートとエスケープ、インラインコメント処理をサポート）。
  - 環境変数取得用 Settings クラスを追加。J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live） / ログレベルの検証を行うプロパティを提供。
  - 必須変数未設定時は明示的なエラーを投げる _require() を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API へアクセスするクライアントを実装。
  - レート制限対策: 固定間隔スロットリングを行う _RateLimiter（120 req/min 相当）。
  - 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE を使って重複を排除。
  - リトライ戦略: 指数バックオフ、最大 3 回、408/429/5xx を対象に再試行。
  - 401 Unauthorized 受信時はリフレッシュトークンから id_token を自動更新して 1 回だけリトライする仕組みを実装（トークンキャッシュあり）。
  - ページネーション対応で日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）を取得。
  - DuckDB へ保存する save_daily_quotes / save_financial_statements / save_market_calendar を実装。取得時刻（fetched_at）を UTC で記録。
  - 型安全な数値変換ユーティリティ (_to_float / _to_int) を提供。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して raw_news に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML Bomb 等に対処。
    - SSRF を防ぐため、URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定、リダイレクト先の検査を実装（カスタム RedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリ DoS を防止。gzip 解凍後もサイズチェック。
  - 冪等性・ID 管理:
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し、トラッキングパラメータの除去やクエリソートを行う正規化関数を実装。
  - 前処理・抽出:
    - 本文・タイトルの URL 除去、空白正規化を行う preprocess_text を実装。
    - テキスト中から 4 桁の銘柄コードを抽出する extract_stock_codes を実装（既知銘柄セットでフィルタ）。
  - DB 保存:
    - raw_news に対するチャンクインサート（INSERT ... ON CONFLICT DO NOTHING RETURNING id）を実装し、実際に挿入された記事 ID のリストを返す save_raw_news。
    - news_symbols（記事と銘柄の紐付け）をチャンク挿入で保存する save_news_symbols / _save_news_symbols_bulk。トランザクション管理とロールバックを適切に行う。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema.md に基づく DuckDB のスキーマ定義と初期化関数を実装。
  - Raw / Processed / Feature / Execution の多層テーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）。
  - 頻出クエリ向けのインデックスを作成する定義を用意。
  - init_schema(db_path) でディレクトリ作成・DDL 実行を行い、get_connection(db_path) で接続取得を提供。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL の設計に基づくパイプライン基盤を実装（差分取得、保存、品質チェックのフック）。
  - ETL 実行結果を表す dataclass ETLResult を追加（品質問題とエラーの集約、シリアライズ用 to_dict）。
  - テーブル存在チェック・最大日付取得ヘルパーを実装。
  - 市場カレンダーを考慮した営業日調整ヘルパー _adjust_to_trading_day を実装。
  - 差分更新用ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）を追加。
  - run_prices_etl を部分実装（差分判定 → fetch_daily_quotes → save_daily_quotes → ログ）。※実装末尾に戻り値関連の不整合が見られる（上記「Unreleased」に記載）。

Security
- ネットワーク/データ処理に対するセーフガードを多く盛り込んでいる点を明記：
  - XML パースで defusedxml を使用。
  - URL スキーム検証・プライベートホスト検査で SSRF を低減。
  - HTTP レスポンスサイズ上限と gzip 解凍後のチェックでメモリ攻撃対策。
  - .env パース周りでファイル読み込み失敗時に警告を出すなど堅牢性を考慮。

Performance / Reliability
- API レート制限のための固定間隔スロットリングを導入（120 req/min）。
- 冪等性を重視した DB 保存（ON CONFLICT DO UPDATE / DO NOTHING）を採用。
- ページネーションやトークンキャッシュを利用し長いデータ取得ジョブに対応。
- バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）とトランザクション集約で DB オーバーヘッドを低減。

Notes（推測）
- strategy/ execution / monitoring の具体的な戦略ロジック・発注連携・監視機能は未実装のプレースホルダが見られるため、今後の主要実装対象。
- run_news_collection は複数ソースを独立して処理し、1 ソース失敗でも他ソースを継続する堅牢な設計になっている。
- DB モデルは埋め込み・運用両方を想定（ファイルベースの DuckDB と :memory: をサポート）。

ライセンスやリリースポリシー、実際のコミットログの詳細はこのファイルからは判別できません。実運用に移す前に以下を推奨します：
- run_prices_etl の戻り値不整合を修正し、パイプラインの完全実装とテストを追加する。
- strategy / execution の具体実装とそれらを統合した E2E テストを整備する。
- ネットワークや DB 周りのフェイルオーバー、リトライ動作を CI で検証する。
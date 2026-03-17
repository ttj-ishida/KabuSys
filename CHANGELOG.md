CHANGELOG
=========

すべての注目すべき変更点はここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-17
--------------------

初回公開リリース。日本株自動売買フレームワーク「KabuSys」のコア機能を実装しました。主な追加内容は以下のとおりです。

Added
- パッケージ骨格
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring をエクスポート。
  - バージョン番号を `__version__ = "0.1.0"` に設定。

- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数の自動読み込みを実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効化するため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をサポート。
  - .env パーサを実装（コメント行、export 形式、クォート内のエスケープ、インラインコメントの扱いに対応）。
  - OS 環境変数の保護（既存キー一覧を protected として .env の上書きを制御）。
  - 必須環境変数取得用の _require と、各種設定プロパティ（J-Quants / kabu / Slack / DB パス / ログレベル / env 判定）を追加。
  - 有効値チェック（KABUSYS_ENV: development/paper_trading/live、LOG_LEVEL の妥当性検証）。

- J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API との通信クライアントを実装。取得対象に日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーを含む。
  - レート制御（固定間隔スロットリング）: デフォルト 120 req/min を厳守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ（最大 3 回）、408/429/5xx に対するリトライ、429 の場合は Retry-After を優先。
  - 認証トークン処理: id_token のモジュール内キャッシュ、401 受信時は自動的に一度だけリフレッシュして再試行する仕組み。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により重複を排除。
  - 取得時刻（fetched_at）を UTC ISO8601 形式で保存し、Look-ahead Bias のトレースをサポート。
  - 数値変換ユーティリティ（_to_float, _to_int）を実装。文字列・空値・浮動小数点文字列の扱いについて明確化。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得して DuckDB に保存するパイプラインを実装（raw_news, news_symbols との連携を想定）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: リダイレクト時にスキームとホストの事前検証を行うカスタム RedirectHandler（プライベートIP/ループバック/リンクローカル/マルチキャストの拒否）。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を実装し、読み込み時に超過した場合はスキップ。gzip 解凍後のサイズも検査。
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去してクエリをソート、フラグメント除去。
    - 正規化 URL の SHA-256 を用い、先頭32文字を記事IDとして冪等性を確保。
  - テキスト前処理（URL除去、空白正規化）。
  - DB 保存の実装:
    - INSERT ... RETURNING を使い、実際に挿入された新規記事IDを返す save_raw_news。
    - news_symbols への紐付けをチャンク単位で一括 INSERT（ON CONFLICT DO NOTHING）する内部関数と公開 API を実装。
    - トランザクション管理（一括挿入は 1 トランザクションにまとめ、失敗時はロールバック）。
  - RSS のパースとフォールバックロジック（channel/item がない場合の探索）と公的なデフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を追加。
  - 銘柄コード抽出ロジック（4桁数字パターン、known_codes によるフィルタ、重複除去）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層＋実行レイヤーのテーブル群を定義。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等。
  - 各テーブルに適切な制約（PRIMARY KEY, FOREIGN KEY, CHECK 等）を設定。
  - 頻出クエリ向けのインデックスを定義（例: code×date、status 検索等）。
  - init_schema(db_path) によりディレクトリ作成（必要なら）→テーブル/インデックス作成を行うユーティリティを追加。get_connection も提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計方針と差分更新ロジックを実装するためのユーティリティ群を追加。
  - ETLResult データクラスを実装（取得件数・保存件数、品質チェック結果・エラー一覧を保持、dict に変換可能）。
  - 差分更新ヘルパー（テーブル存在チェック、最大日付取得）と市場カレンダー補正機能（非営業日の調整）を追加。
  - run_prices_etl の骨格を実装（差分算出、backfill_days の扱い、jquants_client からの取得と保存呼び出し）。品質チェックフック（quality モジュール）への参照を含む（品質チェックは継続実行方針）。

Changed
- （このリリースは初回公開のため、既存変更点はなし）

Fixed
- （初回公開）

Security
- defusedxml を使用した XML パースによる XML 関連攻撃の緩和（news_collector）。
- SSRF 対策としてリダイレクト時の検証、ホストのプライベートアドレス判定、許可スキーム制限。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入。

Notes / Implementation details
- J-Quants API のレート制限は固定間隔スロットリングで実装しており、短期間に複数スレッドから呼ばれる場合はモジュール単位での調整が必要です（現実運用ではプロセス単位の共有や分散制御が検討される）。
- news_collector の RSS 取得は fetch_rss -> save_raw_news -> news_symbols の流れで行い、known_codes を渡すことで記事と銘柄の紐付けを行います。
- DuckDB の INSERT 文ではプレースホルダを文字列結合して使用している箇所があり（大量行の一括挿入のため）、SQL インジェクションを防ぐために渡す値は既に内部で値リスト化されていますが、外部入力を直接連結しないよう注意が必要です。
- 一部モジュール（strategy, execution, monitoring）の __init__ はプレースホルダであり、今後戦略実装・発注連携・監視機能が追加される予定です。
- pipeline.run_prices_etl の実装は途中まで（ファイル末尾が切れている）ですが、差分更新と保存の主要ロジックは含まれています。品質チェック（quality モジュール）との統合は想定されているが、quality の実装はこの差分からは確認できません。

既知の制限 / 今後の作業（提案）
- strategy / execution / monitoring 層の本格的な実装（シグナル生成、発注 API 連携、監視・アラート）。
- quality モジュールの実装（データ品質ルールの具現化と ETL への組み込み）。
- 分散環境や多プロセスからの J-Quants API 呼び出しを考慮したレート制御の強化（例えばプロセス間共有のための外部ミドルウェアや Redis を利用したトークンバケットの導入）。
- テストカバレッジ拡充（特に network / SSRF / XML パース / 大容量レスポンスの境界条件）。

----------------------------------------
参考: 本 CHANGELOG はリポジトリ内のコードコメント・関数名・ドキュメント文字列から実装意図を推測して作成しています。実際の変更履歴（コミット履歴）とは一致しない場合があります。
CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。
このプロジェクトはセマンティックバージョニングに従います。

Unreleased
----------

- なし（初回リリースに向けたスナップショット）

0.1.0 - 2026-03-17
------------------

Added
- 初期リリース。パッケージ名: kabusys（__version__ = 0.1.0）。
- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - .env ファイルパーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォートあり/なしの扱いの違い）に対応。
  - Settings クラスを公開し、J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供（必須キーの検査、enum風の検証を含む）。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得用の fetch_* 関数を実装（ページネーション対応）。
  - レート制御（固定間隔スロットリング）を実装して 120 req/min を遵守。
  - 自動リトライ（指数バックオフ、最大3回）、HTTP 408/429/5xx をリトライ対象に設定。
  - 401 受信時はリフレッシュトークンから id_token を再取得して1回だけリトライするロジックを実装。
  - 取得時刻（fetched_at）を UTC ISO 形式で記録し、Look-ahead bias 防止に配慮。
  - DuckDB への保存関数 save_* を実装（INSERT ... ON CONFLICT DO UPDATE により冪等保存）。
  - 型変換のユーティリティ（_to_float, _to_int）を実装し空値・不正値を安全に扱う。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得・パース・前処理・DuckDB への保存の一連処理を実装。
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃に対処。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）を設け、読み込みオーバー時はスキップ。
  - gzip 圧縮レスポンスの解凍対応（解凍後サイズチェック含む）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト先のスキーム・ホスト検証（内部アドレス拒否）
    - ホスト名の DNS 解決結果からプライベートIPを検出して拒否
  - 記事ID生成: URL 正規化後の SHA-256（先頭32文字）で冪等性を確保（utm_* 等のトラッキングパラメータを除去）。
  - テキスト前処理（URL除去・空白正規化）を提供。
  - raw_news へのバルク挿入は INSERT ... RETURNING を用い、1 トランザクション・チャンク処理で実行。挿入された新規記事IDのリストを返す。
  - 記事と銘柄コードの紐付け（news_symbols）を一括保存する内部ユーティリティを実装。
  - 銘柄抽出ユーティリティ extract_stock_codes（4桁数字の候補検出と known_codes によるフィルタリング）を実装。
  - run_news_collection により複数ソースの収集をまとめて実行（ソース単位で独立したエラーハンドリング）。
- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の多層テーブル群を DDL で定義。
  - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance などのテーブルを含む。
  - 頻出クエリ向けのインデックス（例: idx_prices_daily_code_date, idx_signal_queue_status 等）を作成。
  - init_schema(db_path) により親ディレクトリを自動作成してスキーマを初期化するユーティリティを提供。get_connection も実装。
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新ロジック、最終取得日の判定ヘルパー、カレンダ調整、個別 ETL ジョブ（run_prices_etl 等）の骨格を実装。
  - ETLResult データクラスにより ETL 実行結果・品質問題・エラーを集約可能。
  - 品質チェックモジュール（quality）との連携を想定した設計（重大度レベル判定）。
  - 市場カレンダーの先読みやバックフィル（日数パラメータ）に対応する設計。

Changed
- N/A（初回リリースのため変更履歴はなし）

Fixed
- N/A（初回リリースのため過去の修正履歴はなし）

Security
- defusedxml を使用した安全な XML パースを導入（news_collector）。
- RSS フェッチに関する SSRF 対策（スキーム検証、リダイレクト時のホスト検査、プライベートIP拒否）。
- レスポンスサイズ上限や gzip 解凍後のサイズチェックを導入しメモリ DoS を軽減。
- .env 読み込みでは OS 環境変数を保護（override 制御と protected キー）する仕組みを用意。

Deprecated
- なし

Removed
- なし

Notes / Known issues
- run_prices_etl の末尾が不完全（現状のソースは "return len(records), " といった形でタプルの返却が途切れており、実行時に構文的/論理的エラーが発生する可能性があります）。この箇所は後続のコミットで修正が必要です。
- NewsCollector の DNS 解決でエラーが発生した場合は安全側で「非プライベート」と見なして通過させる実装になっています。環境によってはより厳密なポリシーが必要な場合があります。
- J-Quants クライアントは内部で id_token のキャッシュと自動リフレッシュを行います。テスト時は id_token を注入して副作用を抑制可能です。

Contributors
- コードベースからの推測に基づき記載（個別コントリビュータ名はソースに含まれていないため省略）。

ライセンス
- ソースにライセンス表記がないため、ライセンスはプロジェクトルートの定義に従ってください。

---- 

この CHANGELOG はソースコードの内容から推測して作成しています。必要があれば、実際の Git コミット履歴やリリース計画に合わせて日付・内容を調整してください。
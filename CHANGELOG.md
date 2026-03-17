CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

[Unreleased]
------------

なし

0.1.0 - 2026-03-17
------------------

初回リリース。日本株自動売買プラットフォーム "KabuSys" のコア機能とデータ基盤の初期実装を追加。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化情報（kabusys.__init__、バージョン 0.1.0、公開モジュール一覧）。
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local からの自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
  - .env 行パーサ（export 構文、クォート内エスケープ、インラインコメント考慮）。
  - OS 環境変数を保護する protected オプション（.env.local は上書き可能）。
  - 必須変数取得ヘルパー _require()、環境値検証（KABUSYS_ENV, LOG_LEVEL）、利便性プロパティ（is_live, is_paper, is_dev）。
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等。
- J-Quants データクライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API 用クライアントを実装：株価日足、財務データ、マーケットカレンダーの取得関数を提供。
  - レート制限管理（固定間隔スロットリング、デフォルト 120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 Unauthorized 受信時の id_token 自動リフレッシュ（1 回のみ）とキャッシュ共有。
  - ページネーション対応（pagination_key を追跡）。
  - DuckDB へ保存する冪等な save_* 関数（ON CONFLICT DO UPDATE を使用）を実装。
  - 型変換ユーティリティ (_to_float, _to_int) を追加。
- RSS ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得・パース、記事前処理、DuckDB への保存を行うニュースコレクタを実装。
  - 記事IDは URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を担保。
  - URL 正規化でトラッキングパラメータ（utm_ 等）を除去・クエリをソート・フラグメント削除。
  - defusedxml を使用して XML Bomb 等の攻撃を防止。
  - SSRF 対策: リダイレクト毎のスキーム/ホスト検証、プライベートアドレス判定、許可スキームは http/https のみ。
  - レスポンス上限サイズ（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策、gzip 解凍後サイズ検査（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB へのバルク挿入はチャンク化（_INSERT_CHUNK_SIZE）してトランザクションで実行、INSERT ... RETURNING で実挿入件数を取得。
  - 銘柄コード抽出（4桁数字、known_codes による検証）と news_symbols への紐付け機能。
  - run_news_collection により複数ソースの統合収集を実行（ソース単位でエラーを隔離）。
- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義を追加（raw_prices, raw_financials, raw_news, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, 等）。
  - 各テーブルの制約（PRIMARY KEY、CHECK、外部キー）を定義。
  - 一連のインデックスを定義（頻出クエリパターン向け）。
  - init_schema(db_path) でディレクトリ作成・DDL 実行を行い DuckDB 接続を返す（冪等）。
  - get_connection(db_path) により既存 DB へ接続。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL 実行結果を格納するデータクラス ETLResult を実装（品質問題・エラーログを格納、辞書化メソッドあり）。
  - 差分取得ヘルパー（最終取得日の取得 get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 市場カレンダーに基づき非営業日を直近営業日に調整する _adjust_to_trading_day。
  - run_prices_etl による差分 ETL ロジック（最終取得日 - backfill_days を用いた再取得、デフォルト backfill_days=3、取得→保存のフロー）を実装。
  - テスト容易性のため、id_token を注入可能な設計。

### セキュリティ (Security)
- RSS パーサに defusedxml を採用し XML パース攻撃を軽減。
- RSS フェッチでの SSRF 対策を複数層で実施（初期ホスト検査、リダイレクト時検査、プライベートアドレス拒否）。
- HTTP レスポンスサイズ上限と gzip 解凍後のサイズチェックによりメモリ攻撃（DoS/Gzip bomb）を防止。
- .env パーサでのサニタイズ（引用符・エスケープ、コメント処理）により設定注入の危険を低減。

### 改善 / 設計上の注記 (Notes)
- jquants_client はレート制限とリトライ・トークン自動リフレッシュを組み合わせた堅牢な API 呼び出しを実装。
- DB への保存処理は可能な限り冪等（ON CONFLICT）に設計し、再実行や差分更新に耐えるようにしている。
- ニュース記事の id は URL の正規化→ハッシュ化を用いるため、トラッキングパラメータや URL の順序差異による重複を防止。
- テスト用フック（例: news_collector._urlopen のモック差し替え、pipeline/jquants の id_token 注入等）を用意している。

### 既知の問題 / 要確認 (Known issues / TODO)
- run_prices_etl 関数の戻り値処理（保存件数を返す箇所）の最終行が不完全に見える箇所があり、戻り値の一貫性（取得件数と保存件数のタプル）を確認する必要がある（コード断片の一部切り出しによる可能性あり）。実稼働前にユニットテストで ETL の戻り値と副作用（DB への保存）を検証してください。
- 初期バージョンのため、運用時に観察された細かいエラーハンドリングやログ粒度の調整、監視・アラート設計は今後改善予定。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）

ライセンスや貢献方法、運用手順等は別ドキュメント（README / DataPlatform.md / DataSchema.md 等）を参照してください。
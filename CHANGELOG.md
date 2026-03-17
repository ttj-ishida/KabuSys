# Changelog

すべての重要な変更は Keep a Changelog の仕様に従って記載しています。  
このファイルはプロジェクトのリリース履歴を日本語でまとめたものです。

全般:
- バージョンはパッケージメタデータに従い現時点で `0.1.0` としています（src/kabusys/__init__.py の __version__）。
- 初期リリースとして、データ取得・保存、RSS ニュース収集、環境設定管理、ETL パイプライン、DuckDB スキーマ等の基礎機能を実装しました。

## [Unreleased]
（次回以降の変更をここに記載します）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システムのコア基盤を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。優先順位は OS 環境 > .env.local > .env。
  - プロジェクトルート検出（.git または pyproject.toml）により、CWD に依存しない自動ロードを実現。
  - .env パーサーの実装:
    - export プレフィックス対応、クォート文字とバックスラッシュエスケープの処理、インラインコメント取り扱いなどをサポート。
    - 不正行は無視する堅牢なパーサー実装。
  - 上書き制御（override）と保護キー（protected）機能により、OS 環境変数を保護して .env の上書きを制御。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加（テスト向け）。
  - Settings クラスを実装し、各種必須環境変数（J-Quants、kabuステーション、Slack 等）とパス/列挙値の検証ロジックを提供。
    - DUCKDB_PATH, SQLITE_PATH のデフォルトパス、KABUSYS_ENV / LOG_LEVEL の検証、 is_live / is_paper / is_dev ヘルパーを提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 基本クライアントを実装（ID トークン取得、データ取得、保存）。
  - レート制限制御（固定間隔スロットリング）を実装し、J-Quants のレート制限（120 req/min）を遵守。
  - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx 等を想定）を実装。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。ID トークンのモジュールレベルキャッシュを導入し、ページネーション中の共有をサポート。
  - ページネーション対応の取得関数を提供:
    - fetch_daily_quotes（株価日足、OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等に保存する関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes、save_financial_statements、save_market_calendar
  - 取得時刻（fetched_at）を UTC 文字列で記録し、Look-ahead bias の追跡性を確保。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値を安全にハンドリング。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事取得・前処理・DB 保存の一連のワークフローを実装。
  - セキュリティ対策/堅牢化:
    - defusedxml を使用して XML Bomb 等の攻撃を防止。
    - SSRF 対策: リダイレクトハンドラでスキームとホストを検査、プライベートアドレスへのアクセスを拒否。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンス受信サイズを上限（MAX_RESPONSE_BYTES = 10 MB）で制限しメモリ DoS を軽減。gzip 解凍後もサイズ検査。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url, _make_article_id）。記事IDは正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
  - テキスト前処理（URL 削除、空白正規化）を提供（preprocess_text）。
  - RSS パーシング/抽出: fetch_rss を実装。content:encoded を優先、pubDate を UTC naive にパース。
  - DuckDB への保存関数:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を利用し、新規挿入 ID を返す（チャンク分割、1 トランザクションで実行）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（RETURNING を用いて挿入数を正確に把握）。
  - 銘柄コード抽出ロジック（extract_stock_codes）を実装。4桁数字候補を抽出し、既知コード集合でフィルタリング（重複除去）。
  - 統合収集ジョブ run_news_collection を実装（各ソースは独立エラーハンドリング、既知銘柄との紐付けを一括処理）。

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - DataSchema.md に基づく3層（Raw / Processed / Feature）＋ Execution レイヤーのテーブル定義を実装。
  - 初期テーブル群（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）を定義。
  - 各テーブルに適切な型チェック、PRIMARY KEY、FOREIGN KEY を設定。
  - 頻出クエリ向けインデックスを定義（idx_prices_daily_code_date など）。
  - init_schema(db_path) によりディレクトリ自動作成と DDL 実行で初期化を行う API を提供。get_connection も提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う ETL の骨格を実装。
  - ETLResult データクラスを導入し、ETL 実行結果（取得数、保存数、品質問題、エラー等）を集約して返却可能に。
  - テーブル存在チェック、最終取得日取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - 市場カレンダーを使った非営業日調整ヘルパー（_adjust_to_trading_day）を実装（最大 30 日遡り）。
  - run_prices_etl を実装（差分更新ロジック、バックフィルの既定値 3 日、jquants_client を利用した取得と保存）。取得開始日の自動算出（最終取得日 - backfill_days + 1）や初回ロード時の最小日付（2017-01-01）を考慮。

### Performance
- バルク挿入のチャンク化（news_collector の _INSERT_CHUNK_SIZE、save_raw_news / _save_news_symbols_bulk）により SQL プレースホルダやメモリオーバーヘッドを制御。
- jquants_client のレートリミッタと ID トークンキャッシュにより外部 API 呼び出しを効率化。

### Security
- defusedxml、SSRF ガード、URL スキーム検証、受信サイズ制限など外部入力（RSS / HTTP）関連のセキュリティ対策を多数導入。
- .env 処理時に OS 環境変数を保護する設計（protected keys）を採用。

### Notes / Limitations
- strategy, execution, monitoring の各サブパッケージはパッケージ初期化で公開されているものの（__all__）、現時点のコードベースでは実装が最小限です（拡張予定）。
- 品質チェックモジュール（kabusys.data.quality）は参照されているが、ここに含まれる実装の詳細は別途実装・拡張が必要です。
- ETL の品質検査は pipeline 内で検出を集約しますが、重大な品質問題があっても ETL を継続する設計になっており、呼び出し側での運用判断が必要です。

---

今後の予定（非網羅）:
- strategy / execution 周りの具体的な売買ロジックと注文送信実装の追加。
- 監視・アラート（monitoring）機能の実装強化（Slack 通知など）。
- 品質チェック（quality）ルールの充実化と自動修復/アラート連携。
- 単体テスト・統合テストの整備、CI/CD パイプライン構築。

-----------------------------------------------------------------------------
参考: 主な公開関数・クラス
- kabusys.config.settings (Settings)
- kabusys.data.jquants_client:
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector:
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection, extract_stock_codes
- kabusys.data.schema:
  - init_schema, get_connection
- kabusys.data.pipeline:
  - ETLResult, run_prices_etl, get_last_price_date, get_last_financial_date, get_last_calendar_date

（必要であれば、各機能の使用例や API ドキュメントを別途作成します。）
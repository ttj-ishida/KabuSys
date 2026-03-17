CHANGELOG
=========

すべての重要な変更点をこのファイルで管理します。
このプロジェクトは Keep a Changelog の慣習に倣い、セマンティックバージョニングを使用します。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-----------

（なし）

[0.1.0] - 2026-03-17
-------------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムの基本モジュール群を追加。
  - パッケージ公開名: kabusys（__version__ = "0.1.0"）。
  - エントリポイント: data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env と .env.local からの自動読み込みを実装（プロジェクトルート判定は .git / pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env 行パーサ: export プレフィックス、クォート中のエスケープ、インラインコメント等の扱いに対応。
  - Settings クラスを提供し、J-Quants・kabuステーション・Slack・データベースパス・環境種別・ログレベル等をプロパティで取得・検証。
  - 必須環境変数未設定時は ValueError を送出する _require を提供。

- J-Quants クライアント（kabusys.data.jquants_client）
  - API から株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する機能を実装。
  - レート制限(120 req/min) を固定間隔スロットリングで守る _RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）を実装。429 の Retry-After を考慮。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライする仕組みを実装。
  - ページネーション対応（pagination_key）を実装。
  - DuckDB へ保存する際、ON CONFLICT DO UPDATE による冪等性を確保（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - 数値変換ユーティリティ (_to_float, _to_int) を実装し不正値を安全に扱う。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事抽出を行い raw_news テーブルへ保存する処理を実装。
  - セキュリティ対策:
    - defusedxml を用いて XML Bomb 等の攻撃を軽減。
    - HTTP リダイレクト先のスキーム検査とプライベートアドレス判定による SSRF 防止（_SSRFBlockRedirectHandler, _is_private_host）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限(MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後の上限チェック。
  - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）および記事 ID を SHA-256 の先頭32文字で生成。
  - テキスト前処理（URL除去・空白正規化）。
  - DuckDB へはチャンク化してトランザクションで INSERT ... RETURNING を用い新規挿入IDを正確に取得（save_raw_news）。
  - 記事と銘柄コードの紐付けを一括挿入する機能（_save_news_symbols_bulk, save_news_symbols）を実装。
  - 銘柄コード抽出ロジック（4桁数字の候補を known_codes と照合）を提供。

- スキーマ定義・初期化（kabusys.data.schema）
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等を定義。
  - features, ai_scores（Feature 層）や signals, signal_queue, orders, trades, positions, portfolio_performance（Execution 層）を定義。
  - インデックス定義と外部キー依存を考慮した作成順を実装。
  - init_schema(db_path) により必要な親ディレクトリの自動作成とテーブル作成を行い、DuckDB 接続を返す。get_connection() で既存 DB へ接続可能。

- ETL パイプライン基礎（kabusys.data.pipeline）
  - 差分更新の概念（最終取得日からの差分、デフォルトバックフィル3日）に基づく ETL 構成。
  - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS=90）、最小データ日付の定義。
  - ETL 実行結果を表す ETLResult dataclass（品質チェック結果・エラー集約等）。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日に調整するヘルパーを実装。
  - run_prices_etl を実装し fetch→save の差分 ETL を行う（jquants_client 経由）。

Performance / Reliability
- API 呼び出しに対してレート制御およびリトライを実装し、安定した取得を目指す。
- ニュース収集はチャンク化 / トランザクション / INSERT ... RETURNING を使い一貫性とパフォーマンスを両立。
- DuckDB 操作をまとめて行うことで IO オーバーヘッドを低減。

Security
- RSS パーシングに defusedxml を採用。
- SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）。
- .env の読み込みでは OS 環境変数を保護する仕組み（protected set）を導入。

Known Issues / Notes
- run_prices_etl の実装が本来の戻り値（(fetched_count, saved_count)）を期待する注釈に対して、ファイル末尾が途切れた状態で return 文が不完全（ソースの抜粋による不整合の可能性）。実行時に期待どおりのタプルが返らないため、呼び出し側の扱いに注意が必要。実装全体を確認して最後の return を (len(records), saved) のように修正することを推奨。
- フル機能のユニットテストはこのスナップショットには含まれていません。外部 API（J-Quants）やネットワーク依存部はモックしやすい設計にはなっていますが、実運用前に統合テストを推奨します。

開発者向けメモ
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます。
- jquants_client 内の ID トークンはモジュールレベルでキャッシュされるため、ページネーションを跨ぐ呼び出しでは意図的に同一トークンを共有します。テストでトークンを差し替える場合は get_id_token や _get_cached_token をモックしてください。
- news_collector のネットワークアクセスは _urlopen をモックすることで外部接続を防げます。

作者注: この CHANGELOG は提供されたソースコードから推測して作成したものであり、実際のリリースノートは開発履歴（コミットログ）やリリース時の決定事項に基づいて更新してください。
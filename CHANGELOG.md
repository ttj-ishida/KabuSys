CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

Unreleased
----------

（なし）

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ初版を追加（kabusys v0.1.0）。
- 設定管理モジュールを追加（kabusys.config）。
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート判定: .git / pyproject.toml）。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の行パーサを実装（export プレフィックス、クォート、インラインコメント対応）。
  - 設定値取得用 Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベルなど）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）。

- J-Quants API クライアントを追加（kabusys.data.jquants_client）。
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装。
  - 固定間隔のレート制御（120 req/min）を実装（内部 RateLimiter）。
  - 再試行（指数バックオフ、最大 3 回）を実装。対象は 408/429/5xx とネットワークエラー。
  - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ。
  - 取得日時（fetched_at）を UTC で記録し look-ahead bias を軽減。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保。
  - 型変換ユーティリティ（_to_float / _to_int）を実装し不正データを扱いやすく変換。

- ニュース収集モジュールを追加（kabusys.data.news_collector）。
  - RSS フィードから記事を取得して raw_news に保存する fetch_rss / save_raw_news を実装。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - defusedxml を利用した安全な XML パース（XML Bomb 等への対策）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト先のスキーム／ホストの事前検証（プライベートアドレス拒否）。
    - DNS 解決した A/AAAA の検査でプライベートIPを弾く。
  - レスポンス上限（MAX_RESPONSE_BYTES=10MB）を導入しメモリDoSを防止。gzip 解凍後のサイズチェックあり。
  - トラッキングパラメータの除去による URL 正規化と記事 ID の一貫性確保。
  - 銘柄コード抽出（4桁数字）と news_symbols への紐付け機能を実装。
  - DB 操作はチャンク分割＆トランザクション・INSERT ... RETURNING を用いた効率的な実装。

- データベーススキーマ定義モジュールを追加（kabusys.data.schema）。
  - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル定義を実装。
  - 制約（PK, FOREIGN KEY, CHECK）やインデックスを設計して頻出クエリに対応。
  - init_schema(db_path) により DuckDB の初期化（ディレクトリ自動作成、DDL 実行）を行う API を提供。
  - get_connection(db_path) で接続取得（スキーマ初期化は行わない）。

- ETL パイプライン基盤を追加（kabusys.data.pipeline）。
  - 差分更新ロジック、バックフィル設計（デフォルト backfill_days=3）、市場カレンダーの先読み等の設計を反映。
  - ETL 実行結果を格納する ETLResult データクラスを実装（品質問題やエラーの集約、シリアライズ用メソッド）。
  - raw_prices / raw_financials / market_calendar の最終取得日取得ユーティリティを実装。
  - run_prices_etl の骨組み（差分判定 → fetch → save）を実装。

Changed
- 初期リリースであり互換性の変更なし。

Security
- 外部通信に関する複数の安全対策を実装:
  - RSS 取得時の SSRF 対策（スキーム検査、プライベートIP検出、リダイレクト検査）。
  - XML パースに defusedxml を使用。
  - レスポンスサイズ制限と Gzip 解凍後の再チェック。
  - .env パースでのエスケープ処理に配慮。

Notes / Implementation details
- jquants_client:
  - レート制御はモジュールレベルの _RateLimiter（固定間隔）で実装。ページネーション中はトークンを共有するため ID トークンのキャッシュを利用。
  - 429 時は Retry-After ヘッダを優先して待機時間を決定。
- news_collector:
  - URL 正規化で utm_* など一般的なトラッキングパラメータを除去。
  - 記事テキストは URL を除去し空白を正規化してから銘柄抽出を行う。
- schema:
  - 多数の CHECK 制約・INDEX を含み、データ品質とクエリ性能を考慮した設計。

Known issues / TODO
- ETL パイプラインの実装は骨格が整っているものの、run_prices_etl の末尾が未完（ファイルの抜粋により return 文が不完全に見える）であり、現状のままでは構文エラーや動作未完の可能性があります。実運用前に pipeline の完全実装と単体テストを推奨します。
- ユニットテストや統合テストはこのリリースに含まれていません。ネットワーク呼び出しや DB 操作をモック化したテストを整備してください。
- 大量データ取得時のパフォーマンスやメモリ挙動の追加検証を推奨します（特に DuckDB へのバルク挿入や RSS のチャンク処理）。
- エラーハンドリングポリシー（品質問題の扱い、アラート送信など）は上位の運用要件に合わせて拡張してください。

Credits
- 初期実装: DataPlatform.md / DataSchema.md 等の設計指針に基づく。

ライセンス
- リポジトリに従う（ライセンスファイルがない場合は別途追加してください）。

--- 

注: 上記はソースコードから推測して作成した CHANGELOG です。リリースノートとして公開する前に、実際のコミット履歴や変更意図と照合してください。
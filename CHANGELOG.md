Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました（日本語）。この変更履歴は提示されたコードベースから推測してまとめた初回リリース向けの内容です。

---------------------------------------------------------------------
# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠しています。
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加 (src/kabusys/__init__.py)。公開モジュール: data, strategy, execution, monitoring。
  - バージョン番号を初期化: __version__ = "0.1.0"。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - .env と .env.local の読み込み優先順位を導入（OS 環境変数は保護）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト時などに使用可能）。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート処理、行内コメント取り扱い、無効行スキップ。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベルの検証ロジックを提供。
  - KABUSYS_ENV の許可値 (development, paper_trading, live) と LOG_LEVEL の検証を実装。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 基本クライアントを実装（トークン取得, token refresh, GET/POST, JSON decode）。
  - レート制御: 固定間隔スロットリングで 120 req/min を厳守する RateLimiter を実装。
  - リトライロジック: 指数バックオフ、最大 3 回、HTTP 408/429 と 5xx に対する再試行。429 の場合は Retry-After を尊重。
  - 401 応答時のトークン自動リフレッシュ（1 回のみ再試行、無限再帰回避）。
  - ID トークンのモジュール内キャッシュ（ページネーション間で共有）。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等に保存する保存関数を実装（ON CONFLICT DO UPDATE):
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 保存処理で fetched_at を UTC（ISO 8601 Z 表記）で付与し、どの時点でデータを取得したかを明示。
  - PK 欠損行はスキップして警告ログを出力する挙動を実装。
  - 型変換ユーティリティ: _to_float, _to_int（不正値安全に None を返す、"1.0" のような float 文字列を適切に扱う）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集基盤を実装（デフォルトに Yahoo Finance の RSS を追加）。
  - セキュリティ対策：
    - defusedxml を利用して XML ベースの脆弱性（XML bomb 等）を低減。
    - URL スキーム検証（http/https のみ許可）で SSRF を防止。
    - リダイレクト時にスキームと宛先のプライベートアドレスを評価するハンドラを導入。
    - ホストのプライベートアドレス判定（IP 直接判定および DNS 解決して A/AAAA を確認）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）を導入しメモリ DoS を防ぐ。gzip 解凍後の増大も検査。
  - URL 正規化と追跡パラメータ除去（utm_*, fbclid 等）による記事ID生成（SHA-256 の先頭32文字）を実装。これにより冪等保存を実現。
  - テキスト前処理関数 preprocess_text（URL 除去・空白正規化）。
  - RSS パース: content:encoded 優先、pubDate の安全なパース（失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用いたチャンク挿入（トランザクション内、一括挿入）で新規記事IDリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入で効率的に実行（ON CONFLICT DO NOTHING）。
  - 銘柄コード抽出ロジック（extract_stock_codes）: 4桁数字を候補として known_codes でフィルタし重複除去して返す。
  - 統合収集ジョブ run_news_collection を実装。各ソースを独立処理し、失敗したソースはスキップして残りを継続。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用のスキーマ初期化モジュールを実装。
  - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル DDL を定義（制約と型安全性を考慮）。
  - 典型的クエリのためのインデックスを追加（銘柄×日付、ステータス検索等）。
  - init_schema(db_path) でディレクトリ自動作成とテーブル作成を行う冪等な初期化を提供。
  - get_connection(db_path) で既存 DB 接続を取得可能。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新 ETL の骨子を実装:
    - 最終取得日からの差分取得ロジック（backfill_days による後出し修正吸収）。
    - 市場カレンダーの先読み定数、最小データ日付の定義。
  - 結果を表す ETLResult dataclass を追加（品質問題やエラー情報を格納、辞書化可能）。
  - テーブル存在チェックや最大日付取得などのユーティリティを実装。
  - run_prices_etl を実装（date_from の算出、fetch_daily_quotes 呼び出し、保存処理）。戻り値は取得件数と保存件数。

### 変更 (Changed)
- （初回リリースのため変更履歴は省略）

### 修正 (Fixed)
- （初回リリースのため修正履歴はなし）

### セキュリティ (Security)
- RSS パースに defusedxml を導入して XML 関連の脆弱性軽減。
- RSS 取得で SSRF 対策（スキーム検証・プライベートホスト拒否・リダイレクト前検査）。
- HTTP レスポンスのサイズ上限と gzip 解凍後の再確認でメモリ消費攻撃（Gzip bomb 等）を緩和。

### 既知の制限 / 注意事項 (Notes)
- .env 自動読み込みはデフォルト ON。テストや CI で邪魔になる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants への API リクエストは最大再試行回数を超えると RuntimeError を送出します。呼び出し元での例外ハンドリングを想定しています。
- run_prices_etl 等の ETL 関数は DB スキーマの存在を前提にしており、初回は schema.init_schema を呼び出しておくことを推奨します。
- news_collector の既知銘柄セット (known_codes) を提供しない場合、銘柄紐付け処理はスキップされます。
- パイプライン実装は骨子が実装されている状態であり、品質チェックモジュール (kabusys.data.quality) の詳細実装や追加の ETL ジョブ（財務・カレンダーの差分処理など）の完成は今後の作業を想定。

---------------------------------------------------------------------
（補足）
この CHANGELOG は提供されたソースコードから機能と設計意図を推測して作成しています。実際の変更履歴やリリースノートには開発者の意図やコミット履歴に基づく正式な記載を併せて反映してください。
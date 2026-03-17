# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このファイルはコードベースから推測して生成した初期の変更履歴です。

注: バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせて 0.1.0 としています。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース（推測）。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ骨格
  - パッケージ名 kabusys を導入。公開モジュールとして data, strategy, execution, monitoring を定義（strategy/execution/monitoring は初期プレースホルダ）。
  - バージョン情報を __version__ = "0.1.0" として設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーの拡張:
    - export KEY=val 形式、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、行内コメント処理に対応。
    - 既存 OS 環境変数を保護する protected オプション。
  - Settings クラスを提供（J-Quants トークン、kabu API パスワード・ベース URL、Slack トークン/チャンネル、DB パス、実行環境/ログレベル判定など）。
  - KABUSYS_ENV と LOG_LEVEL の妥当性チェック（許容値の検証）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API クライアントを実装:
    - ベース URL、API レート制限（120 req/min）に基づく固定間隔スロットリング（RateLimiter）。
    - 冪等なデータ保存を想定した fetch/save 関数群（株価日足、四半期財務、マーケットカレンダー）。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx に対応）。
    - 401 Unauthorized 受信時は自動でリフレッシュトークンを使って id_token を更新して 1 回だけリトライ。
    - ページネーション対応と、ページ間で共有する id_token のモジュールレベルキャッシュ。
    - データ保存時の冪等性を保つため DuckDB への INSERT ... ON CONFLICT DO UPDATE を利用。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を軽減。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集機能を実装:
    - デフォルト RSS ソース（例: Yahoo Finance）。
    - RSS 取得 → テキスト前処理（URL 除去・空白正規化） → raw_news テーブルへの冪等保存 → 銘柄紐付け の一連処理。
  - セキュリティ・堅牢性対策:
    - defusedxml を利用して XML Bomb 等を防止。
    - SSRF 防止: URL スキーム検証（http/https のみ）、レスポンスのリダイレクト先を検査する専用ハンドラ（_SSRFBlockRedirectHandler）、プライベート IP/ループバック判定。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入しメモリ DoS を軽減。gzip 圧縮レスポンスの解凍後も確認。
    - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）で冪等性を確保。
  - DB 書き込み:
    - DuckDB へのバルク挿入をチャンク化してトランザクション内で実行。
    - INSERT ... ON CONFLICT DO NOTHING RETURNING を使い、実際に挿入された記事 ID / 件数を正確に返却。
    - ニュースと銘柄コードの紐付けを一括で保存する内部ユーティリティ（重複除去、チャンク処理）。
  - テキスト中の銘柄コード抽出機能（4桁数字パターン + known_codes によるフィルタ）を実装。

- DuckDB スキーマ定義 / 初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature） + Execution 層のテーブル定義を実装。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw レイヤー。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
    - features, ai_scores 等の Feature レイヤー。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
  - 各テーブルに適切な型チェック制約、PRIMARY KEY、外部キーを設定。
  - 検索性能を考慮したインデックスを複数定義（頻出クエリパターンに対応）。
  - init_schema(db_path) 関数でディレクトリ作成・DDL 実行・インデックス作成を行い、冪等にスキーマ初期化を実行。
  - get_connection(db_path) で既存 DB へ接続（初期化はしない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を行う ETL パイプラインの初期実装:
    - DB の最終取得日を元に差分範囲を算出し、デフォルトは backfill_days=3 で直近の数日前から再取得して API 後出し修正を吸収。
    - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）。
    - ETLResult データクラスで詳細結果（取得数、保存数、品質問題、エラー）を集約。
    - テーブル存在チェックや最大日付取得ユーティリティを提供（_table_exists / _get_max_date）。
    - 非営業日調整ユーティリティ（_adjust_to_trading_day）。
    - 個別ジョブ例として run_prices_etl を実装（差分算出、fetch->save の流れ）。※未完の戻り値部分など実装途上の箇所あり（コードより推測）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- news_collector において SSRF 対策、defusedxml の利用、レスポンスサイズ制限、gzip 解凍後の検査など、外部入力・リソース処理に関する堅牢化を実施。
- .env パーサーにおけるクォート内エスケープ処理やコメント除去で意図しない値読み込みを抑止。

### 内部 / その他 (Internal)
- jquants_client の HTTP 実装は urllib を基にした自前実装で、リトライ・バックオフ・Retry-After ヘッダ対応を含む。テスト時の差し替え用フック（_urlopen のような設計思想）を一部に持つ。
- データ保存ロジックは DuckDB のパラメータプレースホルダを用いて実行（大量データ処理時にチャンク化してオーバーヘッドを抑制）。

## 既知の制限・今後の作業（推測）
- pipeline.run_prices_etl の末尾に戻り値が途中で途切れている（コード末尾が不完全）。完全な ETL 結果を返すための仕上げが必要。
- strategy, execution, monitoring モジュールは未実装またはプレースホルダのため、戦略設計・発注ロジック・監視通知などの実装が必要。
- テスト、ドキュメント、CI/CD、型チェックの整備（型ヒントは多くあるがテストカバレッジ不明）。
- J-Quants / kabu API まわりのエラーケースやスロットリング微調整は実運用で検証が必要。

---

（この CHANGELOG はコードの内容から推測して作成した初期ドラフトです。実際の変更履歴やリリース日付はプロジェクトのリリースノートに合わせて調整してください。）
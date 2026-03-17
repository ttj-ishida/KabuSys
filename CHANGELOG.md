# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
既存バージョンはセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主な追加点は以下のとおりです。

### 追加
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ を追加し、バージョン "0.1.0" と公開サブパッケージ（data, strategy, execution, monitoring）を定義。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読み込みを実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサー: export プレフィックス対応、シングル/ダブルクォート処理、インラインコメント処理等の堅牢なパース処理を実装。
  - protected（OS環境変数保護）を考慮した .env/.env.local の読み込みロジック（.env → .env.local の優先度）。
  - 必須設定取得ヘルパー _require。
  - 設定ラッパー Settings を追加（J-Quants/LIVE/Slack/DBパス/環境判定/ログレベル検証などのプロパティを提供）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API クライアントを実装（/token/auth_refresh、/prices/daily_quotes、/fins/statements、/markets/trading_calendar 等を利用）。
  - レート制限遵守のための固定間隔スロットリング実装（120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回。HTTP 408/429/5xx を再試行対象）。
  - 401 応答時はリフレッシュトークンで id_token を自動更新して 1 回再試行。
  - ページネーション対応（pagination_key を用いた全ページ取得）。
  - レスポンスの JSON デコード・エラーハンドリング。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存と fetched_at の記録を行う。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値に対する保護を提供。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と記事保存の一連処理を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ・堅牢性:
    - defusedxml を使った XML パース（XML Bomb 等の対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス検出による拒否、リダイレクト先の事前検査用 RedirectHandler。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ確認（Gzip bomb 対策）。
    - トラッキングパラメータ除去・URL 正規化（_normalize_url）、SHA-256（先頭32文字）による記事 ID 生成で冪等性を確保。
    - HTTP ヘッダに Accept-Encoding: gzip を送る実装。
  - DB 操作の最適化:
    - INSERT ... RETURNING を利用して実際に挿入された記事IDを正確に取得。
    - チャンク分割（_INSERT_CHUNK_SIZE）による大規模挿入の分割。
    - トランザクションでまとめてコミット／ロールバック。
  - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、known_codes フィルタ）を提供。
  - RSS の pubDate を UTC naive datetime に正規化して保存。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）および Execution レイヤーのテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed テーブル。
  - features, ai_scores など Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution テーブル。
  - インデックス（頻出クエリ向け）定義。
  - init_schema(db_path) でディレクトリ作成＋全DDL実行により初期化する API を提供。get_connection で既存DB接続を返す。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult dataclass により ETL の結果・品質問題・エラーを集約。
  - 差分更新ヘルパー（テーブル存在チェック、最大日付取得）。
  - 市場カレンダーに基づく営業日調整ヘルパー。
  - 差分更新ポリシー（最終取得日から backfill_days を用いた再取得）と run_prices_etl の骨子（差分取得 → jquants_client.fetch/save → ログ）を実装。
  - テスト容易性のため id_token を注入可能な設計。

- テスト／拡張性を意識した設計
  - news_collector._urlopen をモック差し替え可能にしてテストを容易化。
  - jquants_client の id_token キャッシュ／注入でページネーションやリトライのテストを容易化。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### セキュリティ
- RSS パースに defusedxml を採用し XML 攻撃を軽減。
- SSRF 対策（スキーム検証、プライベートIP/ホストの拒否、リダイレクト時の検査）。
- .env 自動読み込み時に OS 環境変数を保護する仕組みを導入（.env.local の上書き制御含む）。

### 既知の注意点 / TODO
- strategy および execution パッケージのエントリは存在しますが、具体的な戦略ロジックや発注実行ロジックはこのリリースでは最小実装／プレースホルダに留まっています。
- quality モジュールは参照されています（品質チェックのため）が、実装の詳細はこのリリース範囲外の可能性があります（呼び出し側での統合確認を推奨）。
- run_prices_etl 等の ETL 関数は基本ロジックを実装していますが、上位ジョブ（スケジューリング、監視、通知等）との統合は今後の拡張対象です。

変更やバグ報告、改善提案は Issue を通じてお願いします。
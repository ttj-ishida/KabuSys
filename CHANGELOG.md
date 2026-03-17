CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------
- 既知の問題:
  - run_prices_etl の戻り値が宣言上は (取得数, 保存数) のタプルであるが、実装が途中で切れており現在は取得数のみを返す状態になっています（修正予定）。

[0.1.0] - 2026-03-17
--------------------

Added
- 初回公開: KabuSys 日本株自動売買システム (バージョン 0.1.0)
  - パッケージ公開: kabusys（トップレベルで data, strategy, execution, monitoring をエクスポート）
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD サポート
  - .env/.env.local の読み込みルール（OS 環境変数の保護、override 振る舞い）
  - 環境変数のパース機能（export 形式、クォート・エスケープ、インラインコメントの扱い）
  - Settings クラスによる属性アクセス（J-Quants トークン、kabu API 設定、Slack トークン、DB パス、環境・ログレベル検証、is_live/is_paper/is_dev 等）
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務データ、JPX マーケットカレンダー取得機能を実装（ページネーション対応）
  - API レート制御（固定間隔スロットリング、120 req/min）
  - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx 対象）
  - 401 受信時にリフレッシュトークンを用いた自動トークン再発行を行い 1 回だけリトライ
  - ページネーション横断での ID トークンキャッシュ共有
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT DO UPDATE を利用する save_* 関数）
  - データ変換ユーティリティ (_to_float / _to_int) による安全な型変換
  - レスポンスの JSON デコード検査、ログ出力と詳細エラー情報
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得・パース機能（defusedxml を使用して XML 攻撃を防止）
  - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）
  - 記事ID の生成: 正規化 URL の SHA-256（先頭32文字）で冪等性を確保
  - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルかを判定して拒否、リダイレクト先検査用ハンドラを導入
  - レスポンスサイズ上限（10 MB）や gzip 解凍後のサイズ検査による DoS 緩和
  - テキスト前処理（URL 除去・空白正規化）
  - DuckDB への保存: raw_news に対するチャンク化された INSERT ... ON CONFLICT DO NOTHING RETURNING による挿入（挿入された ID を返す）、トランザクションでのロールバック処理
  - news_symbols への (news_id, code) 紐付けを一括挿入する内部ユーティリティ（重複除去、チャンク挿入、ON CONFLICT DO NOTHING RETURNING）
  - テキストからの銘柄コード抽出機能（4桁数字、known_codes によるフィルタリング）
  - run_news_collection: 複数ソースの独立エラーハンドリング、保存件数の集約
- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の多層スキーマ DDL を実装
  - raw_prices, raw_financials, raw_news, raw_executions 等の生データテーブル
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の整形済テーブル
  - features, ai_scores の特徴量レイヤー
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の実行レイヤー
  - 頻出クエリ向けのインデックス定義
  - init_schema(db_path) によるディレクトリ自動作成とテーブル/インデックス作成（冪等）
  - get_connection(db_path) による既存 DB への接続
- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass: ETL の集計結果・品質問題・エラーの収集と辞書化
  - 差分更新ヘルパー: テーブルの最終取得日取得、trading day 調整ロジック
  - run_prices_etl の骨格（差分取得、backfill による再取得、jquants_client と save の連携）
  - 設計方針: 差分更新、backfill による後出し修正吸収、品質チェックの集約（fail-fast しない）

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Security
- ニュース収集での SSRF 防止: リダイレクト時の検査、ホストのプライベートアドレス判定、許可されない URL スキームの拒否
- XML パースに defusedxml を採用して XML 関連攻撃を緩和
- ネットワークから読み込むデータ量を上限で制限しメモリ DoS を低減

Performance
- J-Quants クライアントに固定間隔レート制御を導入して API レート制限 (120 req/min) を順守
- API リトライ時に指数バックオフを使用
- DB 書き込みをチャンク化して一括挿入、トランザクションでオーバーヘッドを削減
- ページネーション間でのトークンキャッシュ共有による余分な認証コール削減

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Notes / 今後の予定
- run_prices_etl の戻り値不整合を修正し、取得数と保存数の両方を正しく返すようにする予定
- strategy / execution / monitoring パッケージは雛形のみ含まれているため、戦略実装・発注連携・監視機能を順次実装予定
- 品質管理（kabusys.data.quality）モジュールの実装・統合と、ETL の品質チェック結果に基づく自動通知や再処理ワークフローの整備予定

---- End of CHANGELOG ----
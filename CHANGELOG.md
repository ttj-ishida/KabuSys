# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0 — 2026-03-18

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - パッケージの初期バージョンを `__version__ = "0.1.0"` として追加（src/kabusys/__init__.py）。
  - パッケージ公開モジュール一覧を `__all__` で定義。

- 環境設定管理
  - .env ファイルと環境変数から設定を読み込む `kabusys.config` モジュールを実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）によりカレントワーキングディレクトリに依存しない自動ロード。
    - .env, .env.local の読み込み順序（OS環境変数 > .env.local > .env）を実現。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化サポート（テスト用途）。
    - .env の行パース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、行内コメント処理など）。
    - 必須環境変数取得時の検査（未設定時は ValueError）と Settings クラスによるプロパティ提供：
      - J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等。
    - 環境変数値の妥当性検査（env 値、LOG_LEVEL の有限集合チェック）を実装。

- データアクセス（J-Quants）
  - `kabusys.data.jquants_client` を追加（src/kabusys/data/jquants_client.py）。
    - J-Quants API クライアント機能（株価日足・四半期財務・マーケットカレンダーの取得）。
    - レート制限（固定間隔スロットリング、デフォルト 120 req/min）を実装する RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx を考慮）。
    - 401 Unauthorized を受けた場合の自動 ID トークンリフレッシュ（1 回のみ）と再試行対応。
    - ページネーション対応（pagination_key の追跡）とモジュールレベルのトークンキャッシュ共有。
    - JSON レスポンスのデコードチェックと適切な例外メッセージ。
    - DuckDB へ冪等に保存する save_* 関数群（ON CONFLICT DO UPDATE を使用）:
      - save_daily_quotes / save_financial_statements / save_market_calendar
    - fetched_at を UTC ISO8601 形式で保存し、Look‑ahead バイアス追跡が可能。
    - 型変換ユーティリティ `_to_float`, `_to_int`（安全な数値変換、意図しない切り捨て回避）。

- ニュース収集（RSS）
  - `kabusys.data.news_collector` を追加（src/kabusys/data/news_collector.py）。
    - RSS フィードからの記事収集、前処理、DuckDB への保存ワークフローを実装。
    - 設計上の注意点を反映：
      - 記事ID は正規化した URL の SHA-256（先頭32文字）で生成し冪等性を担保。
      - トラッキングパラメータ（utm_* 等）削除、フラグメント削除、クエリソートなど URL 正規化処理。
      - defusedxml を用いた XML パース（XML Bomb 等の攻撃緩和）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキーム/ホスト検証、プライベートIP判定（DNS 解決時の A/AAAA チェック含む）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後のサイズチェック（Gzip bomb 対策）。
      - content:encoded の名前空間対応、pubDate のパース（RFC 2822）、失敗時のフォールバック。
    - DB 保存の実装:
      - save_raw_news: チャンク（最大 _INSERT_CHUNK_SIZE）で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事 ID のリストを返却。トランザクションでまとめて処理。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT で重複排除、RETURNING で挿入数を正確に把握）。
    - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4桁数字、known_codes によるフィルタリング）を実装。
    - run_news_collection: 複数 RSS ソースからの収集を統合し、個々のソースでのエラーハンドリングを行いつつ DB 保存および銘柄紐付けを実行。

- データベーススキーマ（DuckDB）
  - `kabusys.data.schema` を追加（src/kabusys/data/schema.py）。
    - Raw / Processed / Feature / Execution レイヤーに分けたテーブル定義（DDL）を実装。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
    - features, ai_scores 等の Feature テーブル。
    - signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
    - 各種チェック制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を含むスキーマ設計。
    - 頻出クエリを想定したインデックス定義リストを追加。
    - init_schema(db_path): ディレクトリ自動作成（必要な場合）、DDL とインデックスを実行して接続を返す（冪等）。
    - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）。

- ETL パイプライン
  - `kabusys.data.pipeline` を追加（src/kabusys/data/pipeline.py）。
    - 差分更新（差分取得）を行う ETL 層の骨組みを実装。
    - ETLResult データクラス: 各種取得・保存数、品質チェック結果、エラー一覧を保持。品質問題の重大度判定ヘルパ（has_quality_errors）と辞書出力用 to_dict を備える。
    - 差分ヘルパ: テーブル存在チェック、最大日付取得ユーティリティ（_get_max_date）、営業日調整ヘルパ（_adjust_to_trading_day）。
    - run_prices_etl の骨格実装（対象日の差分取得、バックフィル日数のデフォルト、J-Quants クライアント経由での取得と保存）。（注: ファイル末尾で切れている箇所あり、以降の処理は継続前提）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集における SSRF 緩和:
  - URL スキーム制限（http/https）、リダイレクト時の検査、ホストがプライベートアドレスかどうかの判定ロジックを導入。
  - defusedxml による XML パースで XML 攻撃に対する防御を追加。
- ネットワーク関連:
  - J-Quants クライアントでの堅牢なリトライ / 429 の Retry-After 尊重などにより API 側に配慮した実装。

### Performance / Reliability
- レート制限（固定間隔スロットリング）を導入し API 制限を遵守。
- ニュース保存でチャンク化（_INSERT_CHUNK_SIZE）とトランザクションによるロールバック対応を実装し、DB オーバーヘッドを低減しつつデータ整合性を確保。
- DuckDB への保存は可能な限り冪等操作（ON CONFLICT DO UPDATE / DO NOTHING）で安全に更新。

### Notes / Known limitations
- run_prices_etl のファイル末尾が途中で切れている（スニペット末端）ため、ETL の最終的なエラー集約や calendar/financials の統合処理、品質チェック呼び出し部などが完全には確認できません。実運用前に pipeline の残り処理の実装・確認を推奨します。
- settings の一部プロパティ（例: jquants_refresh_token 等）は未設定時に ValueError を投げる仕様のため、環境変数のセットが必須です。`.env.example` に基づき .env を準備してください。
- DuckDB スキーマは多くの CHECK 制約や外部キーを含むため、既存の DB を移行する場合はスキーマ整合性を確認してください。

---

作者: KabuSys 開発チーム  
リリース日: 2026-03-18

（詳細な実装・利用方法はソースコードの docstring と README を参照してください。）
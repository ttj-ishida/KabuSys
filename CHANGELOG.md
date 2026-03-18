CHANGELOG
=========

すべての変更は「Keep a Changelog」フォーマットに準拠して記載しています。

[Unreleased]
-----------

- なし

[0.1.0] - 2026-03-18
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージエントリポイント: kabusys (src/kabusys/__init__.py)。
  - 空の名前空間モジュールを追加: kabusys.execution, kabusys.strategy（将来的な拡張用）。
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込み無効化。
  - export KEY=val 形式やクォート付き値、行内コメントの処理に対応するパーサ実装。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / システム環境設定をプロパティで取得可能。
  - 環境変数バリデーション（KABUSYS_ENV、LOG_LEVEL 等）。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得用の fetch_* 関数を実装。
  - レート制御: 固定間隔スロットリング（120 req/min）を内蔵する RateLimiter。
  - リトライ処理: ネットワーク系 / 429 / 408 / 5xx に対して指数バックオフ（最大3回）。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して1回リトライ。
  - ページネーション対応（pagination_key を利用して全件取得）。
  - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を使用）。
  - データの fetched_at に UTC タイムスタンプを記録し、look-ahead bias のトレースを可能に。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、空値・不正値を安全に扱う。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得 & 前処理 & DuckDB への保存ワークフローを実装。
  - 設計上の特徴:
    - defusedxml を利用して XML Bomb 等の攻撃を防止。
    - SSRF 対策: リダイレクト先スキーム検査、ホストがプライベート/ループバック/リンクローカルかの検査（DNS 解決を含む）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - URL 正規化: トラッキングパラメータ（utm_* 等）を除去、クエリをソート、フラグメント削除。
    - 記事ID は正規化 URL の SHA-256 先頭32文字で生成し冪等性を確保。
    - DB 保存はチャンク化して一括 INSERT（INSERT ... RETURNING を利用し、新規挿入された ID を返す）。
    - 銘柄コード抽出ロジック（4桁数字パターン、known_codes によるフィルタ）と一括紐付け保存機能。
  - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を追加。
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の各レイヤー向けテーブル定義を実装。
  - 主なテーブル: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - 適切なチェック制約（CHECK、NOT NULL、PRIMARY KEY、FOREIGN KEY）を付与。
  - インデックス定義（頻出クエリパターンを想定）。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成 → スキーマ作成（冪等）。get_connection() で既存 DB へ接続。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult dataclass による ETL 結果集約（品質問題やエラーメッセージを保持）。
  - 差分更新ヘルパー: テーブルの最終取得日取得、営業日調整ロジック（market_calendar を利用）。
  - run_prices_etl 実装（差分取得・バックフィル日数・保存処理の呼び出しなど）。（注: 本スナップショットは run_prices_etl 以降が途中の可能性あり）
  - 設計方針: 差分更新（最終取得日の backfill）、品質チェックを呼び出し元が判断できる形で報告する方針などを明記。
- その他
  - ニュース収集や J-Quants クライアント等でロギングを適切に行うよう実装。
  - デフォルトの DuckDB パスや SQLite monitoring パスを Settings で定義（data/kabusys.duckdb, data/monitoring.db）。

Security
- ニュース収集でのセキュリティ強化:
  - defusedxml を使用した XML パースで XML-based attack を軽減。
  - SSRF 対策（リダイレクト検査、プライベート IP の拒否、許可スキーム制限）。
  - レスポンスサイズ制限・gzip 解凍後のサイズチェックによる DoS 対策。
- J-Quants クライアント:
  - トークン自動リフレッシュとリトライ制御で不正な挙動と過度なリトライを抑制。

Changed
- 新規初版のため「Changed」は該当なし。

Fixed
- 新規初版のため「Fixed」は該当なし。

Deprecated
- なし

Removed
- なし

Notes / Requirements / Known issues
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings にて必須として参照）。
- 依存ライブラリ:
  - duckdb, defusedxml（コード内で使用）。
- デフォルト設定:
  - J-Quants のベースURL はデフォルトで https://api.jquants.com/v1 を使用。
  - デフォルト RSS ソースは Yahoo Finance のビジネスカテゴリ（src/kabusys/data/news_collector.py）。
- スキーマ / データ移行:
  - init_schema() は既存テーブルをスキップするため冪等で実行可能。既存データは保護されるが、DDL の変更点がある場合は注意。
- 実装の一部（パイプライン等）はスナップショット時点で継続開発向けの構造を含みます。例えば pipeline.run_prices_etl は本ファイルで実装途中の箇所が見受けられるため、実行前に完全実装・テストを行ってください。
- エラー/例外ハンドリングはログ出力と呼び出し元への例外伝播を基本としています。運用時は監視/再試行の仕組みを追加してください。

Contributing
- 初回リリースのため詳細なコントリビュートルールは未記載。今後のバージョンで CONTRIBUTING.md 等の追加を検討してください。

ライセンス
- コードベースにライセンス表記はスナップショットに含まれていません。公開する際は適切なライセンスを明示してください。
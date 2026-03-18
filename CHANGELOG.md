CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- 基本パッケージ構成を追加（kabusys v0.1.0）
  - パッケージのエントリポイント (src/kabusys/__init__.py) を追加。
  - __version__ を "0.1.0" に設定し、公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロード機構:
    - プロジェクトルートを .git / pyproject.toml を起点に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export KEY=val, シングル/ダブルクォート、インラインコメント、エスケープを適切に処理。
  - 必須設定取得のヘルパー _require と各種プロパティを実装（J-Quants トークン、kabu API、Slack トークン/チャンネル、DB パス、実行環境/ログレベル判定等）。
  - KABUSYS_ENV および LOG_LEVEL のバリデーションを実装（許容値を制限）。

- Data レイヤー: J-Quants クライアントを実装（src/kabusys/data/jquants_client.py）
  - API 基本機能:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 冪等性を考慮したページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時はトークン自動リフレッシュを1回実施（キャッシュ化された ID トークン）。
    - JSON デコードエラーやネットワークエラーの明示的なハンドリング。
  - DuckDB への保存関数（冪等/アップサート）:
    - save_daily_quotes (raw_prices への挿入／ON CONFLICT DO UPDATE)
    - save_financial_statements (raw_financials への挿入／ON CONFLICT DO UPDATE)
    - save_market_calendar (market_calendar への挿入／ON CONFLICT DO UPDATE)
  - データ型変換ユーティリティ (_to_float / _to_int) を実装し、不正値を安全に扱う。

- Data レイヤー: ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集・整形し raw_news に保存するワークフローを実装。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト前後でスキーム/ホストを検証、プライベートアドレスへのアクセスを拒否。
    - 許容スキームは http/https のみ。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の検査（Gzip bomb 対策）。
  - テキスト前処理: URL 削除・空白正規化。
  - URL 正規化: トラッキングパラメータ（utm_ など）の除去、クエリソート、フラグメント削除。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、新規挿入された記事IDを返す（トランザクションで整合性確保）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク挿入で処理（重複除去・トランザクション）。
  - 銘柄抽出ユーティリティ extract_stock_codes を実装（4桁数字の候補抽出と known_codes によるフィルタリング）。
  - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを定義。

- Research レイヤーを追加（src/kabusys/research/*.py）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から各ホライズン先の将来リターンを DuckDB の prices_daily から一度のクエリで取得。
    - calc_ic: スピアマン（ランク）相関を計算し、足りないデータは None を返す。
    - rank: 同順位は平均ランクを付与（浮動小数点の丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）。
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算（ウィンドウ不足は None）。
    - calc_volatility: 20日 ATR、ATR/Close（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials の最新財務データと当日の株価から PER / ROE を計算（EPS 無効時は None）。
  - research パッケージの __all__ を定義し、zscore_normalize（kabusys.data.stats 由来）などを公開。

- スキーマ定義モジュールを追加（src/kabusys/data/schema.py）
  - DuckDB 用 DDL を用意（Raw レイヤーのテーブル定義を含む）。
    - raw_prices, raw_financials, raw_news, raw_executions（途中定義が含まれるが DDL 用意済み）。
  - Data レイヤー向けのテーブル構造（型チェック、PRIMARY KEY、CHECK 制約など）を定義。

Security
- RSS 取得・解析での SSRF 対策、defusedxml 使用、レスポンスサイズ制限、スキーム検証等を導入。
- J-Quants クライアントは認証トークンの安全な更新（自動リフレッシュ）とレート制限を実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / Implementation details
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、prices_daily / raw_financials / raw_* テーブルのみを参照する設計で、
  本番の発注 API や外部サービスに直接アクセスしないよう分離されている（リサーチ/データ処理と実取引ロジックの分離）。
- ネットワークなど外部依存の失敗は適切にログ出力して部分的な失敗が他処理を妨げないよう設計されている。
- 将来的な改良候補:
  - schema の完全完成（Execution レイヤー等の DDL 継続実装）
  - strategy / execution / monitoring の具体実装（現時点ではパッケージエントリのみ）
  - 単体テスト・統合テストの追加

----- 
本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は追加の変更点・マイグレーション手順・既知の問題点を追記してください。
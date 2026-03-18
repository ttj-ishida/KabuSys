CHANGELOG
=========

すべての変更は Keep a Changelog の規約に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加点は以下の通りです。

Added
- パッケージ基礎
  - kabusys パッケージの初期化（__version__ = "0.1.0"、主要サブパッケージの __all__ 宣言）。
- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）。
  - .env 自動ロード機能（優先順位: OS 環境変数 > .env.local > .env）。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - .env パーサの実装（コメント、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ処理、インラインコメント処理をサポート）。
  - 必須設定取得用の _require ユーティリティと、KABUSYS_ENV / LOG_LEVEL の検証ロジック。
  - データベースパス（duckdb/sqlite）、Slack、kabu API、J-Quants トークン等の設定プロパティを提供。
- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大試行回数、特定ステータスコードの再試行）を実装。
  - 401 Unauthorized 時にリフレッシュトークンで自動的に id_token を再取得して 1 回リトライする仕組み。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE による上書きで冪等性を確保。
  - 型変換ユーティリティ _to_float / _to_int（安全な変換ロジック）。
  - fetched_at に UTC タイムスタンプを記録し、データ取得時点を追跡可能に。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news テーブルへ保存する機能。
  - RSS 取得時のセキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等のリスク低減）。
    - URL スキーム検証（http/https のみ許可）と SSRF 対策（リダイレクト先のスキーム/ホスト検査）。
    - ホストがプライベートアドレスかを検査する _is_private_host（直接 IP / DNS 解決の両面で判定）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES、デフォルト 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - リダイレクト時に先に検証を行う専用ハンドラ（_SSRFBlockRedirectHandler）。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - 銘柄コード抽出（4桁の数字パターンと known_codes によるフィルタリング）。
  - DB 保存はチャンク化してトランザクションで一括 INSERT、INSERT ... RETURNING を利用して実際に挿入された件数を返す実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - run_news_collection により複数 RSS ソースの独立した収集処理を提供（ソース単位でエラーハンドリング）。
- DuckDB スキーマ（kabusys.data.schema）
  - Raw Layer の主要テーブル DDL（raw_prices, raw_financials, raw_news, raw_executions（断片））を定義するスクリプトを実装。
  - 各テーブルに適切な型制約・チェック制約（NOT NULL、CHECK など）を記載。
- リサーチ / ファクター計算（kabusys.research）
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズンに対応、DuckDB による一括取得）。
    - IC（Information Coefficient、Spearman の ρ）計算 calc_ic、ランク付けユーティリティ rank。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装する方針を明記。
  - factor_research:
    - モメンタムファクター calc_momentum（1M/3M/6M リターン、200日移動平均乖離）。
    - ボラティリティ／流動性 calc_volatility（20日 ATR、ATR 比率、20日平均売買代金、出来高比）。
    - バリュー calc_value（raw_financials から直近財務を取得し PER/ROE を算出）。
    - DuckDB を用いたウィンドウ関数、LAG/AVG/COUNT を活用した実装。
  - research パッケージの __init__ で主要関数群をエクスポート（calc_momentum 等と zscore_normalize を結合）。
- ロギング
  - 各主要処理（fetch/save/calc など）で情報ログ・警告ログを出力するように実装。
  - エラー発生時には例外ログを残す設計（トランザクション失敗時の rollback と exception ログなど）。
- 設計上の注記（ドキュメント文字列）
  - 各モジュールに設計方針・安全対策・冪等性・Look-ahead bias 対策等の説明を追加（ドキュメント化を重視）。

Changed
- （初回リリースのため、変更点はありません）

Fixed
- （初回リリースのため、修正点はありません）

Security
- ニュース収集における SSRF 対策、defusedxml による XML パース、安全な URL 正規化、レスポンスサイズ上限、プライベートアドレス検査などセキュリティ対策を導入。

Deprecated
- （該当なし）

Removed
- （該当なし）

Notes / Known limitations
- DuckDB スキーマは Raw Layer の DDL を含むが、Feature/Processed/Execution 層の完全な DDL は本バージョンでは未完（raw_executions の DDL が途中までの定義など）。
- research モジュールは標準ライブラリのみで実装されており、pandas 等の利便性ライブラリは利用していない。大量データでの操作は DuckDB 側の性能に依存する。
- J-Quants クライアントはネットワーク呼び出しと外部 API に依存するため、実行環境での設定（JQUANTS_REFRESH_TOKEN 等）が必要。
- news_collector の _is_private_host は DNS 解決失敗時に安全側（非プライベート）扱いするため、厳密な環境では補助的なネットワークポリシーの併用を推奨。

作者・貢献者
- 初期実装: KabuSys 開発チーム

--- 

今後のリリースでは、Feature/Processed/Execution 層の DDL 完全化、戦略実行・発注パイプライン（kabu API 統合）、モニタリング・アラート機能、テストカバレッジの拡充などを予定しています。
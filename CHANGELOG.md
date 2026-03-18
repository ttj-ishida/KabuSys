# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の慣習に従い、セマンティックバージョニングを用いています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18

初回リリース — 日本株自動売買システムの骨格となるモジュール群を実装。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に設定。
  - strategy/ と execution/ モジュールのプレースホルダ（__init__.py を配置）。

- 設定管理
  - kabusys.config モジュールを追加。
  - .env ファイル（.env, .env.local）および環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env の柔軟なパース実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、コメントの扱い）。
  - OS 環境変数を保護する読み込みロジック（.env.local を override=True で上書き。ただし既存の OS 環境変数は保護）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / システム設定等の取得用プロパティを実装（必須変数未設定時は ValueError を送出、enum 的な検証あり）。

- J-Quants API クライアント
  - kabusys.data.jquants_client を追加。
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レート制御: 固定間隔スロットリングで 120 req/min 相当の _RateLimiter を実装。
  - リトライと障害対策: 指数バックオフ、最大 3 回リトライ（408/429/5xx を対象）、429 の場合は Retry-After を考慮。
  - 認証トークン自動リフレッシュ: 401 受信時に refresh を試みて1回リトライ（無限再帰防止）。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を提供。ON CONFLICT DO UPDATE による冪等保存を実現。
  - レスポンスの JSON デコード異常や HTTP エラーを適切に扱うエラーハンドリングとログ出力。

- ニュース収集（RSS）
  - kabusys.data.news_collector を追加。
  - RSS フィード取得とパース機能（defusedxml を使用し XMLBomb 等の攻撃を軽減）。
  - セキュリティ対策:
    - URL スキーム検証（http/https のみ許可）。
    - SSRF 対策: リダイレクト先のスキーム・ホスト検証、プライベート/ループバック/リンクローカルアドレスへの接続拒否（DNS解決して A/AAAA を検査）。
    - 最大受信バイト数制限（デフォルト 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - コンテンツ前処理: URL 除去、空白正規化。
  - 記事ID は正規化された URL の SHA-256（先頭32文字）で生成し冪等性を確保（utm_* 等のトラッキングパラメータは除去して正規化）。
  - raw_news へのバルク保存: チャンク化（デフォルト 1000 件）してトランザクション内で INSERT ... RETURNING を利用し、新規挿入 ID を正確に取得。
  - 記事と銘柄コードの紐付け機能（news_symbols）を提供。銘柄抽出は 4 桁数字パターンに基づき、known_codes に照合して重複除去。
  - RSS フィード収集の統合ジョブ run_news_collection を実装（ソース毎に独立して例外処理、失敗しても他ソースは継続）。

- データベーススキーマ（DuckDB）
  - kabusys.data.schema を追加し、DataPlatform 構成に基づくスキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約、CHECK 制約、PRIMARY/FOREIGN KEY を設定。
  - よく使われるクエリ向けに複数のインデックスを作成。
  - init_schema(db_path) によりディレクトリ自動作成＋DDL 実行で初期化（冪等）。get_connection() で接続取得。

- ETL パイプライン
  - kabusys.data.pipeline を追加。
  - 差分更新（差分ETL）を想定したユーティリティ群を実装:
    - DB の最終取得日取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 営業日調整ヘルパー（_adjust_to_trading_day）。
    - 差分ETL 実装方針: デフォルトは backfill_days=3（最終取得日の数日前から再取得して API の後出し修正を吸収）。
  - ETL 実行結果を表す ETLResult データクラスを導入（品質チェック結果・エラーの収集、シリアライズ可能な to_dict）。
  - run_prices_etl を実装（差分算出→fetch_daily_quotes→save_daily_quotes を行う）。（差分ETL の設計方針、ログ出力あり）
  - 品質チェックモジュール（kabusys.data.quality を参照）との連携設計（品質問題は検知して報告するが、Fail-Fast にはしない設計）。

### Security
- 外部データ取得に複数のセーフガードを導入:
  - RSS の XML パースに defusedxml を用いることで XML 攻撃を軽減。
  - HTTP リダイレクト時にスキームと到達先ホストを事前検査して SSRF を防止。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後の再検査によりメモリ DoS / Gzip bomb を防止。
  - .env 読み込み時に OS 環境変数の上書きを制御する保護機能を実装。

### Internal / Notes
- 設計文書や DataPlatform.md / DataSchema.md を参照した設計方針に沿って実装（コメント・docstring を充実）。
- strategy/ と execution/ はまだ機能実装の骨組み（パッケージレベルでのプレースホルダ）に留まるため、アルゴリズム実装や発注ロジックは今後のフェーズ。
- jquants_client は API レート制限やトークン更新ロジックを組み込んでいるため、テストではネットワーク呼び出しをモックして利用することを推奨。

### Known issues / Limitations
- 初期リリースでは監視（monitoring）・戦略（strategy）・実行（execution）の中核ロジックは未実装またはプレースホルダのまま。ETL / データ収集・保存・スキーマ整備が中心。
- 外部 API / RSS の振る舞いに依存する箇所があるため、実運用前に各種エンドポイント／フィードの互換性検証が必要。
- DuckDB を用いているため、大規模データ運用・同時書き込みが必要な場合は運用設計（ロック・接続制御）を検討すること。

## [Links]
- リリース時のソースは src/kabusys 以下に実装されています（主要モジュール: config, data.jquants_client, data.news_collector, data.schema, data.pipeline）。

（以降の変更は Unreleased セクションに記録してください）
# Changelog

すべての重要な変更点を記録しています。フォーマットは "Keep a Changelog" に準拠しています。  

注: この CHANGELOG は提供されたコードベースの内容から推測して作成した初版のリリースノートです。

## [Unreleased]

## [0.1.0] - 2026-03-19

Added
- パッケージ初期リリース "KabuSys"（__version__ = 0.1.0）。
- パッケージ構成:
  - kabusys.config: 環境変数/設定管理（.env/.env.local 自動読み込み、プロジェクトルート探索、.env の行パーサー、必須環境変数チェック）。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パースはクォート・エスケープ・コメント・`export KEY=val` 形式に対応。
    - settings オブジェクト経由で J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、環境（development/paper_trading/live）やログレベルを取得。値検証（有効な env/log level の検査）を実装。
  - kabusys.data:
    - jquants_client: J-Quants API クライアントを実装。
      - 固定間隔のレート制限（120 req/min）を守る RateLimiter。
      - ページネーション対応の取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
      - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の扱い、429 の Retry-After 考慮）。
      - 401 受信時の自動トークンリフレッシュ（1 回）とモジュール内トークンキャッシュ。
      - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。ON CONFLICT（重複更新）で重複排除。
      - 安全で堅牢な型変換ユーティリティ（_to_float, _to_int）。
    - news_collector: RSS からニュースを収集・DB 保存するモジュールを実装。
      - RSS フェッチ（fetch_rss）: defusedxml によるパース、gzip 解凍対応、Content-Length/受信バイト数上限 (10 MB) の検査、XML パース失敗時の安全なフォールバック。
      - SSRF 対策: URL スキーム検証（http/https 限定）、リダイレクト時のスキーム/ホスト検査、内部アドレス（プライベート/ループバック等）へのアクセス防止。
      - URL 正規化とトラッキングパラメータ削除（_normalize_url）、記事 ID を URL 正規化後の SHA-256 の先頭 32 文字で生成（_make_article_id）して冪等性を確保。
      - テキスト前処理（URL 除去、空白正規化）、銘柄コード抽出（4 桁数字フィルタ + known_codes チェック）。
      - DuckDB への保存関数（save_raw_news, save_news_symbols, _save_news_symbols_bulk）: トランザクションまとめ、チャンク挿入、INSERT ... RETURNING による実挿入件数取得、ON CONFLICT で重複スキップ。
      - 高水準ジョブ run_news_collection: 複数ソースを独立処理し、失敗ソースはスキップして継続。
    - schema: DuckDB 用スキーマ定義（Raw Layer の DDL: raw_prices, raw_financials, raw_news, raw_executions 等）を定義。
  - kabusys.research:
    - factor_research: 戦略向けファクター計算（calc_momentum, calc_volatility, calc_value）。
      - DuckDB のウィンドウ関数/集計を活用してモメンタム（1/3/6ヶ月）、MA200 乖離、20日 ATR、平均売買代金、PER/ROE（raw_financials 結合）等を計算。
      - データ不足時は None を返す等、実運用を想定したロバストな振る舞い。
    - feature_exploration: 特徴量探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）。
      - forward returns の一括取得（単一クエリで複数ホライズン取得）、スピアマン IC（ランク相関）計算、基本統計量サマリー。
      - 外部ライブラリに依存せず標準ライブラリ + duckdb で実装されている点を明記。
    - re-export（research.__init__）で主要関数をまとめて公開（zscore_normalize は kabusys.data.stats から取り込み）。
- ロギング: 各主要関数で情報/警告/デバッグログを追加し、運用中の観察性を向上。

Changed
- 初回リリースのため該当なし（ベース機能の実装）。

Fixed
- 初期実装における堅牢性の考慮点を複数対処（コード上の設計反映として記載）。
  - .env 読み込みで読み取り失敗時に警告を出力してスキップ。
  - RSS 取得でサイズ超過・gzip 解凍失敗時に安全にスキップ。
  - raw_* 保存処理で主キー欠損行をスキップし警告を出力。
  - news_symbols/save_raw_news でトランザクション失敗時にロールバックして例外を再送出。

Security
- news_collector:
  - defusedxml を使用して XML 関連の攻撃（XML bomb 等）への耐性を確保。
  - SSRF 対策: URL スキーム検査、リダイレクト先検査、ホスト/IP のプライベート判定。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES）、gzip 解凍後のサイズチェックでメモリ DoS を軽減。
- jquants_client:
  - レート制限とリトライ（429 の Retry-After を尊重）により API レートリミット違反のリスクを低減。
  - 401 発生時に安全にトークンをリフレッシュする実装（無限再帰回避）。

Notes / Known limitations
- research モジュールは DuckDB の prices_daily / raw_financials テーブルを前提としており、本実装はそれらテーブルの存在・整合性が必要。
- data/schema モジュール内の DDL は Raw Layer を中心に定義済み。プロダクション用の追加テーブル（Processed/Feature/Execution 層）は今後拡張の余地あり。
- 外部依存を最小化する設計だが、実運用では pandas 等を導入したほうが解析の効率が上がる場合がある（現バージョンは標準ライブラリ + duckdb に重点を置く）。
- News の記事 ID は URL ベースの正規化に依存するため、ソースによっては一意性の保証条件に注意が必要。

---

この CHANGELOG はコードベースから推測して作成しています。具体的なリリース方針や日付、追加の修正履歴がある場合は適宜更新してください。
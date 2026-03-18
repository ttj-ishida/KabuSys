# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルではパッケージの主要な追加・変更点を日本語で記載しています。

履歴
----

### 0.1.0 - 2026-03-18

初回リリース。以下の主要機能を実装しました。

Added
- パッケージ基盤
  - kabusys パッケージの初期化（__version__ = 0.1.0、主要サブパッケージを __all__ に設定）。
- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索する実装で CWD に依存しない設計。
  - 強力な .env パーサーを実装（コメント行・export プレフィックス・クォートやエスケープの扱い・インラインコメントの処理等に対応）。
  - 環境変数取得のユーティリティ（必須変数チェック）および Settings クラスを提供。
    - J-Quants / kabu API / Slack / データベースパス / 環境（development/paper_trading/live）/ログレベルの検証を含むプロパティを提供。
    - 不正な KABUSYS_ENV や LOG_LEVEL の値は ValueError で明示的に拒否。
- データ取得・永続化 (kabusys.data)
  - J-Quants API クライアント実装 (kabusys.data.jquants_client)
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
    - 再試行（指数バックオフ、最大 3 回）と HTTP ステータスに基づくリトライロジック（408/429/5xx を対象）。
    - 401 受信時の自動トークンリフレッシュと一度だけのリトライ実装（無限再帰防止）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE を使用した raw_prices / raw_financials / market_calendar 保存）。
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値の安全な処理を行う。
  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィードの取得・パース・記事整形・DB 保存のフローを実装。
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 対策）。
      - SSRF 防止: リダイレクト時のスキーム検査、プライベートアドレス検出によるブロック。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip Bomb 対策）。
    - トラッキングパラメータ除去による URL 正規化と SHA-256 による記事 ID 生成（先頭32文字）。
    - テキスト前処理（URL 除去・空白正規化）。
    - raw_news / news_symbols テーブルへの冪等保存（INSERT ... ON CONFLICT DO NOTHING、INSERT ... RETURNING を利用）とチャンク化によるパフォーマンス改善。
    - 銘柄コード抽出ユーティリティ（4桁数字パターン、既知コードセットでフィルタ）。
    - 全ソースを巡回して収集する統合ジョブ run_news_collection を提供（各ソースの独立エラーハンドリング）。
- リサーチ / 特徴量・ファクター計算 (kabusys.research)
  - feature_exploration モジュール
    - calc_forward_returns: 指定日の終値を基準に複数ホライズン（デフォルト 1/5/21 営業日）に対する将来リターンを単一クエリで計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（ties の処理、3 件未満は None）。
    - rank: 同順位の平均ランクを返すランク関数（丸め誤差対策）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー計算。
    - 研究用関数は標準ライブラリのみを使用する方針（pandas 等に依存しない実装）。
  - factor_research モジュール
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を DuckDB の prices_daily を参照して計算。データ不足時に None を返す設計。
    - calc_volatility: atr_20（20日 ATR）, atr_pct, avg_turnover, volume_ratio を計算（true_range の NULL 伝播制御、カウントによる有効判定）。
    - calc_value: raw_financials と prices_daily を組み合わせ、per（株価/EPS）と roe を算出。target_date 以前の最新財務レコードを取得する処理を実装。
  - 研究用 API を一括で公開するパッケージ初期化（kabusys.research.__init__）。
- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema.md に基づいた 3 層（Raw / Processed / Feature / Execution）設計のための DDL 定義を開始。
  - raw_prices, raw_financials, raw_news のテーブル DDL を実装（主キー・型チェック・NOT NULL 等を定義）。
  - raw_executions テーブル定義の一部を含む（発注/約定関連のテーブル群の整備を想定）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector および RSS フェッチ周りで SSRF・XML Bomb・Gzip Bomb 対策を導入。
- J-Quants クライアントでトークンの取り扱いとリトライポリシーを明確化（401 時に自動リフレッシュを行い、無限再帰を回避）。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

注意事項 / 備考
- DuckDB 接続を引数で受け取る設計のため、実行環境での DB 初期化・接続の責務は利用者側にあります（kabusys.data.schema の DDL を用いた初期化を推奨）。
- research モジュール群は本番の発注 API にはアクセスしない方針で実装されています（Look-ahead Bias の防止・安全性の確保）。
- J-Quants API の利用には環境変数 JQUANTS_REFRESH_TOKEN 等の設定が必須です。設定が未完了の場合は Settings のプロパティアクセスで ValueError が発生します。

今後の予定（例）
- Execution 層の完全実装（発注 / 約定 / ポジション管理テーブルとロジック）。
- Processed / Feature レイヤーの SQL 化と ETL ジョブの提供。
- 単体テストと CI の整備、ドキュメント拡充（使い方・設定例・例外処理の動作など）。

-- end --
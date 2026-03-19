# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
安定バージョン: 0.1.0

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-19
初回公開リリース（ベース実装）。

### 追加 (Added)
- パッケージ骨格
  - kabusys パッケージを追加。サブモジュール: data, strategy, execution, monitoring（__all__ に公開）。
  - バージョン情報を __version__ = "0.1.0" として設定。

- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。
  - .env/.env.local の読み込み順を定義（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env 行パーサーの実装（export プレフィックス、クォート/エスケープ、コメント処理に対応）。
  - 必須環境変数取得用の _require と、env/log_level の妥当性検証を追加。
  - DB パス（DUCKDB_PATH / SQLITE_PATH）、Slack / J-Quants / kabu API 設定取得用プロパティを提供。

- データ取得（J-Quants クライアント: kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライ（指数バックオフ、最大3回）および 401 発生時の自動トークンリフレッシュ（1回）を実装。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（取引カレンダー）
  - DuckDB へ冪等に保存する save_* 関数:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 型変換ユーティリティ (_to_float/_to_int) を実装し、堅牢なデータ取り込みを実現。
  - fetched_at に UTC タイムスタンプを記録して Look-ahead Bias を回避。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集・前処理・DuckDB 保存パイプラインを実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - リダイレクト時のスキーム/ホスト検査と SSRF 対策（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカルかを判定し拒否するロジック。
    - 許容スキームは http/https のみ。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip の検査。
  - URL 正規化（トラッキングパラメータ除去、クエリ整列、フラグメント除去）と記事 ID（SHA-256 先頭32文字）生成。
  - 記事テキストの前処理（URL 除去、空白正規化）。
  - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING）と INSERT ... RETURNING による新規挿入 ID 取得。
  - 銘柄コード抽出（4桁数字パターン + known_codes フィルタ）と news_symbols への紐付け一括保存。
  - run_news_collection により複数ソースをまとめて収集・保存・紐付け可能。

- DuckDB スキーマ初期化（kabusys.data.schema）
  - DataSchema に基づく基本テーブルDDLを追加（raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。
  - Raw / Processed / Feature / Execution 層を想定した設計コメントを含む。

- リサーチモジュール（kabusys.research）
  - 特徴量探索・ファクター計算ユーティリティを実装。
  - feature_exploration:
    - calc_forward_returns: 指定日の終値から複数ホライズン先の将来リターンを一括で取得。
    - calc_ic: ファクターと将来リターン間のスピアマン IC（ランク相関）計算。データ不足や ties 対応。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸め処理で浮動小数点の ties を抑制）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を算出。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率などを算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新の target_date 以前の財務レコードを使用）。
  - DuckDB 接続を受け取る設計で本番APIや発注処理へアクセスしない（安全な研究モード）。

### 変更 (Changed)
- 初期リリースにつき、既存コードからの互換性変更はなし（初回追加）。

### 修正 (Fixed)
- 初期リリースにつき、既存不具合修正はなし。

### セキュリティ (Security)
- RSS 収集での SSRF 対策や defusedxml による XML パース、防御的なレスポンスサイズチェックを導入。
- J-Quants クライアントでのトークン管理と自動リフレッシュにより認証フローの堅牢性を確保。

### 既知の制約 / 注意事項
- research モジュールは標準ライブラリのみを想定した実装方針を採用しているため、高速化や大量データ処理で pandas 等への依存が必要な場合は別途検討が必要。
- save_* 系は DuckDB のテーブル定義（スキーマ）に依存するため、スキーマ変更時は対応が必要。
- _to_int の挙動: "1.0" のような小数表現は int に変換可能だが、小数部が 0 以外の文字列（例: "1.9"）は None を返す。取り込み元データに依存する挙動なので注意。

---

開発・運用に関する詳細は各モジュールの docstring とコード内コメントを参照してください。
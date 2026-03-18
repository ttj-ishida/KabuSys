# Changelog

すべての変更は「Keep a Changelog」の形式に準拠します。  
このファイルはリポジトリ内のコードから推測して作成した初期の変更履歴です。

## [0.1.0] - 2026-03-18
初回公開リリース。本リリースでは日本株自動売買システム「KabuSys」のコアライブラリ群の基礎機能を実装しています。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを定義（__version__ = "0.1.0"）。モジュール一覧を __all__ に公開（data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env 解析ロジック実装（export 形式対応、クォート/エスケープ/コメント処理、無効行スキップ）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants/GW/Slack/DB パス等の設定をプロパティ経由で取得可能に（必須キー取得時のエラー/検証含む）。
  - 環境（development/paper_trading/live）やログレベルの検証ロジックを追加。
- データ層（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - レート制限（120 req/min）を固定間隔スロットリングで実装する RateLimiter を導入。
    - HTTP リクエストの共通処理を実装（再試行・指数バックオフ・429 の Retry-After 優先・401 時のトークン自動更新）。
    - ページネーション対応の fetch_* 関数を実装:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務四半期データ）
      - fetch_market_calendar（JPX マーケットカレンダー）
    - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar（各関数は保存件数を返す）
    - 型変換ユーティリティ _to_float / _to_int を実装し堅牢なパースを提供。
    - id_token のモジュールレベルキャッシュを導入しページネーション間で共有。
  - ニュース収集（kabusys.data.news_collector）
    - RSS フィード取得・パースの実装（defusedxml 使用で安全にパース）。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url / _make_article_id、記事IDは SHA-256 の先頭32文字）。
    - SSRF 対策：スキーム検証、プライベートアドレス判定（_is_private_host）、リダイレクト検査ハンドラを導入。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES）・gzip 解凍後の検査など DoS 耐性を考慮。
    - テキスト前処理（URL 除去・空白正規化）。
    - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING RETURNING id）及び news_symbols への紐付け保存機能（チャンク挿入、トランザクション管理）。
    - 銘柄コード抽出ユーティリティ（4桁数字パターンと known_codes フィルタ）。
    - run_news_collection により複数ソースの統合収集ジョブを提供。
- 研究・特徴量計算（kabusys.research）
  - feature_exploration モジュール
    - calc_forward_returns（将来リターンを DuckDB の prices_daily を参照して計算）
    - calc_ic（Spearman ランク相関による Information Coefficient 計算）
    - factor_summary（基本統計量の計算）、rank（同順位は平均ランク）
    - 設計上、標準ライブラリのみで実装（pandas 未使用）で、prices_daily のみ参照（本番注文APIにアクセスしない）
  - factor_research モジュール
    - calc_momentum（1M/3M/6M リターン、200日移動平均乖離率）
    - calc_volatility（20日 ATR、相対ATR、20日平均売買代金、出来高比）
    - calc_value（PER・ROE の計算。raw_financials と prices_daily を参照）
    - 各関数は (date, code) キーの dict リストを返し、データ不足時は None を扱う設計。
  - research パッケージ __init__ で主要ユーティリティを公開（calc_momentum 等、zscore_normalize を含む）。
- DuckDB スキーマ（kabusys.data.schema）
  - Raw 層のテーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions の定義を含む（途中まで記載））。
  - スキーマ管理と初期化の基盤を作成。

### 変更 (Changed)
- 設計上の選択（ドキュメント相当の記述をコード中に含む）
  - Research / Data 層の関数は本番発注APIにはアクセスしない設計で、分析処理と実行処理を分離している。
  - DuckDB を主要なローカル DB として想定し、INSERT の冪等化や RETURNING で正確な挿入件数を取得するよう実装。
  - 外部依存を最小化（研究モジュールは pandas 等に依存せず標準ライブラリのみで実装）。
- セキュリティ・堅牢性強化
  - news_collector において XML パースは defusedxml を利用、SSRF 対策、応答サイズ検査を実装。
  - J-Quants クライアントでは認証トークン自動リフレッシュと再試行戦略を導入。

### 修正 (Fixed)
- 初期リリースのため特定のバグ修正履歴はなし（実装時点での注意点・防御的実装を多数導入）。

### 既知の制約・注意事項 (Known Issues / Notes)
- research モジュールは標準ライブラリで実装されているため、大規模データ処理時の性能改善には pandas 等の導入を検討する余地がある。
- schema モジュールの DDL は Raw 層の定義が中心で、Processed / Feature / Execution 層の完全な定義は今後追加予定（現在のファイルは一部まで定義あり）。
- J-Quants API のレート/リトライ挙動は実運用状況に応じて調整が必要な場合がある（バックオフ係数や最大試行回数など）。
- news_collector の _is_private_host は DNS 解決に失敗した場合に安全側（非プライベート）として扱うため、特殊ネットワーク環境では追加検証が必要となる可能性がある。
- Settings の必須キー未設定時は ValueError を送出するため、実行環境での .env 設定に注意。

---

今後のリリースでは、Processed/Feature 層の完全なスキーマ追加、strategy / execution / monitoring モジュールの具体的実装（発注ロジック・監視ダッシュボード連携など）、および性能・テストカバレッジの強化を予定しています。
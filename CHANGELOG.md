Changelog
=========
すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[未リリースの変更点]
-------------------
（なし）

0.1.0 - 2026-03-18
-----------------
初回リリース。KabuSys の基盤機能を実装しました。

Added
- パッケージ初期化
  - kabusys.__init__ によるバージョン管理（__version__ = "0.1.0"）と公開モジュール一覧の定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動検出するため、CWD に依存せず動作。
  - .env のパース機能強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメント処理（クォート外の # を考慮）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラスに主要設定をプロパティとして提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境 / ログレベル判定ユーティリティ等）。
  - 環境変数の必須チェック（未設定時は ValueError）。

- Data: J-Quants API クライアント (kabusys.data.jquants_client)
  - API 基本クライアントを実装（/token/auth_refresh, /prices/daily_quotes, /fins/statements, /markets/trading_calendar 等）。
  - レート制限対応: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライロジック: ネットワーク/サーバーエラーに対する指数バックオフ、最大再試行回数 3 回。
  - 401 レスポンス時の自動トークンリフレッシュ（1 回のみリトライ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応で複数ページを取得するロジックを実装。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。INSERT ... ON CONFLICT DO UPDATE により冪等性を確保。
  - 入力値変換ユーティリティ (_to_float, _to_int) を実装し、意図しない変換や空値に対して安全に None を返す設計。

- Data: ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得・パース、前処理、DuckDB への冪等保存機能を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト時のスキーム検証、プライベートアドレス検出によるブロック、_SSRFBlockRedirectHandler による事前検証。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査。
  - URL 正規化: トラッキングパラメータ（utm_* 等）の除去、ソートされたクエリ文字列、フラグメント削除。
  - 記事ID は正規化 URL の SHA-256 の先頭 32 文字で生成し冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）。
  - raw_news 保存時はチャンク化およびトランザクションで処理し、INSERT ... RETURNING で実際に挿入された記事IDを返却。
  - 銘柄コード抽出ユーティリティ（4 桁数字の検出と known_codes によるフィルタリング）と news_symbols への一括保存ロジックを実装。
  - run_news_collection により複数ソースの収集/保存/紐付けを統合して実行。

- Data: スキーマ定義 (kabusys.data.schema)
  - DuckDB 用のテーブル定義（Raw Layer の DDL）を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む基盤スキーマを追加。
  - スキーマ初期化用ユーティリティ（ログ出力あり）。

- Research: ファクター算出 & 特徴量探索 (kabusys.research)
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離率）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS 不在/0 の場合は None）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番口座や発注 API へはアクセスしない設計。
  - feature_exploration.py:
    - calc_forward_returns: 各ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括で DuckDB クエリで取得。
    - calc_ic: factor と forward return の Spearman ランク相関（IC）を実装（同順位は平均ランク処理、記録不足時は None を返す）。
    - rank: 同順位を平均ランクで処理するランク化ユーティリティ（round(v, 12) による丸めで浮動小数点誤差を緩和）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。
  - research パッケージの __init__ で主要関数をエクスポート。

- その他
  - research と data のユーティリティは外部ライブラリ（pandas 等）に依存しないよう、標準ライブラリ + duckdb による実装を優先。
  - strategy/execution パッケージ用のプレースホルダモジュールを追加（将来的な戦略実装・発注処理のための構成）。

Security
- ニュース収集で SSRF や XML 攻撃、巨大レスポンスを考慮した多層の防御を実装。
- J-Quants クライアントはトークン管理（自動更新）とレート制限・再試行戦略を備え、安全な API 取得を目指す。

Known limitations / Notes
- strategy/execution パッケージは初期状態で空の __init__ モジュールのみ。実際の取引ロジック・発注実装は未実装。
- DuckDB スキーマ定義は Raw Layer を中心に実装済み。Processed / Feature / Execution 層の完全な DDL は今後拡張予定。
- news_collector は defusedxml に依存（XML の安全なパースのため）。DuckDB へは直接接続するため、DB スキーマの事前準備が必要。
- J-Quants クライアントは API のレスポンス仕様に依存するため、実運用前に API キー設定・動作確認を推奨。

Authors
- KabuSys 開発チーム（コードベースより推測して記載）

ライセンス
- 本 CHANGELOG はコードから推測して作成しています。実際のライセンス表記はリポジトリの LICENSE を参照してください。
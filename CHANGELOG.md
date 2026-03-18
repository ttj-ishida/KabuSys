Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。初期リリース v0.1.0 の変更点を、提供されたコードベースから推測して記載しています。

CHANGELOG.md
=============

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に従い、セマンティック バージョニングを採用します。

目次
----
- [Unreleased](#unreleased)
- [0.1.0 - 2026-03-18](#010---2026-03-18)

Unreleased
----------
（未リリースの変更はここに記載）

0.1.0 - 2026-03-18
------------------
初回公開リリース。日本株自動売買・データ収集・リサーチ用の基盤ライブラリを実装。

Added
-----
- パッケージ基盤
  - kabusys パッケージ（__version__ = 0.1.0）。
  - パッケージ公開 API に data, strategy, execution, monitoring を __all__ で公開。

- 設定管理
  - kabusys.config: 環境変数・設定管理モジュールを追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、行内コメント等に対応。
    - .env.local は .env の上書き（ただし OS 環境変数は保護）として読み込む実装。
    - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、データベースパス（DuckDB / SQLite）などのプロパティを取得。KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装（許容値チェック）。

- データ取得・永続化（data）
  - kabusys.data.jquants_client:
    - J-Quants API クライアントを実装。
    - 固定間隔の RateLimiter（120 req/min に対応）、ページネーション対応、最大 3 回の再試行（指数バックオフ）を実装。
    - 401 発生時にリフレッシュトークンから id_token を自動リフレッシュして再試行（1回のみ）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar の取得関数。
    - save_daily_quotes / save_financial_statements / save_market_calendar の DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装。
    - 文字列 -> float/int 変換ユーティリティ（_to_float / _to_int）を実装し、不正値や空値を安全に扱う。
    - 実装は標準ライブラリの urllib を利用。

  - kabusys.data.news_collector:
    - RSS フィードからのニュース収集モジュールを実装。
    - feed 取得・XML パース（defusedxml を利用して XML Bomb 等に対策）、gzip 解凍、最大受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）などの保護を実装。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス検査、リダイレクト時の事前検証ハンドラを導入。
    - URL 正規化（トラッキングパラメータ除去、フラグメント除去、ソートされたクエリ）と記事ID生成（正規化 URL の SHA-256 先頭32文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING RETURNING id）をチャンク・トランザクションで行い、実際に挿入された記事IDのリストを返す。
    - news_symbols（記事と銘柄の紐付け）保存用のバルク挿入処理（重複除去・チャンク処理）を実装。
    - 銘柄コード抽出（4桁数字、known_codes フィルタ）機能を実装。

  - kabusys.data.schema:
    - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層の方針）。
    - raw_prices / raw_financials / raw_news / raw_executions などの CREATE TABLE DDL を定義（NOT NULL / CHECK / PRIMARY KEY を含む）。

- リサーチ（research）
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR、平均売買代金、出来高比）、バリュー（PER, ROE）計算関数を DuckDB SQL を利用して実装。
    - データ不足時は None を返す扱い、スキャン範囲バッファ（カレンダー日で営業日欠落を吸収）を考慮。
    - prices_daily / raw_financials テーブルのみを参照し、本番発注 API にはアクセスしない設計。

  - kabusys.research.feature_exploration:
    - 将来リターン calc_forward_returns（指定日から各ホライズン後のリターンを計算、SQL LEAD を使用）。
    - Information Coefficient（Spearman の ρ）を計算する calc_ic。rank ユーティリティを同梱（同順位は平均ランク、丸めで ties の検出漏れを抑制）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - これらは pandas 等に依存せず、標準ライブラリと DuckDB を用いて実装。

  - kabusys.research.__init__:
    - 主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- パッケージ構成
  - strategy, execution, monitoring パッケージの __init__ を配置（将来的な拡張ポイント）。

Security
--------
- RSS パーサに defusedxml を利用し、XML による攻撃を軽減。
- news_collector: SSRF 対策（スキーム検証、プライベート IP/ホスト検査、リダイレクト検査）、レスポンスサイズ上限、gzip 解凍後のサイズチェックを実装。
- jquants_client: API の再試行・レートリミット・トークンリフレッシュを実装し、過負荷・不正な認証状況に対する堅牢性を向上。

Notes / Implementation details
------------------------------
- 自動 .env ロードはプロジェクトルート検出に依存するため、配布後や異なるインストール構成での挙動確認が必要（CWD には依存しない探索を行う）。
- jquants_client は urllib ベースで実装されており、外部 HTTP クライアント（requests 等）に依存していない。テストや拡張で差し替えを検討可能。
- research モジュールは pandas 等に依存しない方針で実装されているため、大量データ処理時のパフォーマンス評価は行う必要がある。
- news_collector の記事 ID は正規化 URL に依存するため、URL の正規化ロジック変更は既存 ID に影響を与える可能性がある。

Known issues / Limitations
--------------------------
- 一部テーブル定義・DDL（例: raw_executions の DDL の一部）は実装ファイルで継続中／切り出し途中の可能性があるため、スキーマの完全性は実運用前に確認が必要。
- calc_forward_returns / factor 計算は prices_daily に十分な過去データがあることを前提としている。営業日とカレンダー日の関係による端数処理は注意が必要。
- ネットワーク等の実環境では、J-Quants のレート制限・Retry-After ヘッダ等に合わせた動作確認が必要。

Contributors
------------
- 初期実装（提供されたコードベース）に基づくドキュメント作成

---

この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴やリリースポリシーに合わせて補正・詳細化してください。必要であれば、各関数やモジュールごとの変更点をさらに細かく分けたセクション（Added / Changed / Fixed）を追記します。
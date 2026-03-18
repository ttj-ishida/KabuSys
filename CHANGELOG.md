# Changelog

すべての変更は Keep a Changelog の形式に従い、逆順（新しいリリースが上）で記載しています。  
フォーマット: 変更種別 (Added / Changed / Fixed / Security) に分類しています。

## [0.1.0] - 2026-03-18
初回リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を追加。
  - パッケージ API エントリポイントを定義（kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring を公開）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出ロジック: 現在のファイル位置から .git または pyproject.toml を探索してルートを決定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ: export プレフィックス、クォート文字列、インラインコメント等に対応する堅牢なパーサを実装。
  - Settings クラスを提供:
    - J-Quants, kabu API, Slack, DB パス等の必須/省略時デフォルト設定をプロパティとして公開。
    - KABUSYS_ENV（development / paper_trading / live）の検証と LOG_LEVEL の検証を実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- Data 層（kabusys.data）
  - J-Quants クライアント (kabusys.data.jquants_client)
    - API リクエストユーティリティを実装:
      - 固定間隔スロットリングによるレート制限（デフォルト 120 req/min）。
      - 最大 3 回の再試行（指数バックオフ）、408/429/5xx をリトライ対象に設定。
      - 401 受信時はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ。
      - ページネーション対応（pagination_key を使って全ページを取得）。
      - JSON デコードエラーやネットワークエラーに対する例外処理・ログ出力。
    - 認証ユーティリティ: get_id_token（リフレッシュトークンから ID トークンを取得）。
    - データ取得関数:
      - fetch_daily_quotes（株価日足・ページネーション対応）
      - fetch_financial_statements（財務四半期データ）
      - fetch_market_calendar（JPX 取引カレンダー）
    - DuckDB へ保存する関数（冪等性を考慮）:
      - save_daily_quotes → raw_prices テーブルへ ON CONFLICT DO UPDATE。
      - save_financial_statements → raw_financials テーブルへ ON CONFLICT DO UPDATE。
      - save_market_calendar → market_calendar テーブルへ ON CONFLICT DO UPDATE。
    - モジュールレベルの ID トークンキャッシュを導入し、ページネーションや連続呼び出しでトークンを再利用。

  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィードからの記事収集と DuckDB への保存を実装。
    - セキュリティと堅牢性の対策:
      - defusedxml による XML パース（XML Bomb 等対策）。
      - HTTP リダイレクト検査と SSRF 対策（リダイレクト先のスキーム/ホストを検証）。
      - ホストのプライベート IP チェック（DNS 解決して A/AAAA を検査、private/loopback/link-local/multicast を拒否）。
      - 受信バイト数上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 展開後のサイズチェック（Gzip bomb 対策）。
      - 許可スキームは http / https のみ。
    - URL 正規化と記事 ID 生成:
      - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去して URL を正規化。
      - SHA-256（正規化 URL）先頭32文字を記事 ID として採用し冪等性を保証。
    - テキスト前処理ユーティリティ（URL 除去、空白正規化）。
    - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes によるフィルタリング。
    - DB 保存関数:
      - save_raw_news: INSERT ... RETURNING を用いて実際に挿入された記事 ID を返却。チャンクバルク挿入、トランザクション管理。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付け保存（重複排除、RETURNING による正確な挿入件数取得）。

  - DuckDB スキーマ定義 (kabusys.data.schema)
    - Raw Layer の主要テーブル DDL を定義:
      - raw_prices, raw_financials, raw_news, raw_executions（スキーマ定義の一部が含まれる）。
    - スキーマ初期化のための基盤を提供。

- Research 層（kabusys.research）
  - 特徴量探索モジュール (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21 営業日）の将来リターンを DuckDB の prices_daily を参照して計算。
      - SQL で一度にまとめて取得し、performance に配慮。
      - horizons の検証（正の整数かつ <= 252）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。欠損・非有限値を除外し、有効レコード < 3 の場合は None を返す。
    - rank: 同順位は平均ランクで処理、丸め誤差対策に round(..., 12) を使用。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーユーティリティ（None 値除外）。
  - ファクター計算モジュール (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率 (ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials の最新財務データ（target_date 以前）と当日の株価から PER / ROE を計算（EPS が 0/欠損の場合は PER を None）。
    - 上記関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照する設計。外部 API へのアクセスは行わない旨を明確化。
    - 各関数は (date, code) をキーとする辞書リストを返す。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集で複数の SSRF/XML/DoS 対策を導入（defusedxml、リダイレクト先検査、プライベートアドレス拒否、受信サイズ上限、gzip 展開後チェック）。
- J-Quants クライアントにおいて再試行時の扱いやトークンリフレッシュ処理で安全側の実装を行い、無限再帰を回避。

### Notes / Known limitations
- strategy/ execution / monitoring パッケージは空の初期モジュールのみを提供（実装は今後追加予定）。
- DuckDB スキーマ定義は Raw Layer の主要な DDL を含むが、リポジトリ内の一部スキーマ定義は継続して追加される想定。
- J-Quants クライアントは urllib を用いた実装であり、非同期処理や高スループット用途では追加改良（並列化や接続プーリング等）が必要。
- news_collector の既定 RSS ソースは Yahoo Finance のビジネスカテゴリのみ。運用時は sources 引数でカスタムソースを指定することを推奨。

---

もし特定の変更点（例: 各関数の入力/出力例、環境変数一覧、DB スキーマ全体など）をより詳しく CHANGELOG に追記したい場合は知らせてください。必要に応じてやさしい日本語で注釈や運用上の注意点も追加します。
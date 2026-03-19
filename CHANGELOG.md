# Changelog

すべての重要な変更点をこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠します。

現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-19

### 追加（Added）
- パッケージ初期実装を追加。
  - パッケージ名: kabusys
  - モジュール構成（主要モジュール）:
    - kabusys.config: 環境変数 / .env 管理（自動ロード機能、プロジェクトルート検出）
    - kabusys.data:
      - jquants_client: J-Quants API クライアント（認証、ページネーション、リトライ、レート制御、DuckDB への冪等保存）
      - news_collector: RSS ベースのニュース収集器（URL 正規化、記事ID生成、SSRF/サイズ/ZIP/XML 対策、DuckDB 保存、銘柄紐付け）
      - schema: DuckDB 用スキーマ定義（raw layer を中心にテーブル定義を用意）
    - kabusys.research:
      - feature_exploration: 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー、ランク付けユーティリティ
      - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を参照）
    - kabusys.strategy, kabusys.execution: パッケージ公開インターフェイスを準備（現時点では初期ファイルを配置）
  - パッケージ初期バージョンは src/kabusys/__init__.py にて `__version__ = "0.1.0"` を設定。

- 環境設定（kabusys.config.Settings）
  - .env ファイル（.env, .env.local）の自動読み込み機能を実装（優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出（.git または pyproject.toml を探索）により CWD 非依存での自動ロードを実現。
  - .env のパースはクォート、エスケープ、コメント処理、`export KEY=val` 形式に対応。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供（テスト向け等）。
  - 必須環境変数取得用 `_require` と Settings のプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_*、DB パス等）を提供。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（許容値の検証）を実装。

- J-Quants API クライアント（kab usys.data.jquants_client）
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回）を実装。HTTP 408/429/5xx を再試行対象とする。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的に ID トークンを更新して 1 回だけリトライする仕組みを実装。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes (OHLCV)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を利用して重複を排除
  - 入力値変換ユーティリティ `_to_float`, `_to_int` を実装（堅牢な変換と空値ハンドリング）。

- ニュース収集（kab usys.data.news_collector）
  - RSS フィード取得とパース機能を実装（デフォルトソース: Yahoo Finance ビジネスカテゴリ）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）
    - SSRF 防止: リダイレクト時のスキーム検査、ホストがプライベートアドレスか判定してアクセス拒否
    - URL スキーム検証（http/https のみ許可）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再検査（Gzip bomb 対策）
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID の SHA-256 ベース生成（先頭32文字）
  - テキスト前処理（URL 除去・空白正規化）と RSS pubDate の安全なパース（フォールバックに現在時刻）
  - DB 保存:
    - save_raw_news: チャンク INSERT + TRANSACTION + INSERT ... RETURNING id で新規挿入ID を正確に取得
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを冪等に保存
  - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数字、既知コードとの照合）
  - run_news_collection: 複数ソースの収集をまとめる統合ジョブ（ソース毎に個別にエラーハンドリング、銘柄紐付け）

- リサーチ系（kab usys.research）
  - feature_exploration:
    - calc_forward_returns: target_date を基準に複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算
    - calc_ic: スピアマン順位相関（ランク）を計算。無効/欠損値除外、サンプル数不足時は None を返す
    - rank: 同順位は平均ランク扱い（丸めを用いた ties 処理）
    - factor_summary: count/mean/std/min/max/median を計算
    - 実装は標準ライブラリのみで行い pandas 等に依存しない設計
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（MA200 との乖離）
    - calc_volatility: ATR20（true range の取り扱いで NULL 伝播を考慮）、atr_pct、avg_turnover、volume_ratio
    - calc_value: raw_financials を参照して per (EPS を用いる) / roe を計算（最新の報告日以前の財務データを取得）
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し本番 API にはアクセスしない

- スキーマ（kab usys.data.schema）
  - DuckDB 用のテーブル DDL を追加（raw_prices, raw_financials, raw_news, raw_executions など raw layer の定義を含む）
  - スキーマ初期化のための DDL 管理を準備

### 変更（Changed）
- ー（初回リリースのため変更履歴はなし）

### 修正（Fixed）
- ー（初回リリースのため修正履歴はなし）

### セキュリティ（Security）
- news_collector:
  - defusedxml による XML パースを採用し、XML 関連の脆弱性（XML bomb 等）を軽減
  - SSRF 対策の実装（最終URL とリダイレクト先の検証、プライベートアドレス判定）
  - レスポンスサイズ制限と gzip 解凍後の再検査によりメモリDoS を緩和

### 既知の制限・注意事項（Notes）
- research モジュールは pandas 等の外部解析ライブラリに依存せず標準ライブラリで実装されているため、データサイズや集計複雑度によっては性能に制約がある可能性があります。大規模データでは DuckDB 側の SQL クエリ最適化を優先してください。
- kabusys.strategy / kabusys.execution の各 __init__ は配置済みだが、実装ファイル（戦略ロジック・発注実装）は本リリースに含まれていません（プレースホルダ）。
- research.__init__ は zscore_normalize を kabusys.data.stats から import していますが、data.stats の実装本体は本差分では提示されていません。実行環境では該当モジュールが必要です。
- DuckDB のテーブル名に prices_daily 等、processed layer のテーブルが前提になっています。データ投入時は schema に合わせた初期化を行ってください。
- J-Quants API クライアントでは rate limit を守る固定間隔方式を採用しています。非常に高頻度並列アクセスがある場合は追加の並列制御が必要になることがあります。
- .env 自動ロードはプロジェクトルート検出に依存します。配布後やインストール環境での挙動に不安がある場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自前で環境設定を制御してください。

### 互換性の破壊（Breaking Changes）
- なし（初回リリース）

---

将来のリリースでは以下を想定しています（計画）:
- strategy / execution の具体的な戦略クラスおよび発注・ポジション管理ロジックの実装
- monitoring（モニタリング・アラート連携）の実装
- data.stats の実体（zscore_normalize 等）とそれに伴うユーティリティの充実
- 単体テスト・統合テストの追加と CI 設定

ご要望があれば、各追加機能についてより詳細な変更点（ファイルごとの差分説明や使用例）を追記します。
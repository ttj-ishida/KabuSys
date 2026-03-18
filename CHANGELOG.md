# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このファイルはコードベースから推測して作成した初期リリース相当の変更履歴です。

## [Unreleased]
- 今後の変更・修正をここに記載します。

## [0.1.0] - 2026-03-18
初回リリース（コードベースから推測してまとめた機能群）。

### Added
- パッケージ基盤
  - パッケージ初期化 (src/kabusys/__init__.py) を追加。公開モジュールとして data/strategy/execution/monitoring を想定。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ から親ディレクトリを辿り .git または pyproject.toml を基準に判定。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env の行パース実装（export プレフィックス対応、クォート・エスケープ処理、インラインコメント処理）。
  - 環境設定取得用 Settings クラスを提供。J-Quants / kabu / Slack / DB パスなどのプロパティを定義。
    - バリデーション: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL に対する検証。
    - デフォルト値: KABUSYS_API_BASE_URL のデフォルトやデータベースパス（DuckDB/SQLite）など。

- データ取得／保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
    - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を導入。
    - リトライロジック（指数バックオフ／最大3回）を実装。408/429/5xx をリトライ対象に指定、429 時は Retry-After を考慮。
    - 401 受信時にリフレッシュトークンで自動的に id_token を更新して1回だけリトライ。
    - ページネーション対応で /prices/daily_quotes や /fins/statements などを全件取得。
    - 取得タイミングを UTC で記録（fetched_at）して Look-ahead bias の追跡性を確保。
  - DuckDB へ冪等的に保存する関数を提供（ON CONFLICT DO UPDATE を使用）。
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
  - 入出力の堅牢性向上: _to_float / _to_int といった変換ユーティリティを実装し、不正な値を安全に扱う。

- ニュース収集（RSS） (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news, news_symbols に保存するパイプラインを提供。
    - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ削除・ソート、フラグメント除去）。
    - 記事ID は正規化 URL の SHA-256 先頭32文字で生成し冪等性を担保。
    - XML パースに defusedxml を利用して XML Bomb 等に対処。
    - SSRF 対策:
      - fetch 時にホストがプライベート/ループバック/リンクローカルでないか検査。
      - リダイレクト時にもスキームとホスト検証を行うカスタム RedirectHandler を導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）の検査（Content-Length チェック、実際に読み込んで超過検出）。
    - gzip 解凍対応と Gzip-bomb 対策（解凍後のサイズ検査）。
    - テキスト前処理（URL 除去・空白正規化）を実装。
    - 銘柄コード抽出（4桁数字）機能と、既知コードセットに対するフィルタリングを実装。
    - DB への保存はチャンク化してトランザクションでまとめ、INSERT ... RETURNING を用いて新規挿入数を正確に返す。
  - デフォルト RSS ソースとして Yahoo Finance のビジネス RSS を設定（DEFAULT_RSS_SOURCES）。

- 研究（Research）モジュール (src/kabusys/research/)
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1SQLでまとめて取得）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンの順位相関、ランク化ユーティリティ rank を含む）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median を算出）。
    - 設計上 pandas 等に依存せず標準ライブラリのみで実装。
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M リターン、MA200 乖離率）計算 calc_momentum。
    - ボラティリティ／流動性（20日 ATR、ATR比率、平均売買代金、出来高比率）計算 calc_volatility。
    - バリュー（PER/ROE）計算 calc_value（raw_financials と prices_daily を組合せ）。
    - DuckDB に対して SQL ウィンドウ関数を活用して効率的に計算。
  - research パッケージ初期公開 API を定義（__all__）。

- スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用のテーブル DDL を定義（Raw Layer の raw_prices / raw_financials / raw_news / raw_executions 等）。
  - 各テーブルに適切な型チェック制約（CHECK）や PRIMARY KEY を設定してデータ整合性を強化。

### Security
- defusedxml を用いた XML パースで XML 関連の攻撃を低減。
- RSS フェッチ時の SSRF 対策（プライベートアドレス除外、リダイレクト検査、スキーム検証）。
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を実装。

### Documentation
- 各モジュールに詳細な docstring が付与され、設計方針・注意点・引数/戻り値の説明が記載されている（環境設定、データ取得、ニュース収集、研究アルゴリズム等）。

### Known limitations / Notes
- 外部依存の最小化が意図されており、研究モジュールは pandas 等に依存しない実装になっているが、実行時は duckdb と defusedxml が必要。
- 一部ファイル（例: src/kabusys/data/schema.py の raw_executions の定義）がスニペットで途中までの提供であり、実運用では完全なスキーマ定義が必要。
- ニュースの pubDate パースに失敗した場合は現在時刻で代替する実装になっている（ログ出力あり）。
- jquants_client のトークンキャッシュはモジュール単位の簡易キャッシュであり、長期運用ではトークン失効やマルチプロセス環境の考慮が必要。

### Breaking Changes
- 初回リリースのため該当なし。

---

この CHANGELOG はソースの実装と docstring から推測して作成しています。細かい挙動や追加のユーティリティ、完全なスキーマ定義などは実際のリポジトリとドキュメントを参照のうえ、必要に応じて更新してください。
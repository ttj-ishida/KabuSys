# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-19

初回リリース — 日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装しました。以下はコードベースから推測してまとめた主な追加点・設計上の要点です。

### Added
- パッケージ基盤
  - pakage 初期化: kabusys パッケージ（__version__ = 0.1.0）と主要サブパッケージのエクスポート設定（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しない自動ロードが可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env（既存環境変数は保護される）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサを実装（コメント、export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント等を考慮）。
  - 必須環境変数取得ヘルパ（_require）と Settings クラスを提供。主な設定キー（未設定時は例外）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DBパス等のデフォルト値:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
  - 環境値検証:
    - KABUSYS_ENV は development/paper_trading/live のみ許可
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 発生時は自動でリフレッシュトークンを使って ID トークンを取得して1回リトライ。
    - ページネーション対応（pagination_key を利用して連続取得）。
    - データ保存ユーティリティ（DuckDB への save_* 関数）:
      - save_daily_quotes: raw_prices へ冪等保存（ON CONFLICT DO UPDATE）
      - save_financial_statements: raw_financials へ冪等保存
      - save_market_calendar: market_calendar へ冪等保存
    - データ変換ユーティリティ: _to_float / _to_int（文字列や空値の安全な変換）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプラインを実装。
    - RSS 取得・XML パース（defusedxml を利用して XML Bomb 等に対策）。
    - gzip 圧縮対応、レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10 MB、解凍後の再チェックを含む）。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
    - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - SSRF 対策:
      - リダイレクト先のスキーム検証とプライベートアドレス検査用ハンドラ（_SSRFBlockRedirectHandler）。
      - 初回ホスト検証（ドメインの DNS 解決結果を検査してプライベート/ループバック等を拒否）。
    - テキスト前処理（URL除去、空白正規化）。
    - raw_news へのバルク挿入（チャンク単位、INSERT ... RETURNING を利用）と news_symbols への銘柄紐付けの一括保存。
    - 銘柄コード抽出ヘルパ（4桁数字を known_codes と照合して抽出）。
    - run_news_collection: 複数ソースの収集を統合し、ソース単位でのエラーハンドリングを行う。

- DuckDB スキーマ初期化（kabusys.data.schema）
  - DataSchema に基づくテーブル定義を実装（Raw Layer を中心に定義）。
    - raw_prices, raw_financials, raw_news, raw_executions などの DDL を含む（カラム型・制約・PRIMARY KEY 等を定義）。
  - スキーマは初期化可能で、データ取り込み用の土台を提供。

- リサーチ機能（kabusys.research）
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定日の終値から各ホライズン（例: 1/5/21 営業日）先のリターンを一括で取得する関数。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を返す。
    - rank: 同順位の平均ランクを扱うランク関数（丸め処理で ties の検出精度向上）。
    - 設計上、標準ライブラリのみで実装され、DuckDB の prices_daily テーブルを参照する想定（外部 API にアクセスしない）。
  - ファクター計算（factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。200日移動平均のカウント不足時は None を返す。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率などの算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が 0 または欠損なら None）および ROE を算出。
    - すべて DuckDB 接続を受け取り SQL ウィンドウ関数等で計算（外部アクセスなし）。
  - リサーチ __init__ で主要関数を公開（calc_momentum 等と zscore_normalize の再エクスポート）。

### Security
- RSS フィード取得に対する SSRF 対策を導入（スキームチェック、プライベート IP 判定、リダイレクト時の再検査）。
- XML パースに defusedxml を利用して安全性を高める。
- J-Quants クライアントは認証トークンの自動リフレッシュをサポートし、401 での無限再帰を防止する設計。

### Performance / Reliability
- J-Quants API クライアントにレートリミッタとリトライ（指数バックオフ）を導入し、API レート制限・一時的エラーに耐性を持たせている。
- 大量挿入処理はチャンク化（INSERT チャンク）とトランザクション単位で行い、DB 書き込みオーバーヘッドを低減。
- news_collector は Content-Length と読み込みバイト数でレスポンスサイズを検査し、メモリ DoS を軽減。

### Notes / Migration
- 必須の環境変数を設定しないと起動時や各機能呼び出し時に例外を投げます。特に下記は必須:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- .env 自動読み込みはプロジェクトルートの検出に依存します（.git または pyproject.toml が必要）。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / raw テーブルのスキーマは既定値で作成されるため、既存 DB との互換性に注意してください（主に初期リリースのため将来的にスキーマ変更の可能性あり）。

### Known limitations
- research モジュールは標準ライブラリで実装されているため、大量データに対するメモリ効率や高度な統計処理は将来的に pandas など導入が検討される可能性があります（現在は外部依存を避ける設計）。
- news_collector の銘柄抽出は単純な4桁数字パターンに依存しており、より高度な NER や曖昧マッチングは未実装。
- schema.py の Execution / Feature レイヤー定義は将来拡張される想定（本リリースでは主に Raw Layer が中心）。

---

この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のリリースノートや追加の変更点がある場合は適宜更新してください。
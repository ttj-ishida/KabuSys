# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-19

初回公開リリース。パッケージ全体のコア機能を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ初期化
  - kabusys パッケージの基本定義を追加（src/kabusys/__init__.py）。
  - エクスポート対象モジュール: data, strategy, execution, monitoring。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD に依存しない自動ロードを実現。
  - .env/.env.local の読み込み順序（OS 環境 > .env.local > .env）、override と protected（OS 環境を上書きしない保護機能）を実装。
  - 行パーサを実装（コメント行、export プレフィックス、クォート内のエスケープ、インラインコメント処理などに対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 必須設定取得時に未設定なら ValueError を投げる _require() 実装。
  - 利用可能な環境値（development, paper_trading, live）やログレベル検証を実装。
  - Settings クラスに J-Quants / kabu API / Slack / DB パス（DuckDB, SQLite）関連プロパティを実装。

- データ取得クライアント - J-Quants（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar 等）。
  - レート制限（120 req/min）に従う固定間隔スロットリング（RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回。対象: 408/429/5xx 等）。429 の場合は Retry-After を優先。
  - 401 を検出した場合、自動でリフレッシュトークンを用いて ID トークンを更新して 1 回リトライする仕組み。
  - ページネーション対応（pagination_key のループ）。
  - DuckDB への永続化用関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）を採用。
  - 文字列→数値の安全変換ユーティリティ（_to_float, _to_int）を実装。PK 欠損行のスキップとログ出力。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードの取得と raw_news/raw_symbols への保存フローを実装。
  - 記事ID を URL 正規化（utm 等のパラメータ除去）後の SHA-256（先頭32文字）で生成し冪等性を担保。
  - defusedxml を用いた安全な XML パース（XML Bomb 等に対応）。
  - SSRF 対策:
    - URL スキーム検査（http/https のみ許可）
    - リダイレクト先のスキーム/ホスト検査（ホストがプライベート/ループバック/リンクローカルであれば拒否）
    - カレント接続での最終 URL の再検証
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策（Content-Length チェック + 実際の読み取り上限 + gzip 解凍後サイズ検査）。
  - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数字、known_codes に基づくフィルタ）。
  - DB 保存はチャンク化と1トランザクション（一括 INSERT + RETURNING）で実装し、実際に挿入された id/件数を返す。
  - run_news_collection により複数ソースを順次処理し、ソース単位でのエラーハンドリングを行う。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw 層のテーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions （部分実装）など）。
  - DataSchema に基づく3層（Raw / Processed / Feature）設計方針を明記。

- 研究・特徴量探索（src/kabusys/research/）
  - feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1 クエリで取得、欠損時は None）。
    - IC 計算 calc_ic（スピアマンのランク相関、同順位は平均ランク、有効レコードが3未満なら None）。
    - ランク変換 util rank（丸めによる ties 検出対策）。
    - factor_summary（count/mean/std/min/max/median を標準ライブラリのみで計算）。
    - 研究モジュールは DuckDB の prices_daily テーブルのみ参照し外部 API にはアクセスしない設計。
  - factor_research.py:
    - モメンタム計算 calc_momentum（1M/3M/6M リターン、MA200 乖離、データ不足時は None）。
    - ボラティリティ/流動性 calc_volatility（20日 ATR / 相対 ATR / 20日平均売買代金 / 出来高比率、true_range の NULL 伝播制御）。
    - バリュー calc_value（raw_financials から直近財務データを取得し PER/ROE を算出、EPS 欠損なら None）。
    - 各関数は DuckDB 接続を受け取り SQL と組み合わせて処理（外部ライブラリに依存しない実装）。
  - research パッケージの __init__ で主要関数を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Fixed
- （初版のため既存バグ修正履歴はなし。ただし多くの関数で不正入力に対する検証・保護処理を追加）

### Security
- RSS パーサで defusedxml を使用し XML 攻撃を防止。
- RSS フェッチで SSRF 対策を実装（スキーム検証、プライベートアドレス拒否、リダイレクト時の検査）。
- API クライアントでトークンリフレッシュ時の無限ループを防ぐ設計（allow_refresh フラグ、1 回だけのリフレッシュ許可）。

### Performance / Reliability
- J-Quants クライアントで固定間隔レートリミッタを導入しレート超過を回避。
- API リトライで指数バックオフを採用し一時的な障害に耐性を持たせる。
- DB バルク挿入をチャンク化して SQL 長やパラメータ数の制約に対応。
- News collector / save_* 関数は ON CONFLICT を用いた冪等保存を行う。

### Known issues / Limitations
- research モジュールは DuckDB テーブル（prices_daily, raw_financials 等）が存在する前提。スキーマ初期化とデータ収集が必要。
- schema.py の raw_executions テーブル定義がソース内で途中まで（切り出し）となっているが、設計として実行取引履歴を格納する意図あり。実装を継続する必要あり。
- calc_forward_returns / factor 計算は営業日ベース（連続するレコード数）でホライズンを扱うため、カレンダー日数の穴（祝日等）に注意が必要。
- news_collector の extract_stock_codes は単純に 4 桁数字を抽出するため、誤検出（無関係な4桁数字）が発生する可能性あり。known_codes によるフィルタリングで緩和可能。
- 設定値の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は環境変数が未設定だと例外となるため、運用前に .env 作成または環境変数設定が必要。

---

今後の予定（例）
- schema の残りテーブル（Processed / Feature / Execution 層）の完全実装。
- strategy / execution モジュールの具体的な戦略実装と発注ロジック（kabuステーション連携）。
- 単体テスト・統合テストの追加と CI パイプライン構築。
- news_collector の自然言語処理強化（形態素分解による銘柄名抽出など）。

もしリリースノートをより詳細に（ファイルごとの差分ベース、コミットハッシュ付き等）したい場合は、追加でその観点に沿って作成します。
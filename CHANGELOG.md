# Keep a Changelog

すべての変更は慣例に従い記載しています。ここではコードベースの初期リリースとして観察可能な機能・設計上の追加点・注意点をまとめています。

## [0.1.0] - 2026-03-18

### Added
- パッケージの初期公開
  - パッケージメタ情報: kabusys v0.1.0（src/kabusys/__init__.py）

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルと環境変数の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env 行のパースロジックを実装（コメント、export プレフィックス、シングル/ダブルクォートおよびエスケープ対応、インラインコメント判定など）。
  - 設定ラッパー Settings を提供（J-Quants / kabuAPI / Slack / DB パス / 環境種別・ログレベル判定など）。必須値取得時は未設定で ValueError を送出。
  - 有効な環境値・ログレベルの検証（不正値は例外）。

- データ取得・保存（src/kabusys/data/）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - RateLimiter による固定間隔スロットリング（120 req/min を想定）。
    - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象、429 の Retry-After を優先）。
    - 401 受信時の ID トークン自動リフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements（pagination_key を追跡）。
    - JPX マーケットカレンダー取得 (fetch_market_calendar)。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。INSERT ... ON CONFLICT DO UPDATE による上書きで重複除去。
    - 数値変換ユーティリティ _to_float / _to_int（安全な None 返却、"1.0" などの扱いに注意）。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード取得(fetch_rss)、記事前処理(preprocess_text) と記事ID生成(_make_article_id：正規化 URL の SHA-256 先頭32文字)。
    - defusedxml を用いた安全な XML パース、gzip 解凍時のサイズ検査（Gzip bomb 対策）。
    - SSRF 対策: URL スキーム検証、リダイレクト時の検査用ハンドラ（_SSRFBlockRedirectHandler）、ホストのプライベートアドレス判定(_is_private_host)。
    - 受信サイズ上限 (MAX_RESPONSE_BYTES=10MB) の厳格なチェック。
    - raw_news / news_symbols への冪等保存（save_raw_news はチャンク INSERT + INSERT ... RETURNING id を用いて新規挿入IDを返す。save_news_symbols/_save_news_symbols_bulk は一括処理と ON CONFLICT で重複回避）。
    - 記事からの銘柄コード抽出機能（extract_stock_codes: 4桁数字パターン + known_codes によるフィルタ）。
    - run_news_collection により複数ソースを順次処理し、個別ソースの失敗は他ソースに影響させない設計。

  - スキーマ定義（src/kabusys/data/schema.py）
    - DuckDB 用の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等の Raw Layer テーブル定義を含む）。
    - テーブルの制約・型チェックを含む初期スキーマ（PRIMARY KEY、CHECK、DEFAULT など）。

- リサーチ（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200日移動平均乖離を計算。データ不足時は None。
    - ボラティリティ・流動性（calc_volatility）: 20日 ATR、ATR/終値比、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に扱う。
    - バリュー（calc_value）: raw_financials から直近財務を取得し PER/ROE を計算（EPS=0/欠損は None）。
    - DuckDB の prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない設計。

  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: target_date の終値から各ホライズン先の終値までのリターンを計算（単一クエリでまとめて取得）。horizons のバリデーションあり。
    - IC 計算（calc_ic）: ファクターと将来リターンの Spearman ランク相関を実装（ランク計算は ties を平均ランクで処理）。有効レコードが 3 件未満なら None を返す。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算（None を除外）。
    - rank ユーティリティ（同順位は平均ランク、丸めで ties 検出精度向上）。
    - 研究モジュールは標準ライブラリのみで実装（pandas 等に依存しない）という設計方針を採用。

  - research/__init__.py に主要ユーティリティを公開（calc_momentum 等、zscore_normalize を含む）。

- パッケージ構成
  - execution / strategy / monitoring 各パッケージ用のプレースホルダ __init__.py を配置し、将来の拡張に備えた構成。

### Security
- ニュース収集で SSRF 対策を実装（スキーム検証・プライベートアドレス拒否・リダイレクト時検査）。
- XML パースに defusedxml を使用して XML ベース攻撃を回避。
- .env 読み込みで OS 環境変数を保護する protected ロジックを導入。

### Performance / Reliability
- J-Quants クライアントに固定間隔レートリミッタを実装し API 制限を順守。
- ネットワーク障害や API ステータスに対するリトライ（指数バックオフ）で信頼性向上。429 の Retry-After を尊重。
- ページネーションやモジュール内トークンキャッシュで連続 API 呼び出しの効率化を図る。
- ニュース保存処理はチャンク分割・トランザクション・INSERT RETURNING により I/O オーバーヘッドを低減しつつ挿入件数を正確に把握。
- DuckDB 側は INSERT ... ON CONFLICT を多用し冪等性を担保。

### Notes / Design decisions
- リサーチ系は外部ライブラリへ依存せず標準ライブラリのみで実装されているため、数値処理の柔軟性（高速化や追加統計）は今後の拡張ポイント。
- news_collector._urlopen はテスト用にモック差替え可能な設計（ユニットテストを想定）。
- .env パーサは複雑なクォート・エスケープやインラインコメントを考慮した実装になっているため、.env の書式互換性に配慮。
- raw_executions テーブル定義が途中まで含まれている（スニペット終端に続きがある可能性）。実運用前にスキーマの完全性を確認すること。

### Breaking Changes
- 初期リリースのため該当なし。

---

今後のリリースでは、strategy / execution / monitoring の実装やテストカバレッジ、外部依存ライブラリ導入（必要に応じて）、およびパフォーマンス最適化の変更を加えていく想定です。必要があれば各モジュールの詳細な API ドキュメントや使用例も別途作成します。
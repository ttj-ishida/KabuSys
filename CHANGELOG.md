Keep a Changelog に準拠した変更履歴

すべての注目すべき変更をこのファイルに記載します。
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

# [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。
主な追加機能・実装方針は以下のとおりです。

Added
- パッケージ構成
  - kabusys パッケージの基本エントリを追加（src/kabusys/__init__.py）。バージョンを 0.1.0 に設定し、主要サブパッケージを __all__ に公開（data, strategy, execution, monitoring）。
  - 空のプレースホルダパッケージを作成（kabusys.execution, kabusys.strategy）。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルート検出は .git / pyproject.toml を基準）。
  - .env パーサ実装（コメント、export プレフィックス、クォート文字列、エスケープ、インラインコメントの扱いなどに対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須変数取得ヘルパ _require と Settings クラスを実装（J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベルの検証および便宜プロパティを含む）。
  - 環境値検証: KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL の許容値チェック。

- データレイヤ（src/kabusys/data/*）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制限順守のための固定間隔スロットリング実装（120 req/min を想定）。
    - リトライロジック（指数バックオフ、最大リトライ回数、408/429/5xx の再試行）、429 の Retry-After ヘッダ優先処理。
    - 401 受信時の自動 ID トークリフレッシュ（1回のみ）とモジュールレベルのトークンキャッシュ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB へ冪等保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による重複処理。
    - 安全な型変換ユーティリティ _to_float, _to_int を提供（不正値を None に変換する挙動を明示）。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード取得（fetch_rss）と記事前処理（URL 除去、空白正規化）を実装。
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先のスキーム/ホスト検査、プライベート IP 判定（IP・DNS 解決の両面で検査）を実装。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES, デフォルト 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - raw_news へのチャンク挿入と INSERT ... RETURNING を用いた実際に挿入された記事IDの取得（save_raw_news）。
    - news_symbols（記事と銘柄の紐付け）を一括挿入する内部ユーティリティ（_save_news_symbols_bulk）と外部向け関数（save_news_symbols）。
    - テキストから銘柄コード抽出ロジック（4桁数字、known_codes によるフィルタリング）を実装。
    - run_news_collection: 複数 RSS ソースからの収集フローを実装（各ソース独立してエラーハンドリング、銘柄紐付けまで含む）。

  - スキーマ定義（src/kabusys/data/schema.py）
    - DuckDB 用のテーブル定義を実装（Raw Layer の raw_prices, raw_financials, raw_news, raw_executions などの DDL を含む。※ファイルの一部に続きあり）。
    - DataLayer の 3 層（Raw / Processed / Feature / Execution）構成を想定したコメントと設計文書リンク代替的説明を追加。

- リサーチ/特徴量（src/kabusys/research/*）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL で一括取得）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンの順位相関を独自実装、欠損・finite チェック、十分なサンプル数の判定）。
    - ランク計算ユーティリティ rank（同順位は平均ランク、丸めによる ties 検出対策）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median を標準ライブラリのみで算出）。
    - 設計方針: DuckDB の prices_daily テーブルのみ参照、外部 API に依存しない実装。

  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（calc_momentum）: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）。データ不足に対する None 処理。
    - Volatility（calc_volatility）: atr_20（20日 ATR 平均）、atr_pct、avg_turnover、volume_ratio。true_range の NULL 伝播コントロール、必要行数チェック。
    - Value（calc_value）: raw_financials から最新財務を取得し per（price/EPS）と roe を計算。price/eps の安全チェック。
    - 全関数は DuckDB 接続を受け取り SQL を用いて効率的に計算する設計。

  - research パッケージ公開（src/kabusys/research/__init__.py）
    - 主要関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を __all__ として公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集に対する SSRF 対策（スキーム検証、プライベート IP 判定、リダイレクト検査）を実装。
- XML パースに defusedxml を使用して XML 関連の攻撃を軽減。
- HTTP レスポンスのサイズ上限を設け、gzip 解凍後もチェックすることで DoS（メモリ枯渇）を緩和。
- J-Quants クライアントでの認証トークン自動更新ロジックは無限再帰を避けるため allow_refresh フラグを導入。

Notes / Design
- Research モジュールは外部ライブラリに依存しない（pandas 等を使用しない）実装方針。
- DuckDB を中心にデータを保持・集計する設計。生データ保存は raw_* テーブルに行い、冪等性を重視した SQL を使用。
- J-Quants API 呼び出しについてはレート制御とリトライを組み合わせ、運用での安定性を高める設計。

Known limitations / TODO
- strategy および execution の具体的な取引ロジック・発注処理はプレースホルダのまま（次フェーズで実装予定）。
- 一部スキーマ（schema.py）の DDL 定義がファイル末尾で継続している箇所があるため、以降のテーブル定義やインデックス等は今後補完される想定。
- 外部テスト・ユニットテストはこのリリース内に含まれていない（別途追加予定）。

---

開発者向け補足
- 環境変数名の例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
- 自動 .env ロードはプロジェクトルートを起点に行われるため、配布後に CWD が変わっても期待通り動作します。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

（以上）
# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

注: このリポジトリは初期リリース（v0.1.0）としての状態を示しています。以下はコードベースから推測して作成した変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

初回リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0。トップレベルで data, strategy, execution, monitoring をエクスポート。
  - ファイル: src/kabusys/__init__.py

- 設定・環境変数管理
  - .env ファイルおよび環境変数から設定を自動ロードする機能を追加。
    - プロジェクトルートは .git または pyproject.toml を起点に探索するため、CWD に依存しない自動ロードを実現。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパースは `export KEY=val`、クォート、インラインコメント等に対応。
    - OS 環境変数を保護するための protected パラメータを用いた上書き制御を実装。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - デフォルト値: KABUSYS_API_BASE_URL、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）等。
    - KABUSYS_ENV と LOG_LEVEL の値チェック（許容値をバリデーション）と is_live / is_paper / is_dev 判定プロパティ。
  - ファイル: src/kabusys/config.py

- J-Quants API クライアント
  - RateLimiter による固定間隔スロットリング（デフォルト 120 req/min、最小間隔 0.5s）を実装。
  - 冪等性を考慮した DuckDB への保存関数を提供（INSERT ... ON CONFLICT DO UPDATE）。
  - 自動リトライ機構（指数バックオフ、最大 3 回）を実装。リトライ対象はネットワークエラーおよびステータス 408/429/5xx。
  - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライする仕組みを実装。
  - ページネーション対応の取得関数を提供:
    - fetch_daily_quotes: 日足データ取得（ページネーション対応）
    - fetch_financial_statements: 財務データ取得（ページネーション対応）
    - fetch_market_calendar: マーケットカレンダー取得
  - DuckDB 保存関数:
    - save_daily_quotes -> raw_prices テーブルへ保存（fetched_at を UTC ISO 形式で付与）
    - save_financial_statements -> raw_financials テーブルへ保存
    - save_market_calendar -> market_calendar テーブルへ保存
  - 入力変換ユーティリティ: _to_float, _to_int（安全な変換ロジック）
  - ファイル: src/kabusys/data/jquants_client.py

- ニュース収集モジュール（RSS）
  - RSS フィードを安全に取得・パースし、raw_news テーブルへ冪等保存する一連の機能を実装。
  - セキュリティ / 頑健性対策:
    - defusedxml による XML パースで XML BOM 等の攻撃に対処。
    - SSRF 対策: フェッチ前のホスト検証、リダイレクト時のスキーム/ホスト検証、プライベート IP へのアクセス拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - 記事IDは正規化URLの SHA-256（先頭32 文字）で生成して冪等性を担保。
  - RSS パース / 前処理:
    - URL 除去、空白正規化等のテキスト前処理機能を提供（preprocess_text）。
    - pubDate のパース関数（RFC2822 互換）。パース失敗時は警告ログを出し現在時刻で代替。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用いて新規挿入された記事IDのみを返す（チャンク化して 1 トランザクションで挿入）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付けをチャンク化して挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING 等で実際の挿入数を正確に取得）。
  - 銘柄コード抽出:
    - extract_stock_codes: テキスト中の 4 桁数字を抽出し、known_codes に基づいて有効コードのみ返す（重複除去）。
  - 統合ジョブ:
    - run_news_collection: 複数 RSS ソースを走らせ、raw_news 保存 → （既知銘柄が与えられれば）news_symbols へ紐付けを行う。各ソースごとに独立してエラーハンドリング。
  - デフォルト RSS ソース（yahoo_finance）を定義。
  - ファイル: src/kabusys/data/news_collector.py

- DuckDB スキーマ定義 & 初期化
  - DataSchema に基づくテーブル定義（Raw レイヤーの DDL を含む）。
    - raw_prices, raw_financials, raw_news, raw_executions（スニペットでは raw_executions の定義途中まで含む）
  - ファイル: src/kabusys/data/schema.py

- 研究（Research）モジュール
  - 特徴量探索 / 統計解析:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21] 営業日）での将来リターンを DuckDB の prices_daily テーブルから計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）時は None を返す。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ（丸めで ties 検出漏れを防止）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None を除外）。
    - 実装は外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
  - ファイル: src/kabusys/research/feature_exploration.py

  - ファクター計算モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を prices_daily から計算。データ不足時は None。
    - calc_volatility: 20 日 ATR（true range の平均）、相対 ATR（atr_pct）、20 日平均売買代金、当日出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し、PER（EPS が 0/欠損時は None）・ROE を計算。PBR/配当利回りは未実装。
    - それぞれ DuckDB 内でウィンドウ関数等を用いて効率的に取得・集計。
  - ファイル: src/kabusys/research/factor_research.py

  - research パッケージの再エクスポート:
    - calc_momentum, calc_volatility, calc_value, zscore_normalize（kabusys.data.stats から）および feature_exploration の関数を __all__ で公開。
    - ファイル: src/kabusys/research/__init__.py

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集での SSRF 対策、defusedxml による XML パース保護、レスポンスサイズ制限、リダイレクト時検証など多層の防御を追加。

### Notes / Known limitations
- 一部の機能は「未実装」注記あり（例: バリューファクターの PBR / 配当利回り）。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装だが、大量データ処理の最適化が今後必要になる可能性あり。
- raw_executions テーブル定義はスニペットで途中まで示されているため、完全な Execution Layer スキーマは引き続き定義される想定。
- settings の必須環境変数が未設定の場合は ValueError を送出するため、デプロイ時には .env の準備が必要。

---

（この CHANGELOG はコードベースの内容から推測して記載しています。実際のリリースノートとして用いる場合は、コミット履歴や実際のリリース日付・対象変更点を反映してください。）
# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリースとして v0.1.0 を記録します。

全般的な注意:
- バージョンはパッケージルートの `src/kabusys/__init__.py` に定義された __version__ に準拠しています。
- 本ログはソースコードから推測して作成しています。実装の細かい挙動や未提示ファイルとの相互作用については実際のリポジトリ内容に依存します。

[Unreleased]

## [0.1.0] - 2026-03-19
Initial release

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開インターフェースを追加（__all__ に data, strategy, execution, monitoring を設定）。
  - 空のサブパッケージ初期化ファイルを追加（`src/kabusys/execution/__init__.py`, `src/kabusys/strategy/__init__.py`）。

- 設定 / 環境変数管理 (`src/kabusys/config.py`)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行うため、CWD に依存しない。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - `.env` 行パーサは `export KEY=val` 形式、引用符（'"/）とエスケープ、インラインコメントの扱い等に対応。
    - 上書き時に OS 環境変数を保護するための protected オプションをサポート。
  - `Settings` クラスを提供し、主要設定値をプロパティとして公開（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）。
    - KABUSYS_ENV と LOG_LEVEL に対するバリデーション実装。
    - パス系設定（DuckDB/SQLite）は Path に変換して返却。

- Data: J-Quants クライアント (`src/kabusys/data/jquants_client.py`)
  - J-Quants API からデータ取得するクライアントを実装（株価日足、財務データ、マーケットカレンダー等）。
  - 特徴:
    - レート制限（120 req/min）を守る固定間隔の RateLimiter を実装。
    - リトライロジック（最大 3 回、指数バックオフ、HTTP 408/429/5xx を対象）を実装。
    - 401 Unauthorized を受けた場合はリフレッシュトークンで id_token を自動更新して 1 回リトライ。
    - ページネーション対応（pagination_key を使用してページをたどる）。
    - データ取得タイミングをトレースするために fetched_at を UTC 形式で記録。
  - DuckDB への保存ユーティリティを実装（冪等性: ON CONFLICT DO UPDATE を使用）。
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
  - 型変換ユーティリティ `_to_float`, `_to_int` を実装し、データの不正値や空文字を安全に扱う。

- Data: ニュース収集（RSS）モジュール (`src/kabusys/data/news_collector.py`)
  - RSS フィードからの記事収集・前処理・DuckDB への保存の一連処理を実装。
  - 特徴と安全対策:
    - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネスカテゴリ）。
    - レスポンスサイズ上限を設け（MAX_RESPONSE_BYTES = 10MB）てメモリ DoS を防止。
    - Gzip 圧縮レスポンスの検証（解凍後も上限チェック）。
    - defusedxml を使った XML パースで XML-Bomb 等に対応。
    - SSRF 防止:
      - URL スキームは http/https のみ許可。
      - リダイレクト時にスキームとプライベート IP/ループバック/リンクローカルを検査するハンドラを導入。
      - 初回 URL と最終 URL 両方でホストがプライベートかをチェック。
    - URL 正規化: トラッキングパラメータ（utm_* 等）除去、クエリソート、フラグメント除去を行う `_normalize_url`。
    - 記事 ID は正規化 URL の SHA-256 を用いて生成（先頭 32 文字）し、冪等性を担保。
    - テキスト前処理（URL 除去・空白正規化）。
    - DuckDB への保存はチャンク化してトランザクション単位で行い、INSERT ... RETURNING を使って実際に挿入された ID を取得する（save_raw_news）。
    - 記事と銘柄コードの紐付けを行う API（save_news_symbols, _save_news_symbols_bulk）を実装。
    - 銘柄コード抽出ユーティリティ（4桁数値パターン + known_codes フィルタ）を実装。
  - 高レベル統合ジョブ `run_news_collection` を提供し、各ソース毎の独立したエラーハンドリングと記事保存 → 銘柄紐付けまでを実行。

- Research（特徴量計算 / 探索）
  - feature_exploration (`src/kabusys/research/feature_exploration.py`)
    - 将来リターン計算 `calc_forward_returns(conn, target_date, horizons)` を実装（複数ホライズンを1クエリで取得）。
      - horizons の検証（正の整数、最大 252 日）。
      - 結果は各銘柄の fwd_<Nd> カラムを含む辞書リストとして返す。
    - IC（Information Coefficient）計算 `calc_ic(factor_records, forward_records, factor_col, return_col)` を実装（Spearman の ρ をランクで計算）。
      - None / 非有限値の除外、レコード数不足（<3）で None を返す。
    - ランク変換ユーティリティ `rank(values)`（同順位は平均ランク・丸めによる ties 検出改善）。
    - ファクター統計サマリー `factor_summary(records, columns)`（count, mean, std, min, max, median）。
    - 設計方針として DuckDB の prices_daily テーブルのみ参照し、外部 API へはアクセスしない点を明記。
    - 標準ライブラリのみでの実装を意図。

  - factor_research (`src/kabusys/research/factor_research.py`)
    - モメンタム/ボラティリティ/バリュー等の定量ファクター計算を実装:
      - calc_momentum(conn, target_date): mom_1m, mom_3m, mom_6m, ma200_dev（MA200 乖離）を計算。データ不足時は None。
      - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio などを計算。真のレンジ算出の NULL 伝播制御やカウント条件による None 処理を実装。
      - calc_value(conn, target_date): raw_financials テーブルから直近決算を取得して PER, ROE を計算（EPS が 0/NULL の場合は None）。
    - DuckDB のウィンドウ関数を効果的に利用して効率的に集計。
    - スキャン期間やウィンドウ長は定数化（例: MA200, ATR20, momentum の日数等）。

- Data スキーマ定義 (`src/kabusys/data/schema.py`)
  - DuckDB 用のスキーマ DDL を追加（Raw Layer を中心に定義）。
    - raw_prices, raw_financials, raw_news の CREATE TABLE 文を提供。
    - raw_executions の定義が途中まで含まれている（Execution レイヤーのスキーマが着手されていることを示唆）。

### Security
- ニュース収集モジュールで SSRF / XML インジェクション / Gzip Bomb / 大容量レスポンス等に対する多重防御を導入。
- J-Quants クライアントで認証トークンの自動リフレッシュとリトライ制御を実装し、失敗時の情報を抑制せずログで警告・例外化。

### Performance
- J-Quants クライアント: 固定間隔スロットリングで API レート制限に準拠しつつページネーションを効率的に処理。
- Research モジュール: DuckDB のウィンドウ関数を用いて必要データをできるだけ少ないクエリで取得。
- news_collector: DB 挿入はチャンク単位・一括プレースホルダで行いトランザクションをまとめてオーバーヘッド削減。

### Internal / Misc
- 各モジュールで詳細なログ出力（logger.debug/info/warning/exception）を追加し、処理状況やスキップ件数などを記録。
- 一部ユーティリティ関数はテストの差し替えを想定した設計（例: `_urlopen` をモック可能）。

### Known limitations / Notes
- research パッケージは標準ライブラリを前提に実装する旨が書かれているが、実際に DuckDB を利用するため duckdb への依存がある。
- schema.py の raw_executions 定義が途中で終わっている（提供されているスニペットが途中までのため、Execution レイヤーの完全なスキーマは別ファイルや後続コミットで完成している可能性があります）。
- `src/kabusys/research/__init__.py` は `kabusys.data.stats.zscore_normalize` を参照しているが、該当の実装は今回提示されたスニペットに含まれていません（別モジュールで提供されていることが想定されます）。

If you want, 次のリリース向けの CHANGELOG テンプレート（Unreleased セクションの詳細）や、各関数の API 使用例・ドキュメント断片も作成できます。どの形式がよいか教えてください。
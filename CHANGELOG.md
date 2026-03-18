Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

なお内容は提示されたコードベースから推測して記載しています。必要に応じて日付や詳細を調整してください。

----
# CHANGELOG

すべての変更は「Keep a Changelog」方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装。

### Added
- パッケージ構成
  - 基本パッケージ `kabusys` を追加。公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート（`src/kabusys/__init__.py`）。
- 環境設定管理
  - `.env` ファイルおよび環境変数から設定を読み込む `kabusys.config.Settings` を追加。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う（`_find_project_root`）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動読み込みの無効化対応。
    - `.env` と `.env.local` の優先順・上書き・保護（OS 環境変数保護）に対応する読み込みロジック（`_load_env_file`, `_parse_env_line`）。
    - 必須設定取得用 `_require` を提供（未設定時は ValueError）。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供（例: `jquants_refresh_token`, `kabu_api_password`, `duckdb_path` 等）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の妥当性チェック（許容値検証）。
- データ取得・保存（J-Quants）
  - `kabusys.data.jquants_client` を実装。
    - J-Quants API 呼び出しユーティリティ（`_request`）。
    - 固定間隔レートリミッタ（120 req/min）`_RateLimiter` を導入し API レート制限を厳守。
    - 再試行（指数バックオフ）、HTTP ステータスに応じたリトライ判定、429 の `Retry-After` 優先処理を実装。
    - 401 受信時はトークン自動リフレッシュの仕組みを実装（ID トークンキャッシュ `_ID_TOKEN_CACHE`, `get_id_token`）。
    - ページネーション対応（`fetch_daily_quotes`, `fetch_financial_statements` 等）。
    - DuckDB への冪等保存（INSERT ... ON CONFLICT DO UPDATE）関数を追加（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）。
    - 型変換ユーティリティ `_to_float`, `_to_int` を追加（不正値は None）。
    - fetched_at を UTC で記録して look-ahead bias を防止。
- ニュース収集
  - `kabusys.data.news_collector` を実装。
    - RSS フィードの取得（gzip 対応）とパース（defusedxml を使用して XML 攻撃対策）。
    - URL 正規化（トラッキングパラメータ除去）および記事 ID の生成（正規化 URL の SHA-256 先頭32文字）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストのプライベートアドレス判定（`_is_private_host`）、リダイレクト前検査用ハンドラ（`_SSRFBlockRedirectHandler`）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェック、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - テキスト前処理（URL 除去・空白正規化）`preprocess_text`。
    - 銘柄コード抽出（4桁数字、既知コード集合でフィルタ）`extract_stock_codes`。
    - DuckDB への保存:
      - `save_raw_news`：チャンク分割、トランザクション、INSERT ... ON CONFLICT DO NOTHING、INSERT RETURNING で実際に挿入された ID を返す。
      - `save_news_symbols` / `_save_news_symbols_bulk`：記事-銘柄の紐付けをチャンクで一括保存し、正確な挿入数を返す。
    - 統合処理 `run_news_collection`：複数ソースを個別に処理し、エラー局所化（1 ソース失敗でも継続）を実現。
- リサーチ / 特徴量探索
  - `kabusys.research.feature_exploration` を実装。
    - 将来リターン計算 `calc_forward_returns`（horizons 指定、SQL で LEAD を使って一括取得）。
    - IC（Spearman の ρ）計算 `calc_ic`（結合、None フィルタリング、ランク付け→スピアマン算出）。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク、丸めによる ties 対策）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median）。
    - ログ出力を含むデバッグフレンドリーな実装。
  - `kabusys.research.factor_research` を実装。
    - Momentum（mom_1m/mom_3m/mom_6m、200日移動平均乖離 ma200_dev）`calc_momentum`。
    - Volatility / Liquidity（20日 ATR、ATR 比率、20日平均売買代金、出来高比）`calc_volatility`。
    - Value（PER、ROE。raw_financials から最新財務データを取得）`calc_value`。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番 API へアクセスしない設計。
  - `kabusys.research.__init__` で主要関数と zscore_normalize をエクスポート。
- スキーマ定義（DuckDB）
  - `kabusys.data.schema` を追加し、Raw レイヤーの DDL を定義（`raw_prices`, `raw_financials`, `raw_news`, `raw_executions` 等のテーブル定義を含む）。
  - テーブル作成用DDLを用意し、データレイヤの基盤を整備。
- その他
  - strategy / execution パッケージの雛形を追加（`__init__.py` が存在） — 戦略・発注ロジックは分離済み。
  - ロギングを各モジュールで利用（debug/info/warning/error の適切な出力）。

### Changed
- （初回リリースのため履歴変更なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- RSS パーサーに defusedxml を使用して XML 関連の攻撃を軽減。
- RSS フェッチで SSRF を防ぐ多数の対策:
  - スキーム検証、プライベート IP 検査、リダイレクト時の再検証。
- J-Quants クライアントでトークン自動リフレッシュ時の無限再帰防止（allow_refresh フラグ）。
- 外部入力（.env）読み込み時に注意喚起（エラーハンドリング、読み込み失敗時の警告出力）。

### Notes / Limitations
- DuckDB 接続を前提とする機能が多いため、実行には適切な DB 初期化（テーブル作成）と接続が必要。
- research モジュールは標準ライブラリ（pandas 等には依存しない）で実装されており、大規模データ処理時は柔軟な最適化が必要となる可能性あり。
- `monitoring` パッケージ名は __all__ に含まれるが、該当する実装がこのバージョンに含まれていない可能性がある（今後追加予定）。
- NewsCollector の URL 正規化や記事 ID 生成はトラッキングパラメータを除去することを前提としているため、外部リンクの扱いに注意。

----

必要であれば、この CHANGELOG をリポジトリに合わせて日付・バージョンを調整し、リリースノートや GitHub リリース説明に転用できる形で整形します。どの程度の粒度（関数単位まで列挙する等）にするか指定があれば追記します。
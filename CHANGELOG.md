# Changelog

すべての主要な変更は Keep a Changelog の形式に従って記載しています。  

※ この CHANGELOG は与えられたコードベースから推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-18
初回公開（推定）。日本株自動売買システム「KabuSys」の基礎機能を実装したリリース。

### Added
- パッケージ初期化
  - パッケージルート (src/kabusys/__init__.py) にてバージョン設定（0.1.0）および主要モジュールを公開（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み（プロジェクトルート判定は .git または pyproject.toml を探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env 行パーサ（クォート対応、export KEY= 形式、インラインコメント処理等）を実装。
    - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / システム環境（env, log_level）等のプロパティを提供。env と log_level の妥当性検査（許容値チェック）を実装。
- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（トークン取得・ページネーション対応）。
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象、429 の Retry-After 優先）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）と再試行。モジュールレベルのトークンキャッシュ実装。
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar のデータ取得関数（ページネーション対応）。
    - DuckDB への冪等保存関数：save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - ユーティリティ関数 _to_float / _to_int（堅牢な変換ロジック）。
    - fetched_at に UTC タイムスタンプを付与（look-ahead bias 防止のため取得時刻を記録）。
- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィード収集機能（fetch_rss）と前処理・DB 保存機能（save_raw_news, save_news_symbols, _save_news_symbols_bulk, run_news_collection）。
    - セキュリティ対策：
      - defusedxml による XML パース（XML Bomb 防御）。
      - SSRF 防止：URL スキーム検証（http/https のみ）、リダイレクト時のホスト検査、プライベートアドレス拒否、カスタムリダイレクトハンドラ実装。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES、Gzip 検査）によるメモリ DoS 対策。
      - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。トラッキングパラメータ除去・クエリソートによる正規化を実施。
    - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁パターン、既知コードフィルタ）。
    - DB 挿入はチャンク化してトランザクション内で実行、INSERT .. RETURNING を利用して実際に挿入された件数を取得。
- DuckDB スキーマ（初期定義）
  - src/kabusys/data/schema.py
    - Raw レイヤーの DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む）。
    - スキーマ定義は DataSchema.md に基づく三層構造（Raw / Processed / Feature / Execution）を想定。
- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（calc_momentum）：1M/3M/6M リターン、200日移動平均乖離率を計算。
    - ボラティリティ/流動性（calc_volatility）：20日ATR、ATR割合、平均売買代金、出来高比率を計算。
    - バリュー（calc_value）：raw_financials から最新財務を取得して PER / ROE を計算。
    - 実装方針として DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番 API にはアクセスしない設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）：指定日から各ホライズン先のリターンを算出（1,5,21 日をデフォルト）。
    - IC 計算（calc_ic）：Spearman（ランク相関）によりファクターの有効性を評価。ties の取り扱い、最小レコード数チェックを実装。
    - 基本統計サマリー（factor_summary）：count/mean/std/min/max/median を計算。
    - rank ユーティリティ：同順位は平均ランク、浮動小数の丸め（round(v,12)）で ties 検出の安定化。
  - src/kabusys/research/__init__.py にて主要関数を再公開（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。
- その他ユーティリティ
  - DuckDB を利用する設計（duckdb パッケージ依存）。research は標準ライブラリと duckdb のみで動作することを意図。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector の実装にて SSRF 対策、defusedxml の採用、レスポンスサイズ制限、URL スキーム検証等複数の防御を導入。
- jquants_client の HTTP エラーハンドリングとリトライロジックにより、外部 API 呼び出し時の堅牢性を向上。

### Notes / Known limitations（推測）
- strategy と execution パッケージの __init__.py は空ファイルになっており、発注ロジックや戦略実装はまだ含まれていない（今後実装予定）。
- schema.py は raw レイヤー定義が中心で、Processed / Feature / Execution 層の完全な DDL はこのスナップショットでは未完了の可能性がある（raw_executions の定義が途中で切れている）。
- research モジュールは外部ライブラリ（pandas, numpy）に依存しない純粋 Python 実装のため、大規模データでのパフォーマンス面は今後の改善対象。
- J-Quants クライアントでは HTTP リクエストに urllib を使用しており、必要に応じてより高機能な HTTP クライアントの検討（例: requests / httpx）を検討可能。

### Breaking Changes
- なし（初回リリース）

---

以上。必要であれば各モジュールごとのより詳細な変更点や使用例、注意点（環境変数一覧、DB スキーマ全体、期待するテーブル構成など）を追加で作成します。どのレベルの詳細を希望しますか？
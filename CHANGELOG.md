Keep a Changelog
----------------

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]

[0.1.0] - 2026-03-19
-------------------

Added
- 初回リリース (バージョン 0.1.0)
- パッケージ基盤
  - パッケージ情報: src/kabusys/__init__.py にて __version__="0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - .env.local は .env より優先して上書き（ただし OS 環境変数は保護）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の設定取得用プロパティを実装。KABUSYS_ENV / LOG_LEVEL の検証・ヘルパープロパティ（is_live 等）を提供。
- Data レイヤー (src/kabusys/data/*)
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - API レート制限を守る固定間隔レートリミッタ実装（120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After ヘッダ考慮、ネットワークエラー再試行。
    - 401 受信時の ID トークン自動リフレッシュ処理（再帰防止のための制御）。
    - ページネーション対応のデータ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存用ユーティリティ: save_daily_quotes, save_financial_statements, save_market_calendar（冪等化のため ON CONFLICT DO UPDATE を使用）。
    - 文字列→数値変換ユーティリティ (_to_float / _to_int)。
  - ニュース収集 (src/kabusys/data/news_collector.py)
    - RSS フィード取得と記事整形、記事ID の冪等性確保（URL 正規化 → SHA-256 の前方 32 文字）。
    - トラッキングパラメータ除去、URL 正規化、テキスト前処理（URL 除去・空白正規化）。
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - レスポンスサイズ制限（デフォルト上限 10MB）・gzip 解凍後のサイズ検証。
    - SSRF 対策: URL スキーム検証 (http/https のみ)、プライベート/ループバックアドレス検出、リダイレクト時の検査用ハンドラ実装。
    - DB 保存はチャンク化してトランザクション内で行い、INSERT ... RETURNING により実際に挿入されたレコード一覧/件数を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
    - 銘柄コード抽出ユーティリティ（4 桁数字、既知銘柄セットフィルタ）。
  - DuckDB スキーマ (src/kabusys/data/schema.py)
    - Raw レイヤ向け DDL 定義（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）。DataSchema.md に準拠した初期化用スクリプト群を用意。
- Research レイヤ (src/kabusys/research/*)
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: DuckDB を用いた将来リターン計算（複数ホライズン／LEAD を用いた単一クエリ取得）。
    - calc_ic: スピアマンランク相関（Information Coefficient）の計算。欠損値・有限性チェック、最小レコード数チェックを実装。
    - rank: 同順位は平均ランク処理（小数丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）計算。
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を DuckDB SQL ウィンドウ関数で算出。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を算出（true_range の NULL 伝播に注意）。
    - calc_value: raw_financials から最新財務データを取得して PER・ROE を計算（prices_daily と結合）。
  - research パッケージ初期化で主要関数と kabusys.data.stats.zscore_normalize を公開。
- ドキュメント準拠
  - 各モジュールに設計方針・注意点・Args/Returns を含む docstring を追加。

Changed
- なし（初回リリースのため）

Fixed
- .env パーサー: クォート内エスケープ、コメント認識、export プレフィックス対応により実運用での .env 取りこぼしを防止。
- jquants_client の HTTP リトライ挙動: 429 の Retry-After を尊重、10xx 系以外の HTTPError に対する再試行制御を明確化。
- news_collector:
  - 大きすぎるレスポンスや gzip 解凍失敗時に安全にスキップするハンドリングを追加。
  - RSS 内の非 URL な guid / link を適切にスキップするロジックを改善。

Security
- RSS パーサで defusedxml を使用して XML 関連攻撃を低減。
- ニュース取得での SSRF 対策を実装:
  - URL スキーム検証（http/https のみ許可）。
  - プライベート IP / ループバック / リンクローカル / マルチキャストアドレスへのアクセス禁止（直接 IP と DNS 解決両方で確認）。
  - リダイレクト先の検査ハンドラを導入してリダイレクト経由の内部アクセスを防止。
- レスポンスサイズ制限および gzip 解凍後の上限チェックによりメモリ DoS を軽減。
- J-Quants クライアントは認証トークンを漏らさないキャッシュ制御と 401 リフレッシュの限定実行で安全性を考慮。

Internal
- モジュールレベルでの ID トークンキャッシュと固定間隔レートリミッタを導入し、ページネーションや連続 API 呼び出しで効率を向上。
- DuckDB への保存は冪等性を考慮した SQL（ON CONFLICT）とトランザクション分割で堅牢化。
- research モジュールは外部依存を極力避け、標準ライブラリ＋DuckDB SQL で実装（再現性重視）。

Known limitations / Notes
- strategy/ execution / monitoring パッケージは初期スケルトン（__init__.py のみ）を用意しており、戦略実行ロジックや発注実装は今後拡張予定。
- research モジュールは DuckDB 内のテーブル（prices_daily, raw_financials 等）に依存するため、事前にデータ整備が必要。
- 一部 SQL やスキーマは拡張・微調整を想定（例: Feature Layer / Execution Layer の詳細スキーマは未完）。
- 外部 API 呼び出しにはネットワークの可用性・API 利用制限が影響するため、運用環境での監視・ロギング設定を推奨。

--- 

注: この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はテスト結果・マイグレーション手順・互換性情報を追記してください。
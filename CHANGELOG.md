Keep a Changelog
=================

すべての公開リリースはセマンティックバージョニングに従います。  
この CHANGELOG は "Keep a Changelog" 構成に準拠します。

[0.1.0] - 2026-03-18
--------------------

Added
- 初回公開リリース。kabusys パッケージの基盤機能を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py: パッケージ名・バージョン定義（__version__ = "0.1.0"）および主要サブパッケージの公開（data, strategy, execution, monitoring）。
  - 設定・環境変数管理
    - src/kabusys/config.py:
      - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（テスト用フック）。
      - .env パーサ実装（export プレフィックス対応、クォートやエスケープ、インラインコメント扱い等の細かい仕様）。
      - 環境変数必須チェック用 _require と Settings クラス（J-Quants/Kabu/Slack/DB/ログレベル/実行環境判定プロパティを提供）。
      - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
  - データ取得・保存（J-Quants）
    - src/kabusys/data/jquants_client.py:
      - J-Quants API クライアントの実装（ページネーション対応）。
      - レート制限のための固定間隔スロットリング RateLimiter（120 req/min に基づく）。
      - 再試行（指数バックオフ、最大3回）。408/429/5xx に対するリトライ、429 は Retry-After を尊重。
      - 401 受信時の自動トークンリフレッシュ（1回リトライ）とモジュールレベルの ID トークンキャッシュ。
      - fetch_* 系 API: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
      - DuckDB への保存関数（冪等性を意識した INSERT ... ON CONFLICT DO UPDATE）: save_daily_quotes, save_financial_statements, save_market_calendar。
      - 入力変換ユーティリティ _to_float / _to_int（堅牢な型変換ルール）。
  - ニュース収集パイプライン（RSS）
    - src/kabusys/data/news_collector.py:
      - RSS 取得・前処理・DB 保存ワークフローの実装（fetch_rss, preprocess_text, save_raw_news, save_news_symbols, run_news_collection）。
      - セキュリティおよび堅牢性:
        - defusedxml による XML パース（XML Bomb 等対策）。
        - SSRF 対策: URL スキーム検証、ホストがプライベート/ループバックでないかの検査、リダイレクト時の検査を行う独自リダイレクトハンドラ。
        - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査。
        - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
      - DB 保存はチャンク化（_INSERT_CHUNK_SIZE）およびトランザクションでまとめ、INSERT ... RETURNING を用いて実際に挿入されたレコードのみを返す実装。
      - 銘柄コード抽出（4桁数字パターン + known_codes フィルタ）および一括紐付け保存機能。
      - テスト用フック: HTTP オープン処理を置き換え可能（_urlopen をモック可能）。
  - データスキーマ
    - src/kabusys/data/schema.py:
      - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層のうち Raw 層の DDL を含む）。
      - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（PRIMARY KEY / CHECK 制約を含むDDL）。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py:
      - ファクター群の計算（DuckDB 経由で prices_daily / raw_financials を参照）。
      - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（ウィンドウの行数不足時は None を返す設計）。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true range の NULL 伝播を考慮）。
      - calc_value: raw_financials から最新財務データを結合して PER・ROE を算出。
      - 各処理は本番 API に接続しない設計（DuckDB 内データのみ参照）。
    - src/kabusys/research/feature_exploration.py:
      - calc_forward_returns: 指定日から各ホライズン（デフォルト 1/5/21 営業日）先までの将来リターンを一度に取得。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（結合・欠損・同順位処理に対応）。
      - rank / factor_summary: ランク計算（同順位は平均ランク、丸めによる ties 対応）および基本統計量集計（count/mean/std/min/max/median）。
    - src/kabusys/research/__init__.py:
      - 主要な計算関数を再エクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。
  - その他
    - すべての主要関数にログ出力（logger）を追加し、処理状況・警告を記録。

Security
- ニュース収集での SSRF 対策、XML パースに defusedxml を使用、受信サイズの上限を設定する等、外部入力に対する複数の防御層を実装。
- J-Quants クライアントは認証トークン管理・自動リフレッシュを備え、API レート制限と再試行ロジックを組み合わせて堅牢化。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Notes / Design decisions
- Research 用関数群は "DuckDB 内の履歴データのみを参照する" 方針を徹底しており、発注 API 等の外部副作用を持たない。
- DB への保存は冪等性（ON CONFLICT）を重視し、重複挿入や再収集に耐性を持たせている。
- .env の自動ロードはプロジェクトルートを基準に行うため、CWD に依存しない挙動を確保している。
- 外部依存の最小化を目指しており、リサーチコードは標準ライブラリのみで実装（pandas 等未依存）。

Acknowledgements
- 仕様や設計はソースコード内の docstring（DataPlatform.md / StrategyModel.md 参照箇所）に準拠しています。

（今後のリリースでは bugfix/changed/deprecated 等のカテゴリで差分を記載します）
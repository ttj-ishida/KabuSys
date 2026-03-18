CHANGELOG
=========

すべての変更は Keep a Changelog の仕様に準拠して記載しています。
このファイルは後方互換やリリースノート作成のための要約を目的とします。

未リリース
---------
（現在なし）

0.1.0 - 2026-03-18
-----------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に追加。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は __file__ を起点に .git / pyproject.toml を探索（CWD に依存しない実装）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
    - OS 環境変数を保護する protected セットを使った上書き制御。
  - .env 行パーサは export 句、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、必須設定取得用の _require とプロパティを公開。
    - J-Quants / kabuステーション / Slack / DB パス等の主要設定プロパティを実装。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装。
    - is_live/is_paper/is_dev の利便性プロパティを提供。

- Data モジュール（src/kabusys/data/*）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API レート制御（120 req/min）用の固定間隔スロットリング _RateLimiter を実装。
    - 再試行（指数バックオフ）ロジックを実装（最大リトライ回数、特定ステータスでリトライ、Retry-After を尊重）。
    - 401 受信時のトークン自動リフレッシュ処理を実装（キャッシュ共有と強制更新の仕組み）。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements。
    - 市場カレンダー取得用 fetch_market_calendar。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。
      - fetched_at を UTC タイムスタンプで記録し、取得時刻のトレースを可能に（Look-ahead bias 対策）。
      - INSERT ... ON CONFLICT DO UPDATE による冪等性を担保。
    - 入力データの安全変換ユーティリティ (_to_float, _to_int) を提供。
  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィード収集・前処理・DB 保存の統合実装。
    - セキュリティ対策:
      - defusedxml を利用した XML パースで XML Bomb 等の攻撃を緩和。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベートアドレス判定、リダイレクト先検査用ハンドラを実装。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査を行う（Gzip bomb 対策）。
      - トラッキングパラメータ除去（utm_* など）と URL 正規化。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - テキスト前処理（URL 除去・空白正規化）と RSS pubDate の堅牢なパース。
    - raw_news へのチャンク INSERT（INSERT ... RETURNING id）で実際に挿入された ID を返す実装。
    - news_symbols テーブルへの銘柄紐付けを一括保存する内部ユーティリティを提供。
    - 銘柄コード抽出ロジック（4桁数字パターン＋ known_codes フィルタ）を実装。
    - デフォルトソースとして Yahoo Finance のカテゴリ RSS を定義。

- Research モジュール（src/kabusys/research/*）
  - 提供 API を __init__ でエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定基準日から各ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを DuckDB の prices_daily から一度に取得して計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算の実装（欠損・ties 対応、最小サンプル数チェック）。
    - rank: タイ（同値）を平均ランクで扱うランク関数（丸めで浮動小数誤差を低減）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能。
    - 設計方針として DuckDB の prices_daily テーブルのみ参照し、外部 API を呼ばないことを明記。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum:
      - mom_1m, mom_3m, mom_6m（営業日ベースの LAG によるリターン）、200日移動平均乖離率(ma200_dev) を計算。
      - データ不足銘柄では None を返す。
    - calc_volatility:
      - 20日 ATR（true range の平均）と相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
      - true_range の NULL 伝播を注意深く扱い、カウントが足りない場合は None を返す。
    - calc_value:
      - raw_financials から target_date 以前の最新財務を取得して PER（EPS が有効な場合）・ROE を計算。
      - DuckDB 内で最新の財務レコードを ROW_NUMBER で抽出するクエリを利用。
    - ファクター計算群は DuckDB 接続を受け取り prices_daily/raw_financials のみ参照（外部 API へアクセスしないことを保証）。

- スキーマ定義（src/kabusys/data/schema.py）
  - DuckDB 向けの DDL 定義（Raw Layer の raw_prices, raw_financials, raw_news, raw_executions 等）を追加。
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）構造の設計に準拠。

Security
- defusedxml を用いた RSS の安全なパースを採用。
- RSS フェッチで SSRF 対策を導入（スキームチェック、ホスト/IP のプライベート判定、リダイレクト検査）。
- HTTP レスポンスサイズと gzip 解凍後サイズの上限チェックを導入し DoS 対策を強化。
- J-Quants クライアントのトークンリフレッシュとリトライで不安定な外部 API 呼び出しに対する耐性を向上。

Performance / Reliability
- API レート制限を守る固定間隔スロットリング実装。
- DuckDB へのバルク挿入をチャンク化してトランザクション内にまとめ、オーバーヘッドを低減。
- 重複排除（ON CONFLICT）により再実行時の冪等性を確保。
- fetch_* 関数はページネーション対応で全件取得をサポート。

Notes / Design Decisions
- Research/Factor モジュールはいずれも本番発注 API には一切アクセスしない設計（安全性と再現性の確保）。
- 日付・時刻は取得時に UTC で記録し、Look-ahead bias のトレースを可能にする。
- .env パーサは現実的な .env の書き方（export, quoted values, inline comments）に対応するようかなり互換性を持たせて実装。

Known limitations / TODO
- strategy/ execution/ monitoring パッケージの実装は骨組みのみ（__init__.py が存在）で、戦略ロジックや発注実行、監視周りの実装は今後の課題。
- PBR・配当利回りなど一部のバリューファクターは未実装（calc_value に注記あり）。
- DuckDB スキーマの Processed / Feature 層や Execution 層の完全な DDL は今後拡張予定。

その他
- ロギングは各モジュールで logger = logging.getLogger(__name__) を使用。デバッグ情報・警告を適切に出力するように設計。

ライセンスや貢献方法等はリポジトリの README を参照してください。
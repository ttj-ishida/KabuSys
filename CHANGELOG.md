CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
例: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-20
-------------------

Added
- 全体
  - 初回公開リリース。パッケージバージョンは kabusys.__version__ = "0.1.0"。
  - DuckDB を中心としたデータパイプライン、研究（research）・戦略（strategy）・データ取得（data）モジュールを実装。
  - ロギングを各モジュールに組み込み、操作中の警告・情報を出力。

- 環境設定（kabusys.config）
  - .env ファイル自動ロード機能を実装（優先順: OS 環境変数 > .env.local > .env）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .env パーサは以下をサポート:
    - 空行/コメント（#）を無視
    - export KEY=val 形式を許容
    - シングル／ダブルクォート内のエスケープ処理対応
    - クォートなし値内のインラインコメント判定（直前が空白/タブのみ）
  - Settings オブジェクトを提供し、必須環境変数の取得（_require による ValueError）や既定値を管理:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等はデフォルトを提供
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装
    - helper プロパティ is_live / is_paper / is_dev を提供

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - rate limiter（120 req/min 固定間隔スロットリング）
    - リトライ（指数バックオフ、最大3回。HTTP 408/429/5xx を対象）
    - 401 受信時にリフレッシュトークンで id_token を自動更新して1回リトライ
    - ページネーション対応（pagination_key）
    - レスポンス JSON のパースとエラー処理
  - データ取得 API:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（冪等保存）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
    - 各保存で fetched_at を UTC ISO8601 で記録
  - ユーティリティ: _to_float / _to_int（入力値の安全な変換）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集パイプラインを実装（デフォルトソースに Yahoo Finance を含む）。
  - セキュリティ対策:
    - defusedxml を利用して XML 攻撃を防止
    - URL 正規化でトラッキングパラメータ除去（utm_* 等）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定してメモリ DoS を緩和
    - 記事 ID は URL 正規化後の SHA-256（先頭32文字）を用いて冪等性を保証
    - HTTP/HTTPS 以外のスキームについての扱い（SSRF 保護）を考慮
  - DB へのバルク保存でチャンク処理やトランザクション最適化を想定

- 研究（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB のウィンドウ関数で計算
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 伝播を明示的に扱う）
    - calc_value: raw_financials と当日株価を組み合わせて per / roe を算出（最新レポートを銘柄ごとに取得）
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得
    - calc_ic: ファクターと将来リターン間の Spearman（ランク）相関を計算（有効サンプル <3 の場合は None）
    - rank: 同順位は平均ランクを割り当てる実装（浮動小数の丸め対策あり）
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算
  - いずれも外部ライブラリ（pandas 等）に依存しない設計

- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールで算出した生ファクターを統合
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）適用
    - 正規化（zscore_normalize を利用）対象カラムを指定し ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE+INSERT をトランザクション内で実施して冪等性・原子性を確保）
  - signal_generator.generate_signals:
    - features と ai_scores を統合して momentum/value/volatility/liquidity/news のコンポーネントスコアを計算
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）をサポート。ユーザ指定 weights は検証・正規化（合計が 1.0 になるよう再スケール）
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= _BEAR_MIN_SAMPLES）では BUY シグナルを抑制
    - BUY は threshold（デフォルト 0.60）超過銘柄を採用、SELL はポジションに対してストップロス（-8%）とスコア低下で判定
    - SELL を優先して BUY から除外、signals テーブルへ日付単位で置換（トランザクション）
    - 生成結果のログ出力（info/debug/warning）

- パッケージ構成
  - kabusys パッケージの __all__ に data, strategy, execution, monitoring を定義（execution ディレクトリは空の __init__ を含む。将来の拡張を想定）

Fixed
- （初版のため該当なし）

Changed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- XML パースに defusedxml を利用（news_collector）
- RSS/URL の正規化とトラッキングパラメータ削除、受信サイズ制限、SSRF を考慮した設計

Notes / 既知の制限・未実装項目
- signal_generator._generate_sell_signals のコメントに記載されている以下は未実装:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の実装は RSS 取得〜正規化までの設計を含むが、実行時の細部（HTTP ヘッダ /リダイレクト制御 など）は運用で調整が必要
- research モジュールは外部ライブラリ非依存で実装されているが、大規模データセットや高度な統計処理では追加最適化が望ましい
- J-Quants クライアントはネットワーク/API の挙動に依存するため、実運用では適切な監視・再試行ポリシーの上積みを推奨
- .env のパースは多くのケースに対応するが、極端に複雑な quoting/エスケープの取り扱いは注意が必要

作者・貢献
- 初期実装（データ取得・保存、研究、特徴量エンジニアリング、シグナル生成、環境設定）を含む v0.1.0 リリース

--- 

（この CHANGELOG は提供されたコードベースからの実装内容・設計コメントをもとに作成しています。実際のリリースノートとして使う場合は、追加の運用情報・変更履歴を適宜追記してください。）
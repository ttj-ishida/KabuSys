CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
リリース日付は 2026-03-20。

[0.1.0] - 2026-03-20
--------------------

Added
- 初回公開リリース。
- パッケージの概要:
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート済みモジュール: data, strategy, execution, monitoring
  - 主要設計方針: ルックアヘッドバイアスの排除、冪等性、DuckDB を用いたローカルデータ基盤

- 環境設定/ロード機能 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してルートを特定（CWD に依存しない）。
  - .env パース機能の実装:
    - コメント行 / 空行の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォート無し値におけるインラインコメント認識（直前が空白/タブの場合のみ）
  - .env 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は上書き許可）
  - OS 環境変数を保護する protected セットの仕組み、読み込み失敗時の警告出力。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを公開（settings インスタンス）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須取得
    - デフォルト値付き設定: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV
    - env / log_level の検証ロジック（有効値チェック）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - REST API 呼び出しユーティリティ _request 実装:
    - 固定間隔スロットリングによるレート制限 (120 req/min)
    - リトライ (最大 3 回)、指数バックオフ、429 の Retry-After 読み取り
    - 401 受信時の自動トークンリフレッシュ（1 回のみ再試行）とトークンキャッシュ
    - JSON デコードエラーハンドリング
  - get_id_token(): リフレッシュトークンから ID トークンを取得
  - ページネーション対応のデータ取得:
    - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - DuckDB へ冪等に保存する関数:
    - save_daily_quotes(): raw_prices テーブルへ ON CONFLICT DO UPDATE
    - save_financial_statements(): raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar(): market_calendar テーブルへ ON CONFLICT DO UPDATE
  - 保存時の fetched_at は UTC ISO8601 で記録（Look-ahead バイアス防止）
  - 型変換ユーティリティ: _to_float, _to_int（堅牢な変換／欠損処理）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集と raw_news への冪等保存機能（ON CONFLICT DO NOTHING）
  - デフォルト RSS ソースに Yahoo Finance を含む
  - セキュリティ・堅牢性考慮:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）
    - HTTP/HTTPS スキームのみを許可（SSRF 緩和）
    - 受信最大バイト数制限（10 MB）
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid, gclid 等）
    - 記事 ID は正規化後の URL の SHA-256（先頭 32 文字）で生成して冪等性を確保
    - テキスト前処理（URL 除去・空白正規化）
    - バルク挿入のチャンク化（デフォルトチャンクサイズ = 1000）
    - DB 操作を 1 トランザクションにまとめる方針

- 研究 / ファクター計算モジュール (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum(): mom_1m/mom_3m/mom_6m、ma200_dev を計算（200 日窓の存在をチェック）
    - calc_volatility(): 20 日 ATR、atr_pct、avg_turnover、volume_ratio を計算（true_range の欠損制御）
    - calc_value(): raw_financials と当日株価から per / roe を計算（最新財務レコードの取得）
    - 各関数は prices_daily / raw_financials のみを参照し、辞書リストを返す設計
  - feature_exploration.py:
    - calc_forward_returns(): 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得
    - calc_ic(): Spearman（ランク相関）による IC 計算（同順位は平均ランク）
    - rank(): 同順位は平均ランクで処理するランク関数（浮動小数丸めで ties 検出）
    - factor_summary(): count/mean/std/min/max/median を算出する統計サマリー
  - research パッケージ __all__ に主要 API を公開（calc_momentum 等、zscore_normalize の再公開）

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date):
    - research モジュールから生ファクターを取得（calc_momentum, calc_volatility, calc_value）
    - ユニバースフィルタ（最小株価 300 円、20日平均売買代金 >= 5 億円）を適用
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）
    - Z スコアを ±3 でクリップして外れ値影響を抑制
    - features テーブルへ日付単位で DELETE → INSERT の形で置換（トランザクションで原子性保証）
    - 処理は冪等（同じ target_date を何度実行しても安定）

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄の最終スコア final_score を計算
    - コンポーネントスコア: momentum/value/volatility/liquidity/news を計算するユーティリティを実装
    - AI news スコアは存在しない場合に中立（0.5）で補完
    - 欠損コンポーネントは中立値 0.5 で補完（欠損銘柄の不当な降格回避）
    - weights の入力は既知キーのみ受け付け、無効値を無視。合計が 1.0 でない場合は正規化。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合、BUY を抑制
    - BUY シグナル閾値（デフォルト 0.60）を超えた銘柄を BUY、既存保有のエグジット条件に応じて SELL を生成
    - エグジット（SELL）ルール実装:
      - ストップロス: pnl <= -8%（優先）
      - final_score が threshold 未満
      - 価格データが欠損する場合は SELL 判定をスキップして誤クローズ回避
    - signals テーブルへ日付単位で DELETE → INSERT の形で置換（トランザクションで原子性保証）
    - 生成ロジックは冪等

- トランザクション / エラーハンドリング
  - features / signals などの書き込み処理は BEGIN / COMMIT / ROLLBACK を使用して原子性を確保
  - ROLLBACK に失敗した場合は logger.warning で情報を残す設計

- ロギング
  - 各主要処理に logger を埋め込み、INFO/DEBUG/WARNING を適切に出力

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Removed
- 該当なし（初回リリース）

Security
- ニュース XML パースに defusedxml を利用（XML 攻撃対策）
- ニュース取得でのスキーム制限・受信サイズ制限・URL 正規化で SSRF/追跡パラメータ対策
- J-Quants クライアントで 401→トークン自動リフレッシュ、429/リトライ制御を実装し API 利用の堅牢性を向上

Public API（主な関数 / オブジェクト）
- kabusys.settings (Settings インスタンス)
- kabusys.build_features(conn, target_date)
- kabusys.generate_signals(conn, target_date, threshold=..., weights=...)
- data.jquants_client: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_daily_quotes, save_financial_statements, save_market_calendar, get_id_token
- data.news_collector: RSS 収集関連ユーティリティ（内部に多数のユーティリティ関数）
- research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（再公開）

注記
- DuckDB のテーブル名やスキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals, raw_prices, market_calendar など）はコード内 SQL に基づく前提があるため、利用前にスキーマの準備が必要です。
- 一部の機能（例: strategy のトレーリングストップや時間決済判定など）は実装コメントとして未実装箇所が明記されています。
- 外部依存は最小限に抑えられています（defusedxml はニュースパーサ用）。必要な依存はパッケージ配布時に requirements 等で明示してください。
CHANGELOG
=========

この変更履歴は「Keep a Changelog」に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-03-20
-------------------

Added
- 基本パッケージ構成と初期リリース（kabusys v0.1.0）。
  - パッケージエクスポート: data, strategy, execution, monitoring を公開。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動ロード（プロジェクトルートを .git / pyproject.toml から探索）。
  - ロード順序: OS 環境変数 > .env.local（上書き） > .env（未設定のみ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル／ダブルクォート内でのバックスラッシュエスケープ対応
    - インラインコメント処理（クォート外では '#' がスペースもしくはタブの直前でコメントとみなす）
  - 環境変数必須チェック用 _require と Settings クラスを提供。
  - 主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development|paper_trading|live）、LOG_LEVEL（DEBUG/INFO/...）
    - is_live / is_paper / is_dev ヘルパー

- データ収集（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔レートリミッタ実装。
  - 再試行ロジック（指数バックオフ、最大 3 回）。対象: ネットワーク/429/408/5xx。
  - 401 受信時はトークンを自動リフレッシュして 1 回リトライ。
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes: raw_prices テーブルへの冪等保存（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials テーブルへの冪等保存
    - save_market_calendar: market_calendar テーブルへの冪等保存（HolidayDivision の意味をマッピング）
  - データ型変換ユーティリティ _to_float / _to_int（空値・不正値を None に）

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集機能（デフォルトソースに Yahoo Finance を含む）。
  - セキュリティと堅牢性: defusedxml を使用して XML 攻撃を防止、受信バイト数上限（10MB）設定、URL 正規化（トラッキングパラメータ除去）、SSRF 対策を考慮した設計。
  - 記事ID の冪等生成（URL 正規化後ハッシュ化）、テキスト前処理、バルク挿入のチャンク化（デフォルト 1000 件）などを実装。

- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算。データ不足時は None。
  - calc_volatility: atr_20, atr_pct（ATR/close）, avg_turnover（20 日平均売買代金）, volume_ratio（当日 / 20 日平均）を計算。
  - calc_value: raw_financials の最新財務データと株価を組み合わせて per / roe を計算。
  - DuckDB の window 関数を用いた SQL 実装で、営業日欠損（祝日等）に対応するためスキャン範囲にバッファを設定。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date) を実装:
    - research モジュールから calc_momentum / calc_volatility / calc_value を取得してマージ
    - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）適用
    - 数値ファクターを zscore_normalize（kabusys.data.stats）で正規化し ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE → INSERT、トランザクションで原子性保証）
  - 冪等性を重視（target_date の既存行は削除してから挿入）

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - スコア変換ユーティリティ: _sigmoid（Z スコア → [0,1]）、欠損コンポーネントは中立 0.5 で補完
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。ユーザー指定 weights を検証・補正し合計 1.0 に正規化
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数 >= 3 の場合）：Bear 時は BUY シグナルを抑制
    - SELL（エグジット）判定:
      - ストップロス: 現在終値 / avg_price - 1 <= -0.08
      - スコア低下: final_score < threshold
      - エッジケース: 価格欠損時は SELL 判定をスキップ（誤クローズ防止）、features に無い保有銘柄は score=0.0 扱いで SELL 対象に
    - BUY / SELL を signals テーブルへ日付単位で置換（トランザクションで原子性保証）
    - 戻り値は書き込んだシグナル数（BUY + SELL）

- 研究支援ユーティリティ（src/kabusys/research/feature_exploration.py）
  - calc_forward_returns(conn, target_date, horizons=[1,5,21])：将来リターンを計算（horizons のバリデーションあり）
  - calc_ic(factor_records, forward_records, factor_col, return_col)：Spearman のランク相関（IC）を計算（同順位は平均ランクで処理、サンプル不足時は None）
  - rank(values)：同順位を平均ランクにするランク関数（round(..., 12) による丸めで ties 検出の安定化）
  - factor_summary(records, columns)：count/mean/std/min/max/median を計算

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Security
- news_collector に defusedxml を採用し XML 関連攻撃対策を実施。
- ニュース取得での受信サイズ上限（10MB）や URL 正規化（トラッキング削除、スキームチェック）等を導入し、メモリ DoS / SSRF を軽減。
- J-Quants クライアントで認証トークンの安全なリフレッシュとレートリミット実装により API 利用ポリシー違反や過負荷を防止。

Notes / Migration
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB / SQLite の既定パス:
  - DUCKDB_PATH= data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH= data/monitoring.db（デフォルト）
- 自動 .env ロードを無効化したいテストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB スキーマ（ルール）:
  - raw_prices, raw_financials, market_calendar, prices_daily, raw_financials, features, ai_scores, positions, signals など既定のテーブル名を前提としています。初回利用前にスキーマを準備してください（本リリースでは DDL は含まれていません）。

開発者向け
- 公開 API（主な関数 / 期待される引数）:
  - kabusys.config.settings (Settings インスタンス)
  - kabusys.data.jquants_client.get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_daily_quotes / save_financial_statements / save_market_calendar
  - kabusys.data.news_collector: RSS 収集ユーティリティ（関数名は実装参照）
  - kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.strategy.build_features / generate_signals

お問い合わせ・バグ報告
- 不具合や改善提案がある場合はリポジトリの Issue へご投稿ください。
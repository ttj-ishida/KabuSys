CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
バージョニングは semver を採用します。

[Unreleased]
------------

（現在のリポジトリ状態は最初の公開バージョン 0.1.0 に相当します。
今後の変更はこのセクションに追記してください。）

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース。主要機能群を実装。
  - パッケージエントリポイント
    - kabusys.__version__ = "0.1.0"
    - __all__ に data / strategy / execution / monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - .env パーサを実装:
    - 空行 / コメント行（先頭 #）無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープを正しく処理。
    - クォートなしの行でインラインコメント（直前が空白またはタブの場合）を扱う。
  - Settings クラスを追加し、以下のプロパティを提供:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
    - kabu_api_password (KABU_API_PASSWORD 必須)
    - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token (SLACK_BOT_TOKEN 必須)
    - slack_channel_id (SLACK_CHANNEL_ID 必須)
    - duckdb_path (デフォルト: data/kabusys.duckdb)
    - sqlite_path (デフォルト: data/monitoring.db)
    - env (KABUSYS_ENV: development/paper_trading/live を検証)
    - log_level (LOG_LEVEL の検証: DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - is_live / is_paper / is_dev ユーティリティ

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - 固定間隔レートリミッタ (120 req/min)。
    - 再試行（指数バックオフ、最大 3 回）。対象: ネットワークエラー、408/429/5xx。
    - 401 受信時はトークンを自動リフレッシュして1回リトライ（トークン自動キャッシュを実装）。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes
      - fetch_financial_statements
      - fetch_market_calendar
    - DuckDB への冪等保存関数:
      - save_daily_quotes (raw_prices テーブル、ON CONFLICT DO UPDATE)
      - save_financial_statements (raw_financials テーブル、ON CONFLICT DO UPDATE)
      - save_market_calendar (market_calendar テーブル、ON CONFLICT DO UPDATE)
    - データ正規化ユーティリティ (_to_float / _to_int) を実装。
    - fetched_at を UTC ISO8601 で記録し、look-ahead バイアスの追跡を可能に。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集モジュールを実装:
    - デフォルトソース: Yahoo Finance の business カテゴリ RSS。
    - RSS から取得した記事を raw_news へ冪等保存する設計（記事ID は正規化 URL の SHA-256 の先頭等で生成する想定）。
    - defusedxml を利用して XML Bomb 等の攻撃対策。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_ 等）除去、フラグメント削除、クエリキーソート。
    - HTTP/HTTPS スキーム以外の URL の拒否や SSRF 防止の設計方針。
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）による効率化。
    - news_symbols 等による銘柄紐付け想定。

- 研究用ファクター計算 (kabusys.research.factor_research, feature_exploration)
  - ファクター計算関数を実装（DuckDB の prices_daily / raw_financials を参照）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR 計算は true_range を正確に扱う）
    - calc_value: per / roe（raw_financials の最新レコードを使用）
  - 研究用解析ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出（LEAD を利用した1クエリ実装）
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（有効サンプルが 3 未満なら None）
    - rank: 同順位は平均ランクで扱うランク関数（浮動小数点丸めによる ties 対応に round(v,12) を使用）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装:
    - research モジュールの calc_momentum / calc_volatility / calc_value を組み合わせて features を生成。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリッピングして外れ値影響を抑制。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで実行し冪等性・原子性を確保）。
    - 欠損値や非有限値に配慮。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイド変換や欠損値は中立値 0.5 で補完する方針。
    - デフォルト重み（momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10）を採用。外部から渡された weights は検証・補完・正規化。
    - Bear レジーム検出（ai_scores の regime_score の平均が負の場合かつサンプル数 >= 3）により BUY シグナルを抑制。
    - SELL (エグジット) 条件を実装:
      - ストップロス: (close / avg_price - 1) < -8%
      - final_score が threshold 未満（score_drop）
      - 価格欠損時は SELL 判定をスキップ（誤クローズ回避）
      - 一部未実装（トレーリングストップ、時間決済は将来的な拡張領域としてコメントあり）
    - BUY / SELL を signals テーブルへ日付単位で置換（冪等性を保証）。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。

Changed
- 設計/実装方針を明確化:
  - ルックアヘッドバイアス回避のため、すべての集計・シグナル処理は target_date 時点のデータのみを使用。
  - DuckDB をデータ層として想定し、SQL と最小限の Python ロジックで処理するアーキテクチャ。
  - 外部の発注 API / execution 層への直接依存は持たない（層の分離）。
  - 冪等性・原子性を重視（ON CONFLICT / トランザクション / DELETE+INSERT のパターン）。

Fixed
- （初版につき該当なし）

Security
- defusedxml を使用した RSS 解析で XML 関連攻撃対策。
- RSS の最大受信バイト数制限によりメモリ DoS の緩和。
- ニュース URL の正規化でトラッキングパラメータを除去（プライバシー上の配慮）。

Notes / Migration / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により必須扱い（未設定時は ValueError を送出）。
- 自動 .env ロード:
  - デフォルトでプロジェクトルートの .env/.env.local が自動ロードされます。テストや CI 環境で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必要な DB テーブル（想定）:
  - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news, news_symbols 等。スキーマは実装で参照されるカラム名に合わせて準備してください。
- API レート制限:
  - J-Quants は 120 req/min を想定。クライアントは固定間隔のスロットリングでこれを守りますが、大規模の同時ジョブは注意してください。
- 将来の拡張点:
  - signal_generator 内のトレーリングストップや時間決済ロジックの追加。
  - feature_engineering / research のさらなるファクター追加や AI スコアの活用拡張。
  - news_collector の記事→銘柄マッピングの精度向上（NLP 系の統合など）。

Contact / Contributing
- バグ報告・機能提案は issue を立ててください。プルリクエスト歓迎。

-----
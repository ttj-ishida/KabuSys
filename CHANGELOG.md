# Changelog

すべての注記は Keep a Changelog の慣習に従っています。  
バージョン番号はパッケージ内の __version__ に合わせています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20

### Added
- パッケージの初期リリース。
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring

- 環境変数 / 設定管理モジュール (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env ファイルパーサ実装:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート対応（バックスラッシュエスケープ考慮）
    - インラインコメント扱いのルール（クォート内無視、未クォート時は直前スペースで判定）
  - .env 読み込み時の保護キー（OS環境変数の上書き防止）機構。
  - Settings クラス:
    - J-Quants / kabu API / Slack / DB パス / システム設定等のプロパティを提供
    - 必須環境変数チェック（_require）で未設定時は ValueError を送出
    - KABUSYS_ENV 値および LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev ヘルパー

- データ取得・保存 (kabusys.data)
  - J-Quants クライアント (jquants_client.py)
    - API レート制限遵守のため固定間隔レートリミッタ実装（120 req/min）
    - リトライ（指数バックオフ、最大3回）と 401 時の自動トークンリフレッシュ（1回のみ）
    - ページネーション対応（pagination_key を利用して全件取得）
    - fetch_* 系関数:
      - fetch_daily_quotes（株価日足、ページネーション対応）
      - fetch_financial_statements（財務データ、ページネーション対応）
      - fetch_market_calendar（JPX カレンダー取得）
    - DuckDB 保存関数（冪等: ON CONFLICT DO UPDATE）:
      - save_daily_quotes → raw_prices
      - save_financial_statements → raw_financials
      - save_market_calendar → market_calendar
    - 型変換ユーティリティ: _to_float / _to_int（安全な変換）
    - fetched_at に UTC タイムスタンプを記録（Look-ahead バイアスの追跡）

  - ニュース収集モジュール (news_collector.py)
    - RSS フィードからの記事収集と raw_news 保存ロジック
    - セキュリティ対策:
      - defusedxml による XML 攻撃対策
      - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）
      - HTTP/HTTPS スキーム以外拒否や最大受信バイト数制限（10 MB）等メモリ/SSRF 対策方針
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）で DB への負荷低減
    - デフォルト RSS ソースを提供（例: Yahoo Finance のカテゴリ RSS）

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（データ不足時は None）
    - calc_volatility: 20 日 ATR / atr_pct、20 日平均売買代金、出来高比率
    - calc_value: PER / ROE（raw_financials と prices_daily を結合）
    - 計算用のウィンドウ長やスキャン範囲は設計に基づく定数で管理（営業日→カレンダー日バッファを適用）
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括取得
    - calc_ic: Spearman のランク相関（Information Coefficient）計算（結合・欠損除外・最小サンプルチェック）
    - rank: 同順位は平均ランクを返す実装（丸めにより ties の検出漏れを防止）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
  - zscore_normalize は外部モジュール経由で re-export（kabusys.data.stats を利用）

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 実装:
    - research 側の raw factor を取得してマージ
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）
    - 指定カラムを Z スコア正規化し ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE ＋ bulk INSERT）して冪等性・原子性を確保

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 実装:
    - features / ai_scores / positions を参照して最終スコアを計算
    - コンポーネントスコア: momentum / value / volatility / liquidity / news
    - デフォルト重みとユーザ提供 weights のマージ、検証、再スケール処理
    - AI スコアは欠損時に中立（0.5）で補完、regime_score の平均で Bear 判定（サンプル数閾値あり）
    - Bear レジームでは BUY シグナルを抑制
    - BUY は閾値（デフォルト 0.60）超過銘柄に対して rank 付与
    - SELL（エグジット）判定:
      - ストップロス（終値/avg_price - 1 < -8%）
      - final_score の threshold 未満
      - 価格欠損時は SELL 判定をスキップ（誤クローズ防止）
    - signals テーブルへ日付単位の置換（DELETE + bulk INSERT、トランザクションロールバック処理あり）

### Known limitations / Notes
- signal_generator のエグジット条件のうち、トレーリングストップ（peak_price 必要）や時間決済（60 営業日超過）は未実装。positions テーブルに追加フィールドが必要。
- zscore_normalize は別モジュール（kabusys.data.stats）に依存しているため、その実装に依存。
- news_collector の記事 ID は URL ベースの正規化に依存するため、極端な URL 形式の場合は別途検証が必要。
- DuckDB のテーブル定義（schema）はこのリポジトリに含まれていないため、利用前に必要なテーブル（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news など）のスキーマを用意する必要があります。
- 外部 HTTP 操作は同期（urllib）で実装されているため、大量取得や非同期処理が必要な場合は改修の検討が必要。

### Security
- defusedxml を用いた XML パース、受信サイズ制限、URL 正規化等、外部データ取込に関する基本的な安全対策を実装。
- J-Quants API のトークン管理はキャッシュと自動リフレッシュを組み合わせ、401 の場合にのみ再取得を試みる設計。

---

（この CHANGELOG は、ソースコードの実装内容から推測して作成しています。実際のリリースノートには環境や DB スキーマ、外部依存のバージョン等の追加情報を含めることを推奨します。）
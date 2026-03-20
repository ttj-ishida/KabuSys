Keep a Changelog 形式に準拠した CHANGELOG を以下に記載します。コード内容から機能・挙動を推測してまとめています。

変更履歴 (CHANGELOG.md)
=======================

全般方針
--------
- このリポジトリは kabusys パッケージの初期リリースを想定しています。  
- 各モジュールは DuckDB をデータ層に想定し、研究（research）→ 特徴量生成 → シグナル生成 → 実行（execution）という分離されたレイヤー設計を採用しています。  
- ルックアヘッドバイアス回避、冪等性（idempotency）、トランザクション単位の原子性、外部 API 呼び出しの再試行やレート制御、安全な XML パース等を設計目標としています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-20
--------------------

Added
-----
- パッケージ初期版 kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py
    - パッケージメタ（__version__ = "0.1.0"）および主要サブパッケージを __all__ で公開。

- 環境設定・ローダー
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 により自動ロードを無効化可能（テスト向け）。
    - .env パーサ: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの適切な取り扱い。
    - 既存 OS 環境変数を保護する protected パラメータを利用した上書き制御。
    - Settings クラス: J-Quants / kabu API / Slack / DB パス（duckdb/sqlite）/ 環境（development/paper_trading/live）/ログレベル等のプロパティを提供し、必須変数未設定時に明示的なエラーを発生させる。

- Data 層：J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx をリトライ対象）。
    - 401 Unauthorized を受けた場合のトークン自動リフレッシュ（1 回のみ）と再試行。
    - ページネーション対応の fetch_* 系関数:
      - fetch_daily_quotes: 日足（OHLCV）取得（pagination_key を利用）。
      - fetch_financial_statements: 財務データ（四半期 BS/PL）取得。
      - fetch_market_calendar: JPX カレンダー取得。
    - save_* 系関数（DuckDB へ冪等保存、ON CONFLICT DO UPDATE を使用）:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - id_token のモジュールレベルキャッシュと取得関数（get_id_token）。呼び出し時の無限再帰防止フラグを実装。
    - 型変換ユーティリティ _to_float / _to_int（堅牢な変換と不正値スキップ）。

- Data 層：ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィード収集パイプライン（デフォルトで Yahoo Finance のビジネスカテゴリを参照）。
    - defusedxml を用いた安全な XML パース（XML Bomb 等対策）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を軽減。
    - URL 正規化 (スキーム/ホスト小文字化、トラッキングパラメータ除去、クエリソート、フラグメント削除) を実装（_normalize_url）。
    - 記事 ID は URL 正規化後の SHA-256 の先頭 32 文字を利用して冪等性を保証。
    - SQL バルク挿入をチャンク化（_INSERT_CHUNK_SIZE）して SQL 長・パラメータ上限を回避。ON CONFLICT DO NOTHING 等で重複対策。
    - SSRF 回避、トラッキングパラメータ除去などのセキュリティ考慮を実装。

- Research 層
  - src/kabusys/research/factor_research.py
    - モメンタム/ボラティリティ/バリューと流動性系のファクター計算関数を提供:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を DuckDB のウィンドウ関数で計算。200 行未満は None。
      - calc_volatility: atr_20（20 日 ATR）、atr_pct、avg_turnover、volume_ratio を計算。データ不足時の None 処理。
      - calc_value: raw_financials から最終財務データを結合し PER / ROE を計算（EPS が 0/欠損なら PER=None）。
    - SQL ベースでスキャン範囲を限定（バッファ日数）し、週末/祝日欠損に対処。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 与えたホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。ホライズンの妥当性チェックあり（1〜252）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算（None 値除外）。
    - rank: 同順位は平均ランクにする安定的なランク関数（round(v, 12) による丸めで ties 検出安定化）。

  - src/kabusys/research/__init__.py
    - 主要関数を公開（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize のエクスポート）。

- Strategy 層
  - src/kabusys/strategy/feature_engineering.py
    - build_features(conn, target_date):
      - research の calc_* で raw factors を取得してマージ。
      - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
      - 指定列（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を zscore_normalize（kabusys.data.stats）で正規化し ±3 でクリップ。
      - features テーブルへ日付単位で置換（DELETE + バルク INSERT）しトランザクションで原子性を保証。
      - 欠損・非数値の扱いとログ出力を実装。

  - src/kabusys/strategy/signal_generator.py
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features / ai_scores / positions を読み込み、各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
      - component スコア計算:
        - momentum: sigmoid(mom/ma200_dev) の平均。
        - value: PER を 20 を基準に 1/(1 + per/20) で評価（PER が不正時は None）。
        - volatility: atr_pct の Z スコアを反転して sigmoid。
        - liquidity: volume_ratio に sigmoid。
        - news: ai_score に sigmoid、未登録は中立補完。
      - weights はデフォルト値からフォールバックし、入力のバリデーション（未知キー除外、非数値/負値除外）、合計が 1 になるよう正規化。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 のとき）。Bear 時は BUY シグナルを抑制。
      - BUY シグナル: final_score >= threshold でランク付け（SELL 対象は除外）。
      - SELL シグナル（_generate_sell_signals）: positions の最新保有に対して
        - ストップロス: 終値/avg_price -1 < -8%（最優先）
        - final_score が threshold 未満
        - 価格欠損時は判定をスキップして誤クローズを防止
      - signals テーブルへ日付単位で置換（DELETE + INSERT）しトランザクションで原子性を保証。
      - ログ（INFO/DEBUG/警告）を豊富に出力。

- Strategy API エクスポート
  - src/kabusys/strategy/__init__.py
    - build_features / generate_signals を公開。

Security
--------
- defusedxml を使用した安全な XML パース（news_collector）。
- ニュース収集でのレスポンスサイズ制御、URL 正規化、トラッキングパラメータ除去により SSRF / トラッキング耐性を強化。
- J-Quants クライアントはレート制御・再試行・トークンリフレッシュを備え、外部 API の健全性に配慮。

Notes / 前提
------------
- DuckDB 上に以下のテーブル等が存在することを前提としている（名前やスキーマは実装側で合わせる必要あり）:
  - raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等。
- kabusys.data.stats.zscore_normalize が別モジュールで提供される前提。正規化処理はこれを利用。
- execution パッケージは空の初期プレースホルダ（src/kabusys/execution/__init__.py）として存在。
- 一部未実装/将来の拡張予定（コード内コメント）:
  - positions テーブルに peak_price / entry_date 等があれば実現可能なトレーリングストップや時間決済などの追加エグジット条件。
  - news -> symbol 紐付けロジック（news_symbols への登録）は実装想定（コード内に記載あり）。

Changed
-------
- 初期リリースのため該当なし。

Fixed
-----
- 初期リリースのため該当なし。

Removed
-------
- 初期リリースのため該当なし。

Security
--------
- defusedxml による XML の安全パース。
- ニュース収集での受信サイズ上限、トラッキングパラメータ除去、HTTP スキーム検査等の実装により一部の攻撃ベクトルを軽減。

開発者向けメモ
----------------
- 環境の自動読み込みをテストで無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings.env / log_level の値は検証され、不正値であれば ValueError を投げます。
- DuckDB 接続は呼び出し側が渡す仕様。トランザクションは各関数内で BEGIN/COMMIT/ROLLBACK を用いて管理しています。
- ロギングが各モジュールに多数配置されています。運用時はログレベルを適切に設定してください。

（以上）
Keep a Changelog
=================

すべての重要な変更点をこのファイルで記録します。  
フォーマットは Keep a Changelog に準拠します。

フォーマットの読み方:
- 各バージョンにはリリース日を添えています。
- セクションは Added / Changed / Fixed / Removed / Security を使用します。

Unreleased
----------

- なし

0.1.0 - 2026-03-20
------------------

Added
- パッケージ初回リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - top-level エクスポート: data, strategy, execution, monitoring

- 環境設定 / ロード機能 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .git または pyproject.toml を基準にプロジェクトルートを自動検出（CWD 非依存）。
  - .env ファイルパーサの実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープ対応
    - 行コメント処理（クォート内無効化、未クォート時の # は直前が空白/タブでコメント扱い）
    - 不正行のスキップ
  - 環境変数必須チェック（_require）および設定値の検証:
    - KABUSYS_ENV（development/paper_trading/live）の検証
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - デフォルト設定値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など）

- データ収集 / 保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装:
    - レート制限（固定間隔スロットリング, 120 req/min）を守る RateLimiter 実装
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
    - リトライ戦略（指数バックオフ、最大 3 回、対象: ネットワークエラー・408/429/5xx）
    - 401 発生時は自動でトークンをリフレッシュして 1 回リトライ（無限再帰回避）
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
    - JSON デコードエラーの明示的エラー化、タイムアウト設定
  - DuckDB への保存ユーティリティ（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装
    - ON CONFLICT DO UPDATE による冪等性確保
    - PK 欠損レコードのスキップと警告ロギング
    - データ変換ユーティリティ _to_float / _to_int（堅牢な変換ルール）
  - Look-ahead バイアス対策:
    - fetched_at を UTC ISO8601 で記録して「データ取得時刻」を追跡可能に

- ニュース収集 (kabusys.data.news_collector)
  - RSS からニュース記事を収集して raw_news に保存する設計を追加
  - セキュリティ上の配慮を考慮:
    - defusedxml を用いた XML パース（XML Bomb 等への耐性）
    - HTTP/HTTPS スキームのみ許可、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）
    - トラッキングパラメータ（utm_, fbclid 等）を除去する URL 正規化
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を想定して冪等性を担保
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）でパフォーマンスを配慮
  - デフォルト RSS ソース一覧を定義（例: Yahoo Finance）

- 研究用ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算
    - calc_volatility: 20日 ATR / atr_pct、20日平均売買代金、volume_ratio を計算
    - calc_value: raw_financials を用いた per / roe の取得（target_date 以前の最新レコードを使用）
    - SQL とウィンドウ関数を活用した効率的な取得、欠損時の None 扱い
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）計算（有効サンプル数判定）
    - rank / factor_summary: ランク計算（同順位は平均ランク）と基本統計量の要約を実装
  - 研究用ユーティリティを __all__ で公開（zscore_normalize は data.stats 経由で利用）

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 実装:
    - research モジュールの calc_momentum / calc_volatility / calc_value を呼び出して原因データを取得
    - ユニバースフィルタ（最低株価 _MIN_PRICE = 300 円、20日平均売買代金 _MIN_TURNOVER = 5e8 円）を適用
    - 指定カラム群の Z スコア正規化（kabusys.data.stats.zscore_normalize）と ±3 でのクリップ
    - features テーブルへの日付単位での置換（BEGIN/DELETE/INSERT/COMMIT）で冪等性と原子性を保証
    - 欠損値・非有限値への配慮（math.isfinite チェック）

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 実装:
    - features / ai_scores / positions を参照して BUY/SELL シグナルを生成し signals テーブルへ日付単位で書き込み（冪等）
    - コンポーネントスコアの計算:
      - momentum, value, volatility, liquidity, news（AI）を算出
      - Z スコアをシグモイド変換して [0,1] にマッピング
      - 欠損コンポーネントは中立値 0.5 で補完
    - final_score は重み付き合算（デフォルト重みを用意、ユーザー指定 weights の検証・正規化を実装）
    - BUY シグナル閾値デフォルト _DEFAULT_THRESHOLD = 0.60
    - Bear レジーム判定: ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合に BUY を抑制
    - エグジット（SELL）判定:
      - ストップロス: 終値 / avg_price - 1 < -8%
      - スコア低下: final_score < threshold
      - SELL は BUY より優先し、BUY リストから除外してランクを再付与
    - signals テーブルへのトランザクション処理（DELETE -> INSERT -> COMMIT）で原子性を保証

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Removed
- なし

Security
- news_collector で defusedxml を利用するなど、外部入力（RSS/XML）の安全性に配慮した実装方針を採用
- ニュース取得時のレスポンスサイズ上限によりメモリ DoS リスクを軽減

Notes / Known limitations
- 一部エグジット条件は未実装（ドキュメントに注記あり）:
  - トレーリングストップ（peak_price の追跡が positions テーブルに必要）
  - 時間決済（一定保有期間を超えたらクローズ）
- news_collector の実装はセキュリティを考慮した設計が記載されているが、ファイル末尾で関数定義が途切れているため（今回提供されたスナップショットでは）実装の一部が未掲載・未検証の可能性あり。実運用前に XML パース、URL 正規化、DB 保存の最終確認を推奨。
- data.stats の zscore_normalize 実装は別モジュール（kabusys.data.stats）に依存しているため、その実装が正しくロードされることが前提。
- 外部 API（J-Quants）との統合はリトライやレート制御を含むが、実環境のネットワーク条件や API 仕様変更に備えた監視が必要。

開発者向けメモ
- Settings クラスは環境変数の欠落時に ValueError を投げるため、CI / テスト環境での .env 制御（KABUSYS_DISABLE_AUTO_ENV_LOAD や環境変数の注入）を推奨。
- DuckDB に対する操作はトランザクションを用いて原子性を確保しているが、接続の例外管理（コネクションのライフサイクル）には呼び出し側で注意すること。
- ロギングは各モジュールに logger を用意。運用時は LOG_LEVEL を適切に設定して過度なログ出力を抑制すること。

----- 
（この CHANGELOG は提供されたソースコードの内容・docstring から推測して作成しています。実際のリリースノートとして利用する際は、テスト結果や運用上の補足情報を追記してください。）
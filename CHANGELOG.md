CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-19
--------------------

Added
- パッケージ初期リリース。
- 基本構成:
  - パッケージメタ情報: kabusys/__init__.py にてバージョン "0.1.0"、公開 API を定義。
- 環境設定管理 (kabusys.config):
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 高度な .env パーサ実装:
    - "export KEY=val" 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなし値におけるインラインコメント検出ルール
  - 既存 OS 環境変数を保護する protected 機構（.env.local は既存値を上書き可能だが OS 環境変数は保護）。
  - Settings クラスにて必須設定取得メソッドとプロパティを提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境/ログレベル検証など）。
  - KABUSYS_ENV と LOG_LEVEL の許容値検査（不正値は ValueError）。

- Data 層:
  - J-Quants API クライアント (kabusys.data.jquants_client) を実装:
    - 固定間隔の RateLimiter（120 req/min 相当）とモジュールレベルの待ち制御。
    - 再試行ロジック（最大 3 回、指数バックオフ、408/429/5xx の再試行、429 の Retry-After 優先）。
    - 401 受信時の自動トークンリフレッシュ（無限再帰防止のため allow_refresh 制御）。
    - ページネーション対応の fetch_ 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT による upsert を採用。
    - レコード保存時の PK 欠損行のスキップと警告ログ出力。
    - JSON デコード失敗や API エラー時の明瞭な例外メッセージ。
    - 数値変換ユーティリティ _to_float / _to_int （安全な型変換と異常値処理）。

  - ニュース収集モジュール (kabusys.data.news_collector) を実装:
    - デフォルト RSS ソース（Yahoo Finance）の定義。
    - RSS 解析と記事生成のフロー（URL 正規化、トラッキングパラメータ除去、content 前処理）。
    - defusedxml を用いた安全な XML パースで XML Bomb 等を防御。
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を緩和。
    - URL 正規化ロジック（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリ並び替え）。
    - DB 保存はバルク挿入をチャンク化して実行し、ON CONFLICT / INSERT RETURNING 相当の扱いを意識した実装。

- Research 層:
  - ファクター計算 (kabusys.research.factor_research):
    - calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB の window 関数を活用した営業日ベースのリターン・MA・ATR・平均売買代金等の計算。
    - データ不足時に None を返す設計（安全な欠損処理）。
  - 特徴量探索 (kabusys.research.feature_exploration):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。
    - calc_ic: Spearman のランク相関（IC）計算（同位は平均ランクで扱う）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
    - rank: 同順位を平均ランクとするランク変換ユーティリティ（丸めで ties 検出精度向上）。
  - research パッケージエクスポートを整備。

- Strategy 層:
  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering):
    - build_features: research モジュールの生ファクターを結合・ユニバースフィルタ（最低株価・平均売買代金）適用・Z スコア正規化・±3 クリップして features テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - ユニバース最低基準は _MIN_PRICE=300 円、_MIN_TURNOVER=5e8（5 億円）。
    - 価格取得は target_date 以前の最新価格を参照し、休場日や当日欠損に対応。
  - シグナル生成 (kabusys.strategy.signal_generator):
    - generate_signals: features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付け合算して final_score を生成。
    - デフォルト重みと閾値を実装（デフォルト閾値 0.60）。
    - 重みの入力検証（未知キー・非数値・負値は無視、合計を再スケール）。
    - シグモイド変換、欠損コンポーネントを中立値 0.5 で補完する設計。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上）。
    - BUY シグナル抑制（Bear 時）、SELL ロジック（ストップロス -8% など）を実装。
    - positions / prices に基づくエグジット判定（価格欠損時は判定をスキップし警告）。
    - signals テーブルへ日付単位の置換（トランザクションで原子性保証）。
  - strategy パッケージエクスポートを整備。

Changed
- 設計/実装上の方針を明確化:
  - 全ての分析・ファクター計算は DuckDB の prices_daily / raw_financials 等のローカルデータを用い、発注 API など本番の実行系依存を持たない（ルックアヘッドバイアス対策）。
  - API 取得では fetched_at を UTC で保存して「いつデータが利用可能になったか」をトレース可能に。

Fixed
- データ取り込み周りの堅牢化:
  - raw_* 保存時に PK 欠損レコードをスキップしてログ出力するようにし、不完全データでの DB 書き込み失敗を防止。
  - save_* 系で ON CONFLICT を使用し冪等性を担保。
  - _request の 401 リフレッシュで無限ループに陥らないよう allow_refresh フラグと _token_refreshed 制御を実装。
  - ネットワーク/HTTP エラー時の再試行ロジックを追加し、失敗時に明瞭な RuntimeError を投げる。

Security
- 外部データ取り込みに対する安全対策:
  - news_collector で defusedxml を使用し XML の脆弱性を緩和。
  - RSS の URL 正規化により追跡パラメータを除去、SSRF の緩和を意識した実装（スキームチェック等の準備）。
  - API クライアントでタイムアウト・最大受信サイズ等の保護を設定。

Notes
- 未実装/将来の拡張点（コード内コメントとして言及）:
  - signal_generator の SELL 条件に関して、トレーリングストップや時間決済は positions テーブルに peak_price / entry_date を保存する拡張が必要。
  - news_collector の完全な記事→銘柄紐付け処理（news_symbols）や INSERT RETURNING を利用した正確な挿入件数取得は今後の改善余地あり。

Authors
- このリリースの実装はコードベースに基づき推定して記載しています。

--- 

注: 上記は与えられたソースコードから推測できる変更点・機能をまとめた初期 CHANGELOG です。実際のリリース履歴や日付、作者情報はプロジェクトの公式記録に合わせて調整してください。
CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、コードベースから推測できる実装内容を基に作成した初期リリースの変更履歴です。

Unreleased
----------

- なし

0.1.0 - 2026-03-20
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリーポイントを定義（src/kabusys/__init__.py）。公開 API: data, strategy, execution, monitoring。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から検索（配布後もCWDに依存しない設計）。
  - .env 読み込みルール:
    - 優先順位: OS 環境変数 > .env.local > .env
    - export KEY=val 形式、クォート（シングル／ダブル）やバックスラッシュエスケープ、行内コメント処理に対応。
    - protected パラメータを用いた既存 OS 環境変数の上書き防止。
  - Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス / システム環境（development/paper_trading/live）/ログレベルの取得と検証。

- Data モジュール（src/kabusys/data/）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API 呼び出しの共通処理: レートリミット（120 req/min の固定間隔スロットリング）、リトライ（指数バックオフ、最大3回）、ページネーション対応。
    - 401 受信時の自動トークンリフレッシュ（1 回まで）と id_token のモジュールレベルキャッシュ共有。
    - GET/POST のラッパー _request を実装。429 の Retry-After ヘッダを尊重。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（それぞれページネーション対応）。
    - DuckDB への保存関数（冪等設計）:
      - save_daily_quotes: raw_prices への保存（ON CONFLICT DO UPDATE）
      - save_financial_statements: raw_financials への保存（ON CONFLICT DO UPDATE）
      - save_market_calendar: market_calendar への保存（ON CONFLICT DO UPDATE）
    - データ変換ユーティリティ: _to_float / _to_int（入力の安全な変換、空値や不正値を None にする挙動）
    - fetched_at は UTC ISO8601 で記録し、Look-ahead bias トレーサビリティを確保する設計。

  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィードから記事を取得し raw_news へ冪等保存する設計（ON CONFLICT DO NOTHING 想定）。
    - URL 正規化ユーティリティ（_normalize_url）を実装:
      - スキーム・ホスト小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント削除、クエリパラメータのソート。
    - defusedxml を用いた XML パース、安全対策（XML ボム回避）を採用。
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）やメモリ DoS 対策、バルク INSERT のチャンク化を設計に組み込み。
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。

- Research モジュール（src/kabusys/research/）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。true_range の NULL 伝播制御により集計の正確性を確保。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0 または欠損なら PER は None）。
    - DuckDB を利用した SQL ベースの実装（prices_daily / raw_financials のみ参照）。
  - feature_exploration.py:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度に取得する SQL 実装。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。有効ペアが 3 未満なら None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）や各ファクターの基本統計量（count/mean/std/min/max/median）を計算。
  - research/__init__.py で主要関数をエクスポート。

- Strategy モジュール（src/kabusys/strategy/）
  - feature_engineering.py:
    - 研究環境（research で計算した raw ファクター）から features を構築する処理を実装:
      - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20 日平均売買代金 _MIN_TURNOVER=5e8 円）を適用。
      - 数値ファクターを zscore_normalize（kabusys.data.stats）で正規化し ±3 でクリップ。
      - features テーブルへ日付単位の置換（DELETE + bulk INSERT）で冪等／原子性を確保。
  - signal_generator.py:
    - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY/SELL シグナルを生成して signals テーブルへ冪等保存。
    - コンポーネントスコア:
      - momentum/value/volatility/liquidity/news を計算するユーティリティを実装（シグモイド変換や PER に基づく value スコア等）。
    - ウェイト処理: ユーザー指定 weights を検証・補完し、合計を 1.0 にスケーリング。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数が閾値以上の場合に BUY シグナルを抑制。
    - SELL 判定（エグジット）:
      - ストップロス（終値／avg_price - 1 < -8%）を最優先
      - final_score が threshold 未満で SELL
      - positions / prices_daily を参照して判定。価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入）で原子性を保証。

- Strategy パッケージ公開（src/kabusys/strategy/__init__.py）
  - build_features, generate_signals をエクスポート。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- defusedxml を利用して RSS XML の安全なパースを実現。
- ニュース収集での URL 正規化やトラッキングパラメータ除去により、記事 ID の冪等性やトラッキング除去を考慮。
- J-Quants クライアントでトークン管理・自動リフレッシュ・リトライ制御を実装し、不正な再試行や無限ループを回避。
- .env 読み込みでファイル I/O エラー時に警告を出す設計（例外を上げてプロセスを停止しない）。

注意事項 / 既知の制限
- signal_generator の一部エグジット条件は未実装（ドキュメントに記載）:
  - トレーリングストップ（peak_price のトラッキングが positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）などは未実装
- calc_momentum / calc_volatility 等は過去データ不足銘柄について None を返す設計（欠損取り扱いが必要）。
- ニュース収集モジュールの一部（記事 ID 生成・news_symbols との紐付け・SSRF 固定的対策の一部）はドキュメントに記載された設計方針を反映しているが、提供コードの範囲で追加実装が必要な箇所がある可能性があります（例えば IP アドレス検証やソケット接続周りの実装断片は present するが未使用の変数が存在）。
- データベースは DuckDB を前提として実装されているため、実行環境に DuckDB が必要。
- Python バージョン: 型注釈（| を使ったユニオン等）や typing の利用から Python 3.10 以降を想定。

作者注
- 本 CHANGELOG はコードのドキュメント文字列（docstring）と実装内容から推測して作成しています。実際のリリースノートはプロジェクトの公式リリース情報に基づいて更新してください。
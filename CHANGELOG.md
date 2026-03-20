CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

[Unreleased]
------------

（現時点のリポジトリには未リリースの変更はありません）

[0.1.0] - 2026-03-20
-------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" のコア機能群を追加。
  - パッケージ公開情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - パブリック API: data, strategy, execution, monitoring を __all__ で公開

  - 環境設定（kabusys.config）
    - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索するため、CWD に依存しない実装。
    - .env のパースは以下をサポート/考慮:
      - 空行・# コメント行を無視
      - export KEY=val 形式を許可
      - シングル/ダブルクォート内のエスケープ文字（\）を考慮して正しく値をパース
      - クォートなし値でのインラインコメント判定（'#' の直前が空白/タブの場合はコメントと認識）
    - .env 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き、ただし OS 環境変数は保護）
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - Settings クラスを提供し、各種必須環境変数をプロパティで取得（未設定時は明瞭な ValueError を送出）
      - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを提供
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）
    - duckdb/sqlite パスはデフォルト値を提供し Path オブジェクトとして返却

  - データ取得・保存（kabusys.data.jquants_client）
    - J-Quants API クライアントを実装:
      - API レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）
      - 再試行（指数バックオフ、最大 3 回）。対象はネットワーク系エラー・HTTP 408/429/5xx。
      - 401 エラー受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰回避）
      - ページネーション対応のデータ取得（fetch_daily_quotes / fetch_financial_statements）
      - データ保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は DuckDB へ冪等に書き込み（ON CONFLICT DO UPDATE）
      - 保存時に fetched_at を UTC ISO8601 で記録し、いつデータが取得されたかトレース可能
      - レスポンス JSON のデコード失敗や HTTP エラーに対する適切なログと例外処理
      - モジュールレベルの ID トークンキャッシュを導入（ページネーション間で共有）

    - データ正規化/変換ユーティリティ:
      - _to_float / _to_int を用いて外部 API の各種フィールドを安全に変換

  - ニュース収集（kabusys.data.news_collector）
    - RSS フィードから記事を収集して raw_news に保存する基盤を実装（デフォルトで Yahoo Finance のカテゴリフィードを定義）
    - セキュリティ / 安全対策:
      - defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）を防止
      - HTTP/HTTPS スキーム以外の URL を拒否して SSRF リスクを低減（URL パース時の検証を想定）
      - 受信最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止
    - URL 正規化:
      - スキーム/ホスト小文字化、フラグメント除去、トラッキングパラメータ（utm_*, fbclid など）の除去、クエリパラメータをキーでソート
      - 記事 ID は正規化後の URL の SHA-256 ハッシュ先頭 32 文字などを用いる想定で冪等性を確保
    - テキスト前処理（URL 除去・空白正規化）を行い raw_news に ON CONFLICT DO NOTHING / バルク挿入
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）で SQL パラメータ数上限を回避
    - INSERT の結果件数を正確に返す設計（INSERT RETURNING 等を想定）

  - 研究用ユーティリティ（kabusys.research）
    - factor_research:
      - calc_momentum: 1M/3M/6M 等のモメンタム、200日移動平均乖離を計算
      - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算
      - calc_value: 財務データ（raw_financials と prices_daily）から PER, ROE を計算（EPS が 0 または欠損なら PER=None）
      - 実装は DuckDB の SQL ウィンドウ関数を多用し、営業日欠損（週末等）に対するバッファを考慮したスキャン範囲を採用
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）での将来リターンを一括算出。ホライズン入力の検証（1..252）あり
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）
      - rank: 同順位は平均ランクを与えるランク化関数（丸めを行い浮動小数誤差による ties 検出漏れを防止）
      - factor_summary: count/mean/std/min/max/median を算出する統計サマリー
    - 研究モジュールは外部依存（pandas 等）を使わず、DuckDB 接続を受け取る設計

  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - build_features(conn, target_date) を実装:
      - research の calc_momentum / calc_volatility / calc_value から生ファクターを取得
      - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円）を適用
      - 指定の数値ファクターを Z スコア正規化（zscore_normalize を使用）し ±3 でクリップ（外れ値抑制）
      - features テーブルへ日付単位の置換（DELETE → bulk INSERT をトランザクションでラップ）により冪等性と原子性を確保
      - 価格取得は target_date 以前の最新価格を参照し、休場日や当日の欠損に対応

  - シグナル生成（kabusys.strategy.signal_generator）
    - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
      - features テーブルと ai_scores を統合し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
      - スコア変換にシグモイド関数を用いる（Z スコアを [0,1] に変換）
      - コンポーネント欠損は中立値 0.5 で補完して欠損銘柄の不当な降格を防止
      - デフォルトの重みは StrategyModel.md Section 4.1 相当値を使用し、ユーザ提供 weights は検証・補完・リスケールされる（未知キー、非数値、負値は無視）
      - Bear レジーム判定: ai_scores の regime_score 平均が負の場合を Bear と判断（サンプル数不足時は Bear とみなさない）
      - BUY シグナルは final_score >= threshold の銘柄（Bear では BUY を抑制）
      - SELL シグナル（エグジット判定）:
        - ストップロス: 現在終値 / エントリー平均価格 - 1 <= -8%
        - スコア低下: final_score < threshold
        - 価格欠損時は SELL 判定をスキップ（誤クローズ防止）
        - 保有銘柄が features に存在しない場合は final_score=0.0 と見なして SELL 対象とする
      - SELL を優先して BUY から除外し、最終的に signals テーブルへ日付単位の置換で書き込み（トランザクション + バルク挿入）
      - ログ出力により処理状況や警告を記録（例: features が空、weights が不正、ROLLBACK 失敗の警告等）

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Notes / Known limitations
- 一部のエグジット条件は未実装（戦略仕様書に基づく TODO）
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過など、positions に entry_date が必要）
- news_collector の記事と銘柄紐付け（news_symbols）等は基盤を整備済みだが、実際のマッピングロジックは運用時の追加開発が必要
- data.stats.zscore_normalize は別モジュールとして想定されており、feature_engineering / research モジュールから利用される（本リリースでは当該ユーティリティが存在する前提）

作者・貢献者へ
- 初回リリースのため、追加のテストケース・エンドツーエンドの検証を推奨します。特に外部 API 呼び出し（J-Quants）周りのリトライ／レート制御や、DuckDB への大量データ挿入時のパフォーマンス検証を行ってください。
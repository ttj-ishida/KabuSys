CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

（現時点のリポジトリは初期リリース相当の状態のため、未公開の変更はありません。）

[0.1.0] - 2026-03-20
--------------------

Added
- 初回公開リリース (0.1.0)
  - パッケージ概要
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - エクスポート済みモジュール: data, strategy, execution, monitoring

  - 環境設定 / 設定管理 (src/kabusys/config.py)
    - .env / .env.local を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト等で利用）。
    - .env パーサ実装:
      - export KEY=val 形式対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ対応
      - インラインコメントの取り扱い（クォート有無に応じて適切に無視）
    - OS 環境変数を保護する protected 上書きロジック（.env.local は override=True だが既存 OS 環境変数は上書きしない）。
    - Settings クラス提供（プロパティ経由で設定取得）:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須項目としてチェック（未設定時は ValueError）。
      - KABU_API_BASE_URL / DUCKDB_PATH / SQLITE_PATH のデフォルト値を提供。
      - KABUSYS_ENV, LOG_LEVEL のバリデーション（許容値を定義）。
      - is_live / is_paper / is_dev の便利プロパティ。

  - データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - J-Quants API 用クライアント実装。
    - レート制限対応: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
    - 再試行ロジック: 指数バックオフ、最大 3 回（408/429/5xx を対象）。429 の場合は Retry-After を優先。
    - 401 ハンドリング: トークン期限切れ時に自動でリフレッシュして 1 回リトライ（無限再帰防止処理あり）。
    - ページネーション対応の fetch 関数:
      - fetch_daily_quotes (日足 OHLCV)
      - fetch_financial_statements (財務四半期データ)
      - fetch_market_calendar (JPX カレンダー)
    - DuckDB 保存ユーティリティ:
      - save_daily_quotes / save_financial_statements / save_market_calendar を実装（ON CONFLICT DO UPDATE により冪等性確保）。
      - fetched_at を UTC ISO8601 形式で記録。
    - 入出力変換ユーティリティ: _to_float / _to_int（不正入力を安全に None に変換）。
    - モジュールレベルで ID トークンキャッシュを持ち、ページネーション間でトークンを共有。

  - ニュース収集 (src/kabusys/data/news_collector.py)
    - RSS フィードから記事収集し raw_news に保存する基本実装。
    - セキュリティ / 頑健化:
      - defusedxml を使用して XML ボム等の攻撃を防止。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定しメモリ DoS を緩和。
      - URL 正規化機能 (_normalize_url): トラッキングパラメータ除去 (utm_*, fbclid, gclid 等)、スキーム/ホストの小文字化、フラグメント削除、クエリパラメータソート等。
      - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を用いて冪等性を確保。
    - DB 側は ON CONFLICT DO NOTHING / バルク挿入チャンク化で高速かつ冪等に保存。
    - デフォルト RSS ソースとして Yahoo Finance のビジネス RSS を採用。

  - 研究（research）モジュール (src/kabusys/research/...)
    - ファクター計算 (factor_research.py)
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率(ma200_dev) を計算。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR、相対ATR(atr_pct)、20 日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。true_range の NULL 伝播を考慮。
      - calc_value: raw_financials と prices_daily を組み合わせ、PER / ROE を算出（EPS が 0/欠損の場合は PER を None）。
      - DuckDB のウィンドウ関数を活用し、性能面を考慮したスキャン範囲を設定。
    - 特徴量探索 (feature_exploration.py)
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証を実施。
      - calc_ic: スピアマンランク相関（IC）を実装。サンプル不足（<3）や分散 0 の場合は None を返す。
      - rank: 平均順位 (ties を平均ランク) の実装。浮動小数点の丸め誤差に配慮して round(..., 12) を使用。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを実装（None を除外）。

  - 戦略 (src/kabusys/strategy/...)
    - 特徴量エンジニアリング (feature_engineering.py)
      - build_features(conn, target_date): research モジュールの生ファクターを取得・マージし、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
      - 指定数値カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
      - features テーブルへの日付単位置換（BEGIN/DELETE/INSERT/COMMIT）で冪等性と原子性を保証。
    - シグナル生成 (signal_generator.py)
      - generate_signals(conn, target_date, threshold=0.60, weights=None):
        - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
        - シグモイド変換・欠損値の中立補完（0.5）により頑健性を確保。
        - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を提供。ユーザ指定 weights は検証・正規化（非数値・負値は無視、合計を 1.0 に再スケール）。
        - Bear レジーム判定 (_is_bear_regime)：ai_scores の regime_score 平均が負なら BUY を抑制（サンプル数閾値あり）。
        - BUY: final_score >= threshold による選定（Bear 時は抑制）。
        - SELL: positions テーブルと最新価格からストップロス（-8%）およびスコア低下を判定。価格欠損時は SELL 判定をスキップして誤クローズを防止。
        - signals テーブルへの日付単位置換で冪等性を確保。BUY のランク付けや SELL 優先ポリシーを実装。
      - 実装上の既知の未実装点:
        - トレーリングストップ（peak_price 必要）
        - 時間決済（保有 60 営業日超過）などは未実装（positions テーブル側の情報が必要）

  - ロギングとエラーハンドリング
    - 各処理で適切な logger レベルのメッセージ（info/warning/debug）を出力。
    - DB トランザクションで例外発生時は ROLLBACK を試行し、失敗した場合は警告を出す。

Security
- 外部通信・パース処理に対する安全策を導入:
  - J-Quants クライアント: レート制限、再試行制御、トークン自動リフレッシュなどにより API 利用の堅牢化。
  - news_collector: defusedxml 使用、受信サイズ制限、URL 正規化（トラッキング除去）、挿入時の冪等性などで悪意ある入力や DoS を緩和。
  - .env ローダー: ファイル読み込み失敗時に warnings.warn を発行し安全に退避。

Breaking Changes
- なし（初回リリース）。

Migration / Setup Notes
- 必須環境変数を設定してください:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。テスト環境等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Known Issues / Limitations
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price や entry_date の情報が必要。
- news_collector の SSRF / IP ホワイトリスト等の厳密なネットワーク検証は今後強化の余地あり（モジュール内に ipaddress, socket などのインポートはあるが実装詳細は拡張可能）。
- research モジュールは外部ライブラリ（pandas 等）に依存しない設計。大量データでの性能チューニングは今後の課題。

Acknowledgments
- 本リリースはシステム設計に関するドキュメント（StrategyModel.md, DataPlatform.md 等）の仕様を実装する形で作成されています。

---
注: 上記はソースコードの内容から推測して作成した CHANGELOG です。実際の変更履歴やリリース日付・項目はリポジトリの開発履歴に合わせて調整してください。
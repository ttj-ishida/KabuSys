# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。本リポジトリで公開された最初のリリースを記録しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-19

初回リリース — 日本株自動売買システムのコア機能を実装しました。主にデータ取得・保存、リサーチ用ファクター計算、特徴量エンジニアリング、シグナル生成、設定管理、ニュース収集などの基盤を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化とバージョン情報を追加 (kabusys.__init__).
  - モジュールエクスポート: data, strategy, execution, monitoring を公開。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動で .env/.env.local をロード。
  - .env パーサー: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応する堅牢な行パース実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑制可能。
  - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベル等のプロパティを提供（必須環境変数未設定時は ValueError を送出）。
  - 有効な env 値 (development/paper_trading/live) とログレベルの検証を実装。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応の fetch_ 関数群:
      - fetch_daily_quotes (株価日足)
      - fetch_financial_statements (財務データ)
      - fetch_market_calendar (マーケットカレンダー)
    - HTTP レスポンスの JSON デコードエラー検出と例外化。
  - DuckDB への冪等保存関数:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を用いて保存。
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE を用いて保存。
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE を用いて保存。
    - データ整形・型変換ユーティリティ (_to_float/_to_int) を実装し、不正行はスキップしてログに警告を出力。
    - fetched_at を UTC ISO8601 で記録し、Look-ahead バイアス回避のため取得時刻を保持。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを取得して raw_news へ保存する基盤を実装。
  - 安全対策: defusedxml を使用して XML 攻撃を緩和、HTTP(S) スキーム検証、受信サイズ上限 (10MB) 設定。
  - URL 正規化処理: トラッキングパラメータ (utm_*, fbclid 等) の除去、クエリパラメータのソート、フラグメント削除を実装。
  - 記事ID 生成ポリシー（URL 正規化後の SHA-256 ハッシュを使用）により冪等性を確保。
  - チャンク化してバルク INSERT を実行し、INSERT RETURNING 相当で挿入数を正確に扱う設計（SQL チャンクサイズ制御）。

- リサーチ（research）モジュール
  - ファクター計算 (kabusys.research.factor_research):
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true_range の欠損制御を含む）。
    - calc_value: per, roe を raw_financials と prices_daily から計算（target_date 以前の最新財務データを取得）。
    - 各関数は prices_daily / raw_financials のみ参照し、結果を (date, code) ベースの dict リストで返す。
  - 特徴量探索 (kabusys.research.feature_exploration):
    - calc_forward_returns: target_date から各ホライズン先の将来リターン（デフォルト [1,5,21]）を計算。ホライズンは営業日ベースで検証。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（結合・無効値除外、最小サンプル数チェック）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を提供。
  - 外部依存を避け、標準ライブラリと DuckDB SQL を活用する実装方針を採用。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research の calc_momentum/calc_volatility/calc_value を統合して features テーブル用レコードを構築。
    - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）を適用し ±3 でクリップ。
    - 日付単位で既存行を DELETE してから INSERT（トランザクション + バルク挿入）することで冪等性と原子性を保証。
    - 欠損や非有限値に対して安全に処理。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features / ai_scores / positions / prices_daily を参照して銘柄ごとのコンポーネントスコアを計算し、final_score を導出。
    - コンポーネント:
      - momentum（momentum_20 / momentum_60 / ma200_dev をシグモイド変換して平均）
      - value（PER を 20 ベースでスケーリング）
      - volatility（atr_pct の Z スコアを反転してシグモイド）
      - liquidity（volume_ratio をシグモイド）
      - news（AI スコアをシグモイド、未登録は中立）
    - デフォルト重みと閾値:
      - デフォルト重み: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10
      - デフォルト BUY 閾値: 0.60
      - ユーザ重みは検証・フィルタリングされ、合計が 1.0 になるようリスケールされる。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合（ただしサンプル数閾値あり）に BUY を抑制。
    - エグジット条件（SELL）:
      - ストップロス: 現在価格が avg_price より 8% 以上下落したら即時 SELL。
      - スコア低下: final_score が threshold 未満なら SELL。
      - SELL 優先ポリシー: SELL 対象を BUY リストから除外し、BUY のランクを再付与。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性を保証。

- その他ユーティリティ / 設計上の配慮
  - ルックアヘッドバイアス回避方針を各所に明記（target_date 時点のデータのみを使用、fetched_at を記録）。
  - SQL クエリやウィンドウ関数を多用し、DuckDB 上で効率的に集計を実施。
  - トランザクション管理 (BEGIN/COMMIT/ROLLBACK) による原子性保証と、ROLLBACK 失敗時のログ警告を実装。
  - ロギング（logger）による処理状況・警告出力を多くの箇所で導入。

### 変更 (Changed)
- 新規リリースのため該当なし。

### 修正 (Fixed)
- 新規リリースのため該当なし。

### 削除 (Removed)
- 新規リリースのため該当なし。

### 既知の制約 / 今後の TODO
- signal_generator の一部エグジット条件は未実装（トレーリングストップ、時間決済等）であり、positions テーブルに peak_price や entry_date 等の追加情報が必要。
- news_collector の RSS フィードソースはデフォルトに Yahoo Finance のみを設定。拡張は可能。
- 一部の SQL 実行や外部 API 呼び出しに対する単体テスト・統合テストは今後追加予定。
- execution モジュールは空モジュールのプレースホルダ（発注層）として存在。実稼働連携のため実装が必要。

---

このリリースはプロジェクトの機能的基盤を確立するものです。README とドキュメントに記載の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してご利用ください。
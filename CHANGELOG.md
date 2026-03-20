# Changelog

すべての重要な変更は Keep a Changelog の原則に従って記録しています。  
フォーマット: https://keepachangelog.com/ （訳注: 本ファイルはコードベースからの推測に基づく初期リリース記録です）

## [Unreleased]
- 今のところ未リリースの変更はありません。

## [0.1.0] - 2026-03-20
初回公開リリース。以下の主要機能と実装が含まれます。

### 追加 (Added)
- パッケージ基礎
  - パッケージのメタ情報（kabusys.__version__ = "0.1.0"）と公開 API（__all__）を追加。
  - サブパッケージ構成: data, strategy, execution, monitoring（execution は空の初期モジュール）。

- 環境設定 / config
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に自動探索。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env の行パーサを実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント処理）。
  - Settings クラスを追加し、アプリケーション設定（J-Quants / kabu API / Slack / DB パス / 環境フラグ / ログレベルなど）をプロパティ経由で取得。
  - 入力検証: KABUSYS_ENV と LOG_LEVEL の許容値チェック、必須キー未設定時は ValueError を発生させる _require。

- データ取得 / data.jquants_client
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx のリトライ挙動、429 の Retry-After 優先）。
    - 401 発生時はトークンを自動リフレッシュして一度だけリトライする仕組みを実装。
    - ページネーション対応（pagination_key の追跡）。
    - データ取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB へ冪等に保存するユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を利用）。
    - レスポンスの fetched_at を UTC ISO8601 で記録して Look-ahead をトレース可能にする。
    - 型変換ユーティリティ (_to_float / _to_int) を提供して不正な文字列を安全に扱う。

- ニュース収集 / data.news_collector
  - RSS フィードから記事を収集し raw_news に保存する基盤実装。
    - デフォルト RSS ソースとして Yahoo Finance を設定。
    - 記事 ID は正規化 URL を SHA-256（先頭32文字）でハッシュ化して冪等性を確保。
    - URL 正規化: スキーム/ホストの小文字化、トラッキングパラメータ（utm_*, fbclid, gclid 等）の除去、クエリソート、フラグメント削除。
    - defusedxml を使った XML パース（XML Bomb 防御）。
    - HTTP レスポンス上限（MAX_RESPONSE_BYTES = 10MB）設定でメモリ DoS を軽減。
    - DB バルク挿入最適化（チャンク、1 トランザクションまとめ、ON CONFLICT DO NOTHING / INSERT RETURNING を想定）。

- 研究（Research）モジュール
  - factor_research: モメンタム / ボラティリティ / バリュー算出ロジックを実装。
    - calc_momentum: 約1ヶ月/3ヶ月/6ヶ月のリターン、200日移動平均乖離率（ma200_dev）。窓サイズ不足時は None を返す。
    - calc_volatility: 20日 ATR と相対 ATR（atr_pct）、20日平均売買代金、出来高比率（volume_ratio）。true_range の NULL 伝播に注意した実装。
    - calc_value: raw_financials から最新の財務情報を取得し PER / ROE を算出（EPS が 0/欠損の場合は None）。
  - feature_exploration:
    - calc_forward_returns: LEAD を使った将来リターン計算（horizons のバリデーション・デフォルト [1,5,21]）。
    - calc_ic: スピアマンのランク相関（IC）計算。ties の処理（平均ランク）を行い、有効レコードが 3 未満なら None。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ関数。
    - rank: 同順位は平均ランクとするランク変換ユーティリティ（浮動小数丸めで ties 検出の安定化）。
  - research パッケージ __all__ で主要ユーティリティを公開。

- 戦略（Strategy）モジュール
  - feature_engineering.build_features:
    - research で計算した生ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）を行い、±3 でクリップして外れ値の影響を抑制。
    - DuckDB の features テーブルに対し日付単位で delete→bulk insert を行い、トランザクションで原子性を確保（冪等）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換や平均化、欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を用い、ユーザ指定の weights を受け付けつつ正規化（合計1.0）する安全な処理。
    - Bear レジーム検出（ai_scores の regime_score の平均が負 → BUY を抑制。サンプル数不足時は Bear とみなさない）。
    - BUY シグナル閾値デフォルト 0.60。
    - エグジット判定（STOP-LOSS: pnl <= -8%、final_score < threshold）を実装し SELL シグナルを生成。SELL は BUY より優先して BUY リストから除外。
    - signals テーブルへ日付単位の置換を行い、トランザクションで原子性を確保。

### 変更 (Changed)
- （初期リリースのため変更履歴はありませんが、設計上の考慮点・振る舞いを README 等に記載済み）
  - SQL クエリや集計ロジックはデータ欠損・休日を考慮して最新価格取得やウィンドウ処理で安全に動作するよう実装。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件は未実装（コメントあり）:
  - トレーリングストップ（peak_price に依存、positions テーブルの拡張が必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の完全な記事パース・銘柄紐付け処理（news_symbols への関連付け）はドキュメントに示唆はあるが実装詳細は追加実装が必要。
- monitoring モジュール・execution 層は外部 API 呼び出しや実際の発注に関わるため、現状は分離されている（将来的に発注ロジックや監視処理の追加予定）。
- 外部依存:
  - defusedxml を利用（XML の安全パース）するため、運用環境にて該当パッケージの導入が必要。

### セキュリティ (Security)
- news_collector:
  - defusedxml による XML 攻撃対策、HTTP レスポンス上限によるメモリ DoS 対策、許可外スキーム拒否など SSRF/DoS に配慮した実装。
- jquants_client:
  - トークン自動リフレッシュ機能を実装し、機密情報の取り扱いを明確化（settings 経由での取得）。

---

（注）本 CHANGELOG は提示されたソースコードの内容から機能・設計意図を推測して作成した初期リリース向けのまとめです。実際のリリースノートとして使う場合は、プロジェクトのリリース日や変更履歴に基づき適宜修正してください。
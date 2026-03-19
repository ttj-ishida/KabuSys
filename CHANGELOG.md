# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装しました。

### 追加 (Added)
- パッケージ初期化
  - パッケージメタ情報を設定（kabusys.__version__ = 0.1.0）。
  - 公開 API を __all__ で定義。

- 環境設定 / ロード (.env 対応)
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env の柔軟なパース実装（コメント・export KEY=val・クォート内エスケープ等に対応）。
  - OS 環境変数を保護する override/protected の仕組みを実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、必須キー取得時の検証（未設定時は ValueError）、既定値、列挙的妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）を実装。

- データ取得 / 保存 (J-Quants)
  - J-Quants API クライアントを実装（jquants_client）。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）・HTTP 429 の Retry-After 考慮・ネットワークエラー再試行。
    - 401 発生時の自動トークンリフレッシュ（1 回）とモジュール内トークンキャッシュ。
    - ページネーション対応のデータ取得（株価・財務・市場カレンダー）。
    - DuckDB へ冪等保存する関数を実装（raw_prices / raw_financials / market_calendar）と ON CONFLICT 更新ロジック。
    - データ型変換ユーティリティ (_to_float/_to_int) を実装。

- ニュース収集
  - RSS フィードからニュースを収集する news_collector を実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES）・HTTP スキーム制限など安全対策。
    - 記事IDを正規化 URL のハッシュで生成し冪等性を担保。
    - DB へのバルク挿入を想定したチャンク処理。

- 研究用ファクター計算 / 探索
  - research モジュールを提供。
  - factor_research:
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日ATR, 相対ATR, 平均売買代金, 出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算。
    - 欠損やウィンドウ不足時の None ハンドリング。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman rank）計算（ランク処理・同順位平均ランク対応）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
    - rank ユーティリティ。

- 特徴量エンジニアリング
  - strategy.feature_engineering.build_features 実装。
    - research の生ファクターを読んでマージ、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - DuckDB の features テーブルへ日付単位の置換（BEGIN/DELETE/INSERT/COMMIT）で冪等・原子性を担保。

- シグナル生成
  - strategy.signal_generator.generate_signals 実装。
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、None を中立値 0.5 で補完するポリシーを採用。
    - デフォルト重み・ユーザー指定 weights の検証・補完・再スケーリング処理を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負、ただしサンプル数閾値あり）。
    - BUY（閾値 0.60）および SELL（ストップロス -8%、スコア低下）を判定。
    - positions / prices データを参照してエグジット判定。signals テーブルへ日付単位の置換で保存。

### 変更 (Changed)
- 該当なし（初回リリースのため）。

### 修正 (Fixed)
- 該当なし（初回リリースのため）。

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML による攻撃を防止。
- news_collector にて受信サイズ上限・HTTP スキーム検査・トラッキングパラメータ除去等の入力正規化を実装し、メモリ DoS や SSRF のリスクを低減。
- J-Quants クライアントの HTTP レスポンス処理で JSON デコードエラーを明示的に検出・報告。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件は未実装（コメントに明記）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の具体的な RSS フィード登録・DB スキーマとの結合ロジック（news_symbols などの紐付け処理）は実装方針はあるが、ここに含まれるコードスニペットは正規化ユーティリティや定数実装までで、フルパイプラインの統合テストは別途必要。
- 一部モジュールは外部依存（DuckDB 接続、J-Quants API、Slack 等）に依存するため、運用時に環境変数の設定・DB スキーマ準備が必要。
- get_id_token/get requests は実際の API レスポンス仕様に依存するため、実運用前にエンドポイントの挙動確認を推奨。

---

今後のリリースで予定している改善例:
- トレーリングストップ / 時間決済の実装
- AI スコアの収集パイプラインとニュース→銘柄紐付け精度向上
- 単体テスト・統合テストの追加と CI ワークフロー整備
- モニタリング/アラート用の Slack 通知統合（設定は Settings に追加済み）
- パフォーマンス改善（大規模データでの DuckDB クエリ最適化）

（必要があれば、この CHANGELOG を基にリリースノートやリリースタグ向けの要約を作成します。）
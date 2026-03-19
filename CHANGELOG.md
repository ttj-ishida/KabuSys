# CHANGELOG

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-19

初期リリース。日本株の自動売買／リサーチ基盤のコア機能を提供します。

### 追加
- パッケージ初期化
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。
  - バージョン情報を __version__ = "0.1.0" で管理。

- 設定/環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス等の設定取得を型安全に提供。
  - 設定値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（prices, financials, market calendar の取得）。
  - レート制限対策（固定間隔スロットリング、デフォルト 120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
  - ページネーション対応。
  - DuckDB への冪等保存関数を実装（raw_prices / raw_financials / market_calendar、ON CONFLICT DO UPDATE）。
  - 数値変換ユーティリティ（_to_float / _to_int）を導入（不正データの安全処理）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの収集・正規化処理を実装（デフォルトに Yahoo Finance のカテゴリ RSS）。
  - 記事 URL 正規化（トラッキングパラメータ削除、ソート、フラグメント削除）。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
  - defusedxml による XML パースで XML Bomb などの攻撃に対処。
  - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、HTTP スキーム検証、SSRF 緩和の考慮。
  - バルク INSERT チャンク化による DB への効率的保存。

- リサーチ（kabusys.research）
  - ファクター計算モジュール（factor_research）を実装：
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe、raw_financials から最新財務を参照）
  - 特徴量探索モジュール（feature_exploration）を実装：
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応・入力検証あり）
    - IC（Spearman のランク相関）計算（calc_ic）とランク付けユーティリティ（rank）
    - factor_summary による統計サマリー計算
  - 外部依存を抑え、DuckDB の prices_daily / raw_financials のみ参照する設計。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research の生ファクターを読み込み、ユニバースフィルタ（最低株価・最低売買代金）を適用。
  - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
  - features テーブルへ日付単位で置換（トランザクション + バルク挿入で冪等性・原子性を保証）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースの各コンポーネントから final_score を算出。
  - デフォルト重み・閾値を実装し、ユーザ指定の weights を検証・正規化（未知キー・不正値は無視、合計が 1 に再スケール）。
  - Bear レジーム判定（ai_scores の regime_score が負の平均のとき）により BUY シグナルを抑制。
  - BUY/SELL シグナルを生成し、signals テーブルへ日付単位で置換（トランザクション管理）。
  - エグジット判定（ストップロス、スコア低下）を実装。売却優先ポリシーにより SELL 対象は BUY から除外。
  - 欠損値に対する中立値補填（None 部分は 0.5 で補完）で不当な降格を防止。

### 変更（設計）
- ルックアヘッドバイアス防止設計を明確化
  - すべての計算は target_date 時点で入手可能だったデータのみを参照する方針を採用（fetched_at の記録等）。
- DuckDB を中心としたデータフロー設計（SQL ウィンドウ関数や一括挿入を多用）により計算・保存の一貫性と効率を重視。

### 修正（実装上の安全・堅牢化）
- HTTP 周りでの例外処理と再試行処理を強化（JSON デコード失敗時のエラー情報、429 の Retry-After 優先）。
- DB トランザクション（BEGIN/COMMIT/ROLLBACK）で失敗時に適切にロールバック、かつロールバック失敗時はログ出力。
- 不正・欠損データをスキップする処理を一貫して導入（PK 欠損行のスキップと警告ログ）。

### セキュリティ
- RSS パーサーに defusedxml を使用して XML による攻撃を緩和。
- ニュース URL の正規化とトラッキングパラメータ除去、HTTP スキームチェックにより SSRF・追跡パラメータの影響を低減。
- API トークンの自動リフレッシュは最小化され、無限再帰を防ぐ仕組み（allow_refresh フラグ）を導入。

### パフォーマンス
- レート制限を守る固定間隔スロットリングを実装し、API 呼び出しの安定性を向上。
- DuckDB へのバルクインサートと executemany 使用、news_collector のチャンク挿入などで DB 操作を効率化。
- SQL 側でウィンドウ関数を活用し、計算を DB 内でまとめて実行することで Python 側オーバーヘッドを低減。

### 未実装 / 既知の制限
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加が必要で現状未実装（コード内に注記あり）。
- news_collector の記事→銘柄紐付け（news_symbols）実装は注記されているが、紐付けロジックの完全実装状況は利用に応じて要確認。
- execution パッケージは初期化ファイルのみ（公開 API を提供するレイヤーは別途実装予定）。

---

今後のリリースでは以下の項目を想定しています（優先度順）:
- execution 層（kabu ステーション等との実際の注文発行ロジック、ロギング・リトライ・安全制御）
- monitoring / alerting 機能（Slack 通知統合の実装・テスト）
- news と銘柄の自動マッチング改善（NLP を用いた抽出精度向上）
- テストカバレッジ拡充と CI ワークフローの整備

（この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートとは異なる場合があります。）
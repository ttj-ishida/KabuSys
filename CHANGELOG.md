# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に従います。  
比較可能性と利用者向けの参考のため、実装上の設計方針や既知の制限も併記しています。

最新: [0.1.0] - 2026-03-19

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19
初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開用 __all__ と __version__ を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
  - .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により抑制可能。
  - .env ファイルのパース実装（コメント行、export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理 等に対応）。
  - 環境設定取得用 Settings クラスを提供。J-Quants / kabuAPI / Slack / DB パス 等のプロパティを定義し、必須値未設定時に明示的な例外を投げる。
  - 環境変数値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）。

- Data 層（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - 株価日足、財務データ、マーケットカレンダーの取得機能（ページネーション対応）。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライロジック（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュ対応。
    - DuckDB へ冪等保存するユーティリティ（raw_prices / raw_financials / market_calendar に対し ON CONFLICT 相当の挙動）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead bias のトレーサビリティを確保。
    - 型変換ユーティリティ（_to_float / _to_int）で不正値や空値を安全に扱う。

  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィードから記事を取得して raw_news に保存する処理の下地を実装。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリソート）を実装。
    - セキュリティ対策（defusedxml を用いた XML 攻撃対策、受信サイズ上限／SSRF 回避の方針）を備える設計。
    - 記事 ID の冪等生成（URL 正規化後の SHA-256 部分採用など）を想定。

- Research 層（kabusys.research）
  - ファクター計算群を実装（kabusys.research.factor_research）
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
    - Volatility（atr_20 / atr_pct / avg_turnover / volume_ratio）
    - Value（per / roe、raw_financials から最新財務データを参照）
    - DuckDB の SQL を利用した営業日ベース窓処理（LAG / AVG / LEAD 等）で実装。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライゾン、デフォルト [1,5,21]）。
    - IC（Information Coefficient：Spearman の ρ）計算。
    - factor_summary（count/mean/std/min/max/median）と rank（同順位は平均ランク）ユーティリティ。
  - zscore_normalize を外部公開（kabusys.research.__init__ 経由で再公開）。

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research 層の生ファクターをマージし、ユニバースフィルタ（最低株価／最低平均売買代金）を適用。
    - Z スコア正規化（指定列）、±3 でのクリップ、features テーブルへの日付単位 UPSERT（トランザクションで原子性確保）。
    - 処理は target_date 時点のデータのみ使用（ルックアヘッドバイアス対策）。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - 重み付け合算による final_score 計算（デフォルト閾値 0.60）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、十分なサンプル数がある場合に BUY を抑制）。
    - エグジット条件（ストップロス: -8%、final_score の低下）に基づく SELL シグナル生成。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - ユーザー指定の weights の検証・リスケーリングの実装（未知キー・非数値・負値を無視）。

- API エントリポイント
  - strategy モジュールの公開 API: build_features, generate_signals を公開。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector は defusedxml を使用して XML の脆弱性を緩和。
- RSS ダウンロード時の受信サイズ上限（10 MB）や URL 正規化・スキームチェックにより SSRF / DoS のリスクを軽減する設計が反映されています。
- J-Quants クライアントはトークン自動リフレッシュ時の無限再帰を防ぐ制御を実装。

### 既知の制限 / 未実装事項
- signal_generator 内の一部エグジット条件（トレーリングストップや時間決済）はコメントで未実装と示されており、追加の position テーブルカラム（peak_price / entry_date 等）を必要とします。
- news_collector の RSS パース／DB 永続化の完全実装（ID ハッシュ化・news_symbols の紐付け 等）は設計方針を示した段階で、実際の運用上の細部（チャンク処理や INSERT RETURNING を用いた挿入数返却など）は今後の実装が想定されます。
- J-Quants API クライアントは HTTP レスポンスの JSON デコード失敗時に明示的エラーを返すが、取得データのスキーマ変化に対する追加検証は今後の改善点です。
- research 層は外部依存（pandas 等）を排除して標準ライブラリ＋DuckDB SQL で実装しているため、大規模データに対するメモリ・性能チューニングは今後の課題。

### 互換性 (Compatibility)
- 本リリースは初回公開のため後方互換性注記はありません。

### 開発ノート（簡易）
- 主要な設計方針はソース内ドキュメントに記載（ルックアヘッドバイアス回避、冪等性、トランザクションによる原子性、セキュリティ対策等）。
- 環境依存設定は settings を通じて参照することを想定。CI / テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動 .env ロードを抑制可能。

---

（注）本 CHANGELOG はソースコード内のコメント・実装から推測して作成した初版です。実際の配布リリースノートとして使用する場合は、テスト・リリース時の差分や既知のバグ修正情報を追記してください。
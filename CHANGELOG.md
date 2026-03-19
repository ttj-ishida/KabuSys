# Changelog

すべての注記は Keep a Changelog の形式に準拠します。本ファイルは、与えられたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-19
最初の公開リリース。以下の主要機能・設計方針を実装しています。

### Added
- パッケージ初期化
  - kabusys パッケージ（__version__ = 0.1.0）。主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring（execution は空の初期モジュールとして存在）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env パーサは export 付き行・クォート・エスケープ・インラインコメント処理をサポート。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能（テスト用途）。
  - 必須環境変数取得用の _require と Settings クラスを提供（J-Quants / kabu / Slack / DB パス等のプロパティを用意）。
  - 環境（development / paper_trading / live）とログレベルのバリデーション、便宜メソッド is_live/is_paper/is_dev を実装。

- データ収集クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（株価日足、財務データ、マーケットカレンダーの取得）。
  - レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）。
  - 401 発生時はトークン自動リフレッシュを試行（1 回のみ）する仕組みを実装。ID トークンのモジュールレベルキャッシュを導入。
  - ページネーション対応の fetch_* 関数と、DuckDB へ冪等保存する save_* 関数（ON CONFLICT DO UPDATE）を実装。
  - データ変換ユーティリティ（_to_float/_to_int）を提供し、不正データや欠損を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集用モジュールを実装。既定のソースに Yahoo Finance を設定。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）により記事 ID を安定化。
  - defusedxml を使った XML 解析、受信サイズ制限、SSRF を防ぐ URL ハンドリング等のセキュリティ考慮。
  - バルク INSERT のチャンク処理と冪等保存を実装。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m/mom_3m/mom_6m、ma200_dev）、Volatility（atr_20/atr_pct、avg_turnover、volume_ratio）、Value（per/roe）の計算関数を実装。
    - DuckDB のウィンドウ関数を用いた効率的な SQL ベース計算、欠損/データ不足時の安全な None 処理。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力バリデーション）。
    - IC（Information Coefficient）計算（Spearman の ρ に相当するランク相関）とランク化ユーティリティ。
    - ファクター統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージは zscore_normalize を含む data.stats からのユーティリティを公開するよう準備。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究環境で算出した生ファクターを統合して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 ≥ 5 億円）を実装。
  - 指定カラムの Z スコア正規化（±3 にクリップ）を適用し、日付単位で冪等に features テーブルを置換（DELETE + INSERT をトランザクションで実行）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を算出するユーティリティを実装。
  - デフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）と閾値（BUY:0.60）を提供。ユーザー重みはバリデーション・リスケールしてマージ。
  - AI レジームスコアに基づく Bear 判定（サンプル数閾値あり）で BUY を抑制。
  - エグジット判定（ストップロス -8% / final_score の閾値割れ）を実装。SELL 権限の優先処理（SELL 対象は BUY から除外）。
  - signals テーブルへ日付単位の置換をトランザクションで行い冪等性を確保。

### Changed
- （初版のため該当なし）コード内に今後の拡張や外部連携ポイント（execution 層や monitoring）を残し、戦略ロジックと発注実装を分離した設計。

### Fixed
- （初版のため該当なし）

### Known limitations / Notes
- 一部のエグジット条件は未実装（コード内注記）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有日数閾値）
- feature_engineering / signal_generator は発注 API（execution 層）へ直接依存しない設計。
- research モジュールはパフォーマンスと再現性のため外部ライブラリ（pandas 等）に依存しない実装を目指している。
- DuckDB スキーマ（raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）はコードから参照されるが、スキーマ作成スクリプトは別途必要。

### Security
- news_collector: defusedxml の使用、受信サイズ制限、トラッキングパラメータ除去、HTTP スキーム検証などの安全対策を実装。
- jquants_client: トークン自動リフレッシュの流れで無限再帰を防ぐため allow_refresh フラグを導入。

---

以上はコードベースの実装内容から推測して作成した CHANGELOG です。必要であれば、実際のコミット履歴やリポジトリの変更単位に合わせて日付やカテゴリの分割・修正を行います。どの粒度で詳細化するか（例えばモジュール単位のサブ項目追加や既知不具合の追記）をご指定ください。
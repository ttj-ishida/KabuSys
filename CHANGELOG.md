# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [Unreleased]

（現在の作業中の変更はここに記載します）

## [0.1.0] - 2026-03-19

初回リリース。

### Added
- パッケージの基本構成を追加
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージを __all__ に公開）。
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - .env 行パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理）。
  - override / protected 機能を持つ .env 読み込みロジック。
  - 必須環境変数取得用の _require と Settings クラスを提供（J-Quants / kabu ステーション / Slack / DB パス / 実行環境 / ログレベル等をラップ）。
  - KABUSYS_ENV の許容値検証（development / paper_trading / live）や LOG_LEVEL 検証を実装。
- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
  - ページネーション対応の fetch_XXX 系メソッド（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx 等を対象）。
  - 401 を受けた場合の自動トークンリフレッシュとリトライ処理（1 回のみ）。
  - JSON デコードエラーやネットワーク障害に対する例外処理強化。
  - DuckDB への保存用関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。いずれも冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存。
  - レスポンス値を安全に変換するユーティリティ _to_float / _to_int を実装。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を抽出・正規化する基盤実装。
  - URL 正規化処理（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリキーソート）。
  - セキュリティ配慮: defusedxml による XML パース（XML Bomb 等対策）、受信サイズ上限（MAX_RESPONSE_BYTES）設定、SSRF を抑制する URL チェック方針（コメントに明記）。
  - 記事 ID を生成して冪等保存する方針（コメントで仕様を明記）。
  - バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）で DB オーバーヘッドを削減。
- 研究・因子計算（kabusys.research）
  - ファクター計算モジュール（factor_research）：
    - モメンタム（mom_1m / mom_3m / mom_6m / ma200_dev）
    - ボラティリティ・流動性（atr_20 / atr_pct / avg_turnover / volume_ratio）
    - バリュー（per / roe、raw_financials から最新財務を取得）
    - DuckDB のウィンドウ関数を活用した SQL ベースの実装。データ不足時には None を返す仕様。
  - 特徴量探索（feature_exploration）：
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）での将来リターンを計算。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンの ρ をランク相関で計算、サンプル不足時は None。
    - 統計サマリー（factor_summary）と rank（同順位は平均ランク、浮動小数誤差対策の丸めあり）。
  - 研究モジュールは pandas 等の外部依存を持たず標準ライブラリと DuckDB のみで実装。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールから得た生ファクターのマージ、ユニバースフィルタ（最低株価・最低平均売買代金）適用、Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 でクリップして features テーブルへ UPSERT（トランザクションで日付単位の置換）する実装。
  - ルックアヘッドバイアス対策として target_date 時点のデータのみを使用する設計。
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し final_score を計算、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換保存する実装。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を算出（シグモイド変換など）。
  - 欠損コンポーネントは中立値 0.5 で補完する方針（欠損銘柄の不当な降格を防止）。
  - 重みのマージと再スケール、無効値スキップ、合計ゼロ時のフォールバック処理を実装（デフォルト重みは StrategyModel.md に準拠）。
  - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数が閾値以上）により BUY を抑制するロジックを実装。
  - エグジット判定（売りシグナル）にストップロス（-8%）とスコア低下（threshold 未満）を実装。トレーリングストップ等は未実装で要追加データ（peak_price / entry_date）。
  - signals テーブルへの原子性を確保するトランザクション＋バルク挿入。
- パッケージ公開インターフェース
  - strategy パッケージは build_features / generate_signals を __all__ で公開。
  - research パッケージで主要な研究関数を公開。

### Changed
- 初回リリースのため該当なし（初出）。

### Fixed
- 初回リリースのため該当なし（初出）。

### Security
- news_collector で defusedxml を使用し XML パース攻撃に対処。
- ニュース収集側で受信サイズ上限（MAX_RESPONSE_BYTES）を設け、メモリ DoS を軽減。
- J-Quants クライアントでトークン管理と 401 リフレッシュを導入し、認証不整合時のハンドリングを強化。
- URL 正規化でトラッキングパラメータを除去し、ID 生成と冪等性の信頼性を向上。

### Known limitations / TODO
- execution パッケージはまだ実装されておらず、発注ロジックとの統合は未完了。
- signal_generator のエグジット条件はトレーリングストップや時間決済を未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- news_collector の記事 ID 生成・DB 保存の詳細実装はコメントで仕様が示されているが、運用テストが必要。
- 一部のコメントに記載の仕様（StrategyModel.md、DataPlatform.md 等）に依存しており、外部ドキュメントとの整合性チェックが必要。
- 大規模データ運用時のパフォーマンス検証・チューニングが必要（DuckDB クエリ計画やバッチサイズ等）。

---

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0 (placeholder)
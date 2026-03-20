# CHANGELOG

すべての注目すべき変更履歴をここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

注: 以下はリポジトリ内のコードから実装内容を推測して記載した変更履歴です。

## [Unreleased]

- なし（次回リリース用の未確定変更をここに記載してください）

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システムのコア機能を含む初期実装を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。モジュール構成: data, research, strategy, execution, monitoring（__all__ を公開）。
  - バージョン番号を `__version__ = "0.1.0"` として定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動読み込み機構を実装（プロジェクトルートの判定に .git / pyproject.toml を使用）。
  - .env/.env.local の読み込み優先度を実装（OS環境変数 > .env.local > .env）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env ファイル行のパーサを実装。`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 必須環境変数取得ヘルパー `_require` を実装（未設定時は ValueError）。
  - 各種設定プロパティを提供:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB / SQLite）/ 環境（development, paper_trading, live）/ ログレベル検証など。
  - 設定オブジェクト `settings = Settings()` を公開。

- データ収集（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - レート制限のための固定間隔スロットリング `_RateLimiter`（120 req/min）。
    - 再試行 (指数バックオフ)、HTTP 429/408/5xx のリトライ、最大試行回数制御。
    - 401 発生時のリフレッシュ処理（id_token の自動リクエストとキャッシュ共有）を実装。
    - ページネーション対応の取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への冪等保存ユーティリティを実装:
    - save_daily_quotes/save_financial_statements/save_market_calendar: ON CONFLICT DO UPDATE による上書きで重複除去。
    - レコードの変換ユーティリティ `_to_float` / `_to_int` を提供（パースの安全性考慮）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプラインを実装（デフォルトに Yahoo Finance の RSS を登録）。
  - セキュリティ考慮:
    - defusedxml を利用して XML 攻撃を軽減。
    - 受信サイズ制限（MAX_RESPONSE_BYTES=10MB）でメモリ DoS を抑制。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ先頭で生成し冪等性を確保。
  - バルク INSERT チャンク化や INSERT RETURNING を意識した設計。

- 研究モジュール（kabusys.research）
  - ファクター計算 / 探索ツールを実装:
    - factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials の SQL ベース実装）。
    - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（統計要約）、rank（同順位は平均ランク）。
  - zscore_normalize を外部参照（kabusys.data.stats よりインポートして再公開）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールから生ファクターを取得し統合して features テーブルへ UPSERT する処理を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
  - Z スコア正規化・±3 クリップ、日付単位の置換（トランザクション）で冪等性を確保。
  - DuckDB を用いた効率的な SQL 取得を実装。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AIスコア）を計算。
  - 重みの入力バリデーションと合計1.0へ再スケールを実装。無効値はログでスキップ。
  - Bear レジーム検知（ai_scores の regime_score の平均が負かつ十分なサンプル数）で BUY を抑制。
  - エグジット条件（ストップロス -8% およびスコア低下）に基づく SELL 生成、保有銘柄の価格欠損時は判定をスキップして警告を出力。
  - signals テーブルへの日付単位置換（トランザクション）で冪等性を保証。

- 内部ユーティリティ
  - 数値処理・欠損処理の方針（None/NaN/Inf 判定）を各モジュールで一貫して適用。
  - 詳細な logger.debug/info/warning を各主要処理に追加し、運用時のトラブルシュート性を向上。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を使用、受信バイト数制限、URL 検証（トラッキングパラメータ除去）等を実装して外部入力の安全性を向上。
- J-Quants クライアントでトークン管理および再試行制御を実装し、機密情報の扱いとエラー耐性を向上。

---

注記:
- 多くの設計/実装はドキュメント（StrategyModel.md、DataPlatform.md 等）に準拠している旨のコメントがコードに含まれており、本 CHANGELOG はそれらコメントとソース実装から主要な追加・仕様を推測して作成しています。
- 将来のリリースではテストカバレッジ、performance チューニング、追加の発注（execution）実装、監視（monitoring）機能の詳細実装が追記される想定です。
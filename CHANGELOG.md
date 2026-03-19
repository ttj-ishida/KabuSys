# Changelog

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
このファイルは後からの変更追跡とリリースノート作成を目的としています。

全般的な慣例:
- 変更はセマンティックバージョニングに従います。
- 各リリースは「Added / Changed / Fixed / Security / Deprecated / Removed」のカテゴリで整理します。

## [Unreleased]
- （未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買システム「KabuSys」の基礎となる機能群を実装しました。主要コンポーネント、設計方針、重要な実装上の配慮（冪等性・ルックアヘッド対策・セキュリティ制御・DBトランザクション等）を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化とエクスポートを追加（data, strategy, execution, monitoring）。
  - バージョン情報: `__version__ = "0.1.0"`。

- 設定管理
  - 環境変数・設定管理モジュールを追加（kabusys.config）。
  - プロジェクトルート自動検出: `.git` または `pyproject.toml` を基準にルートを探索（CWD依存しない）。
  - .env 自動読み込み機能:
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 環境変数保護（既存 OS 環境変数は保護可能）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - Settings クラス: 必須変数取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）、パス設定（duckdb/sqlite パス）、環境（development/paper_trading/live）・ログレベル検証ユーティリティ。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを追加（kabusys.data.jquants_client）。
  - 機能:
    - API 呼び出し（/prices/daily_quotes, /fins/statements, /markets/trading_calendar）とページネーション対応。
    - 固定間隔レート制限（120 req/min）を実装する RateLimiter。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時は自動トークンリフレッシュを行い1回リトライ（無限再帰防止フラグ）。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
  - DuckDB への保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar：いずれも冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存。
    - fetched_at（UTC）を記録して Look-ahead バイアスのトレースを可能に。
    - PK 欠損行のスキップとログ警告。

- ニュース収集
  - RSS 収集モジュールを追加（kabusys.data.news_collector）。
  - 機能と対策:
    - RSS 解析（defusedxml）による安全なXMLパース。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - 記事 ID を正規化済URLの SHA-256（先頭32文字）で生成し冪等性を担保。
    - HTTP/HTTPS 以外のスキーム拒否や受信サイズ制限（MAX_RESPONSE_BYTES=10MB）による SSRF / DoS 対策。
    - バルク INSERT のチャンク処理とトランザクションまとめで性能最適化。
    - INSERT RETURNING として実際に挿入された件数を正確に扱う設計（実装方針として明記）。

- リサーチ（研究）機能
  - ファクター計算モジュール（kabusys.research.factor_research）:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials から算出。
    - 欠損・データ不足時の None 処理、営業日ベースのウィンドウ・スキャン範囲バッファ。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman の ρ）計算、ランク化ユーティリティ（同順位の平均ランクを採用、丸めによる ties 対策）。
    - 基本統計量サマリー（count/mean/std/min/max/median）。
  - 研究向けユーティリティを __all__ でエクスポート。

- 戦略（Strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）:
    - research モジュールの生ファクターを統合・正規化し features テーブルへUPSERT（冪等）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）。
    - Z スコア正規化（zscore_normalize を使用）、±3 でクリップ。
    - トランザクション＋バルク挿入による日付単位の置換で原子性保証。
  - シグナル生成（kabusys.strategy.signal_generator）:
    - features と ai_scores を統合し各コンポーネントスコア（momentum/value/volatility/liquidity/news）から final_score を計算。
    - デフォルト重みと閾値（デフォルト threshold=0.60）を実装。重みの入力検証と再スケーリング処理を実装。
    - Bear レジーム判定（AI の regime_score 平均が負かつ十分なサンプル数）による BUY 抑制。
    - エグジット判定（ストップロス -8% / スコア低下）で SELL シグナル生成。SELL 優先ポリシー。
    - signals テーブルへの日付単位置換（トランザクションで原子性保証）。
    - 欠損値のコンポーネントは中立値（0.5）で補完するロバストなスコア計算。

- 汎用ユーティリティ
  - HTTP/JSON ラッパー（_request）における詳細なエラーハンドリング（429 の Retry-After 優先、JSON デコード例外の明示的エラー等）。
  - 型安全な変換ヘルパー: _to_float / _to_int。
  - RateLimiter 実装とモジュール内キャッシュ（ID トークン共有）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- ニュース収集で defusedxml を使用して XML ベースの攻撃を軽減。
- ニュース URL 正規化でトラッキングパラメータ除去、HTTP/HTTPS スキーム制限、受信バイト上限などを実装して SSRF/DoS のリスクを低減。
- J-Quants クライアントのトークン自動更新は allow_refresh フラグで再帰を防止。

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

---

注記:
- 多くの DB 操作は DuckDB 接続を前提としており、関数は接続と基準日（target_date）を受け取る純粋な処理になっています（発注 API 等の外部副作用を持たない設計）。
- ルックアヘッドバイアスを防ぐ工夫（fetched_at の記録、target_date 時点のデータのみ参照する方針など）が各所で注記されています。
- 将来的なリリースでは監視/実行層（execution、monitoring）や Slack 通知連携などの拡張が見込まれます。

（この CHANGELOG は現行のコードベースから推測して作成しています。実際のコミット履歴・リリース計画に応じて適宜更新してください。）
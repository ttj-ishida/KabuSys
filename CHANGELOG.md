# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、Semantic Versioning を採用します。

## [Unreleased]

## [0.1.0] - 2026-03-21

初回公開リリース。日本株自動売買システムのコア機能群（データ取得・加工・研究・戦略生成）を実装しました。主な追加点と設計上の注意点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__version__ = 0.1.0, __all__ を定義）。
- 設定管理（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数から設定を安全に読み込む自動ロード機能を実装。
  - 読み込み順序: OS 環境変数 > .env.local（上書き）> .env（未設定時のみセット）。
  - .env パーサは export KEY=val 形式、クォート・エスケープ、インラインコメントの取り扱いに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - Settings クラスを提供し、必須環境変数取得（_require）、env / log_level の検証、パス（duckdb/sqlite）の展開ユーティリティを実装。
- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。機能:
    - レート制限遵守（固定間隔スロットリングで 120 req/min 相当）。
    - 自動リトライ（指数バックオフ、最大 3 回、408/429/5xx に対応）。
    - 401 の場合はリフレッシュトークンで ID トークンを自動更新して 1 回リトライ。
    - ページネーション対応（pagination_key を追跡して重複を防止）。
    - fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、冪等な保存（ON CONFLICT DO UPDATE / DO NOTHING）を行う。
    - fetched_at を UTC ISO8601 で記録（Look-ahead バイアスのトレース用）。
  - 型変換ユーティリティ (_to_float, _to_int) を追加。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する基盤を実装。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除など）、記事 ID を正規化 URL の SHA-256 で生成する方針を導入し、冪等性を確保。
  - defusedxml を用いた安全な XML パース、受信サイズ上限（10MB）設定、挿入時のバルクチャンク処理などを実装。
  - デフォルトソースとして Yahoo Finance のカテゴリ RSS を定義。
- 研究 / ファクター計算（kabusys.research）
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。ウィンドウ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS=0 などは None）。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21）で将来リターンを計算（営業日ベース）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算するユーティリティ。
    - rank, factor_summary（count/mean/std/min/max/median）を実装。
  - これらは DuckDB の prices_daily / raw_financials のみを参照し、本番 API にはアクセスしない設計。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research モジュールから生ファクターを取得しマージ、株価・流動性によるユニバースフィルタを適用（最低株価 300 円、20日平均売買代金 5 億円）。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクション内で実行し原子性を保証）。
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算、重み付き合算で final_score を算出（デフォルト重みを採用、ユーザ指定重みは検証・正規化）。
    - シグモイド変換・欠損補完（コンポーネント None は中立値 0.5）で堅牢性を確保。
    - AI レジーム（ai_scores.regime_score）の平均が負であれば Bear レジームと判定し BUY を抑制（サンプル不足時は Bear とみなさない）。
    - 保有ポジションに対する SELL 判定を実装（ストップロス -8% 優先、スコア低下によるエグジット）。
    - signals テーブルへ日付単位で置換（トランザクション内で DELETE + INSERT）。
- ロギング、エラーハンドリング
  - 各処理で適切なログ（info/warning/debug）を出力し、トランザクション失敗時は ROLLBACK を試行。

### Changed
- （初版のため該当なし）初期実装に集中。

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- ニュース収集で defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）への対策を導入。
- ニュース URL の正規化でトラッキングパラメータを除去し、ID 生成の冪等性を強化。
- J-Quants クライアントでトークン管理・自動リフレッシュを実装（401 による不要な失敗を軽減）。
- ネットワークエラー・HTTP エラー時のリトライ制御と RateLimiter により外部 API への過負荷を抑制。

### Known limitations / Notes
- 信号生成の一部エグジット条件は未実装（コメントで TODO を記載）:
  - トレーリングストップ（peak_price / entry_date が positions に必要）や時間決済（60 営業日超過）などは未実装。
- news_collector の SSRF / IP バリデーションや全 URL 検査の詳細実装はモジュール内で考慮されているが、完全なルールセットは今後の拡張対象。
- 外部依存を抑える目的で研究モジュールは pandas 等の追加ライブラリに依存しない実装だが、大規模データではパフォーマンス検証が必要。
- DuckDB スキーマ（tables）の作成は本リリースに含まれていないため、初回実行前に適切なスキーマ定義が必要です（README 参照想定）。

---

今後の予定（例）
- トレーリングストップや時間決済等のエグジットロジック強化。
- news_collector のより厳格な URL/SSRF 防御、ソース拡張。
- モニタリング / 実行レイヤ（execution, monitoring パッケージ）の実装と Slack 等への通知連携強化。
- テストカバレッジの拡充と CI パイプライン整備。

署名: kabusys 開発チーム
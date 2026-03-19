# CHANGELOG

すべての注目すべき変更はここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。以下の主要機能・実装が含まれています。

### Added
- パッケージ初期化
  - kabusys パッケージ（__version__ = 0.1.0）と主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、パッケージ設置後も CWD に依存せず動作するように実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト向け）。
  - .env パーサーがシングル/ダブルクォート、export プレフィックス、行末コメント、バックスラッシュエスケープに対応。
  - OS 環境変数を保護する protected オプション（上書き禁止）を実装。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック（未設定時に ValueError を投げる）。
    - KABUSYS_ENV（development / paper_trading / live）のバリデーション。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）の Path 変換ユーティリティ。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - API レート制限 (120 req/min) を満たす固定間隔スロットリング（_RateLimiter）を導入。
    - リトライロジック（指数バックオフ、最大3回）。HTTP 408/429 と 5xx をリトライ対象とする。
    - 401 受信時にはリフレッシュトークンで自動的に ID トークンを再取得して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存（save_daily_quotes, save_financial_statements, save_market_calendar）は ON CONFLICT で重複更新。
    - データ変換ユーティリティ (_to_float / _to_int) により不正な値を安全に処理。
    - fetched_at を UTC ISO 形式で保存し、データ収集時点のトレースを可能にする（Look-ahead Bias 対策の一部）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集・正規化するモジュールを追加（デフォルトソースに Yahoo Finance を設定）。
  - 記事 URL の正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリのソート、フラグメント削除）。
  - defusedxml を使って XML による攻撃（XML Bomb 等）を防御。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定してメモリ DoS を軽減。
  - DB バルク挿入用のチャンクサイズ設定（_INSERT_CHUNK_SIZE）を導入。
  - 設計として記事IDを正規化 URL の SHA-256（短縮）で作る方針や SSRF 回避の考慮が明記されている。

- リサーチ/ファクター計算（kabusys.research）
  - factor_research モジュール:
    - モメンタム（1M/3M/6M リターン、MA200 乖離率）、ボラティリティ（20日 ATR、相対 ATR、平均売買代金・出来高比率）、バリュー（PER、ROE）の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用した営業日ベースのリターン・移動平均・ATR 等の計算。
    - データ不足時の None 処理（ウィンドウ内データ不足で None を返す挙動）。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns）: LEAD を用いて指定ホライズン後の終値を取得しリターンを計算。horizons の検証（正の整数かつ <= 252) を実施。
    - IC（Information Coefficient）計算（calc_ic）: factor と将来リターンを code で結合し Spearman の ρ を計算（ties の平均ランク対応、3 サンプル未満は None を返す）。
    - ランク生成ユーティリティ（rank）とファクター統計サマリ（factor_summary）を提供。factor_summary は count/mean/std/min/max/median を返す。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research 側で算出した raw ファクターを合成して features テーブルへ保存する build_features を実装。
    - 処理フロー: momentum/volatility/value を取得 → ユニバースフィルタ（最低株価/平均売買代金）適用 → Z スコア正規化 → ±3 クリップ → features テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - ユニバースフィルタは _MIN_PRICE=300 円、_MIN_TURNOVER=5e8（5 億円）を採用。
    - 欠損や非有限値の扱いについて明確に実装。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を組み合わせて final_score を計算し BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI）。
    - スコア変換にシグモイド関数を使用し、欠損成分は中立値 0.5 で補完。
    - 重みのマージ・検証と再スケーリング。ユーザー提供の weights の検証（非数値、負値、NaN/Inf の除外）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合）により BUY シグナルを抑制。
    - エグジット条件（ストップロス -8% / スコア低下）に基づく SELL 生成。価格欠損時は SELL 判定をスキップして誤クローズを回避。
    - SELL 優先ポリシー（SELL 銘柄は BUY から除外しランクを再付与）。
    - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。

### Changed
- （設計の明文化）各モジュールはルックアヘッドバイアスを防ぐため target_date 時点のデータのみを利用する方針を明記・実装。
- DuckDB を中心としたデータフロー設計に統一（prices_daily / raw_prices / raw_financials / features / ai_scores / signals / positions などのテーブルを前提）。

### Fixed
- .env パーシングの堅牢化:
  - export プレフィックス、クォート文字列内のバックスラッシュエスケープ対応、インラインコメントの扱いなどを実装して誤解釈を低減。

### Security
- news_collector で defusedxml を利用して XML の脆弱性を緩和。
- news_collector と jquants_client のネットワーク周りで入力検証・受信サイズ制限・SSRF 回避方針を明示。

### Notes / Known limitations
- 一部機能は今後の改善余地が明記されています:
  - signal_generator のトレーリングストップ・時間決済は positions テーブルに peak_price / entry_date 等が揃った段階での実装を想定（コメントで未実装と明記）。
  - news_collector の記事 ID 生成・news_symbols 連携は方針・ユーティリティが記載されているが、完全な紐付けロジックは追加作業が必要な場合がある。
  - 一部ドキュメントや SQL の最適化（大量データ時のパフォーマンスチューニング）は今後の改善対象。

---

この CHANGELOG は、ソースコード内の docstring・実装・ログ出力・定数・関数名などから推測して作成しています。実際のリリースノート作成時はリリースポリシーに従い内容を調整してください。
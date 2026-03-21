# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはリポジトリの現行コードベース（バージョン 0.1.0）から推測して作成しています。

## [Unreleased]
- 特になし（初回リリースは 0.1.0）

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。以下はコードベースから推測される主要な追加点と挙動です。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__version__ = "0.1.0"、__all__ 定義）。
  - strategy、execution、data、monitoring 等のモジュール構成を定義（空の execution パッケージ含む）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動的に読み込む仕組みを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - 高度な .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等）。
  - 自動読み込みの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを提供し、アプリで必要な設定アクセスをプロパティとして公開：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス、Path型で返却）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live / is_paper / is_dev プロパティ

- データ収集・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（価格・財務・マーケットカレンダーの fetch/save）。
  - レート制限制御（固定間隔スロットリング、120 req/min を実装）。
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を再試行）。
  - 401 発生時にリフレッシュトークンから ID トークンを再取得して 1 回リトライする自動トークンリフレッシュ。
  - ページネーション対応（pagination_key）。
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE を利用）:
    - raw_prices（save_daily_quotes）
    - raw_financials（save_financial_statements）
    - market_calendar（save_market_calendar）
  - データ変換ユーティリティ（_to_float / _to_int）を提供（不正値は None）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する仕組み（既定ソースに Yahoo Finance を含む）。
  - URL 正規化（トラッキングパラメータの除去、スキーム/ホストの小文字化、クエリソート、フラグメント削除）を実装。
  - セキュリティ対策: defusedxml を用いた XML パース、受信サイズ上限（10 MB）、SSRF 対策（HTTP/HTTPS のみ受け入れ）、トラッキングパラメータ除去、記事ID に SHA-256 ハッシュを使用した冪等性。
  - バルク挿入のチャンク処理とトランザクションまとめ。

- 研究用モジュール（kabusys.research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
  - ファクター探索ユーティリティ:
    - calc_forward_returns（複数ホライズン対応、最大 252 営業日のバリデーション）
    - calc_ic（Spearman ランク相関による IC 計算、最小サンプル判定）
    - factor_summary（count/mean/std/min/max/median）
    - rank（同順位は平均ランクに変換、丸め処理による ties 対処）
  - zscore_normalize は kabusys.data.stats から利用する前提で参照。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research のファクター計算結果をマージ
    - 株価・流動性によるユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）
    - 指定カラムの Z スコア正規化、±3 でクリップ
    - features テーブルへ日付単位で置換（トランザクションにより原子性を保証）
    - 冪等動作（既存 date を削除して挿入）

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features, ai_scores, positions, prices_daily を参照して BUY/SELL シグナルを生成
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算と重み付け（デフォルト重みを実装）
    - Sigmoid・Z スコア→[0,1] マッピング、欠損コンポーネントは中立 0.5 で補完
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）
    - BUY は閾値超過、Bear 時は BUY 抑制
    - SELL 条件にストップロス（-8%）とスコア低下（threshold 未満）を実装
    - SELL 優先ポリシー（SELL 対象を BUY から除外）
    - signals テーブルへ日付単位の置換（トランザクションで原子性確保）
    - weights 入力のバリデーションとリスケール処理を実装（未知キー・非数値は無視）

### Security
- news_collector で defusedxml を使用し XML 攻撃への耐性を強化。
- news_collector は受信サイズ制限、URL 正規化、HTTP/HTTPS スキーム制限等を実装して SSRF や DoS のリスクを低減。
- jquants_client は API レート制御とリトライ・トークンリフレッシュを実装し、過負荷や認証切れに対処。

### Notes / Usage & Migration
- 必須環境変数（最低限セットが必要）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に .env / .env.local を読み込みます。
  - OS 環境変数は保護され、.env による上書きはデフォルトで発生しません。.env.local は override=True（ただし既存 OS 環境変数は保護）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- DuckDB を利用するため、prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar 等のテーブルスキーマが前提になります（コードはそれらテーブルへの SQL を直接実行します）。
- research モジュールは外部依存（pandas 等）を持たず純粋に SQL + 標準ライブラリで実装されているため、軽量に動作します。

### Known limitations / 未実装（コードに明示されている事項）
- signal_generator のエグジット条件でいくつかのルールは未実装（トレーリングストップ、時間決済等は positions テーブルの拡張が必要）。
- 一部の統計処理・正規化ロジックは kabusys.data.stats など他モジュールに依存しているため、それらの実装が必要。
- news_collector の詳細な RSS パーシング・記事→銘柄の紐付けロジックは概説されているが、完全な実装の有無はコードスニペットの範囲では不明（ただし URL 正規化等の基盤は実装済み）。

### Breaking Changes
- なし（初回リリース）。

---

貢献やバグ報告、ドキュメント改善の提案は Issue または Pull Request で受け付けてください。
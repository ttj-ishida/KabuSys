# Changelog

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」（慣例）に準拠しています。  
リリースはセマンティックバージョニングに従います。

全般的な注意:
- この CHANGELOG はソースコードの内容から推測して作成しています。実装の詳細や将来の変更により実際と異なる可能性があります。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回公開リリース。

### 追加 (Added)
- パッケージ基盤を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定/ロード
  - 開発用の Settings クラスを追加（kabusys.config）。
  - .env ファイル自動読み込み機能を実装:
    - プロジェクトルートは __file__ の親ディレクトリから `.git` または `pyproject.toml` を探索して特定（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` に対応。
  - .env パーサを実装:
    - export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応。
  - 必須設定の取得ヘルパー `_require` を提供（未設定時は ValueError）。
  - Settings で主要な設定項目をプロパティ化:
    - J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル 等。
    - env/log_level の検証（許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを追加（kabusys.data.jquants_client）。
    - レート制限管理（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）を実装（408/429/5xx を再試行対象）。
    - 401 発生時はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ。
    - ページネーション対応の fetch_ 関数を提供:
      - fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar。
    - DuckDB への冪等保存関数を提供（ON CONFLICT DO UPDATE を利用）:
      - save_daily_quotes（raw_prices）、save_financial_statements（raw_financials）、save_market_calendar（market_calendar）。
    - 値変換ユーティリティ `_to_float`, `_to_int` を提供（堅牢な変換ロジック）。

- ニュース収集（RSS）
  - RSS ベースのニュース収集モジュールを追加（kabusys.data.news_collector）。
    - RSS 取得（fetch_rss）: defusedxml を用いた安全な XML パース、gzip 対応、受信サイズ上限（10MB）チェック、Content-Length の事前チェック、XML パース失敗時のフォールバック/警告。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクトごとにスキームとホストを検査するカスタムリダイレクトハンドラ。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定してアクセス拒否。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）関数を提供。
    - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成（冪等性）。
    - テキスト前処理（URL 除去・空白正規化）のユーティリティを提供。
    - DB への保存関数（DuckDB）:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いて実際に挿入された記事 ID を返す。チャンク挿入と単一トランザクションによる最適化。
      - save_news_symbols / _save_news_symbols_bulk: ニュースと銘柄コードの紐付けをチャンクで挿入（ON CONFLICT を利用）し、挿入件数を正確に返す。
    - 銘柄コード抽出: 4 桁数字パターンから既知銘柄セットに含まれるものを抽出するユーティリティ（重複除去）。

- DuckDB スキーマ定義（初期）
  - kabusys.data.schema にてデータベーススキーマ（Raw Layer 等）の DDL を追加:
    - raw_prices, raw_financials, raw_news, raw_executions 等の作成文を定義（CHECK 制約・PRIMARY KEY 等を含む）。
    - 初期化／DDL 管理の基盤を想定。

- リサーチ / ファクター計算
  - kabusys.research パッケージを追加。
  - factor_research:
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 乖離率を prices_daily から計算（行ウィンドウを用いた集計）。
    - ボラティリティ (calc_volatility): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（true_range の NULL 伝播を考慮）。
    - バリュー (calc_value): raw_financials の最新財務データと prices_daily を組み合わせて PER（EPS が 0/欠損なら None）と ROE を計算。
    - 設計上、本番発注 API に一切アクセスせず、prices_daily / raw_financials のみ参照。
  - feature_exploration:
    - 将来リターン calc_forward_returns（複数ホライズンを同時取得、horizons のバリデーションあり）。
    - Information Coefficient（calc_ic）: Spearman ランク相関を実装（ties を平均ランクで処理）。3 レコード未満では計算不能のため None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで計算。
    - rank: 同順位の平均ランク計算（丸めて ties 検出漏れを防止）。
  - research パッケージ __init__ で主要ユーティリティを公開:
    - calc_momentum, calc_volatility, calc_value, zscore_normalize（kabusys.data.stats から）, calc_forward_returns, calc_ic, factor_summary, rank

- パッケージ公開 API
  - top-level __init__ に __version__ = "0.1.0" と __all__ を設定（data, strategy, execution, monitoring を想定したエクスポート）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- RSS/HTTP 関連で複数の防御を実装:
  - defusedxml による XML 攻撃対策。
  - SSRF 対策（スキーム検証・プライベートホストチェック・リダイレクト検査）。
  - レスポンスサイズ上限と gzip 解凍後のサイズ検査で DoS を緩和。

### 既知の制限 / 注意点 (Known limitations & notes)
- research モジュールは外部ライブラリ（pandas 等）を使わない方針。大量データ処理ではパフォーマンス面のチューニングが必要になる可能性あり。
- J-Quants クライアントは urllib ベースで実装されているため、細かな HTTP 制御（セッション/Keep-Alive 等）の最適化は今後の改善点。
- schema.py は DDL を定義しているが、マイグレーション管理やバージョニング機構は未実装。
- strategy / execution / monitoring パッケージは名前空間を用意（__init__.py が存在）しているが、実装はこれから想定される（現状空または未完成）。
- news_collector の既定 RSS ソースは最小構成（yahoo_finance）。実運用ではソース追加・運用監視が必要。

---

（以上）
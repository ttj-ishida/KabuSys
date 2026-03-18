# CHANGELOG

すべての重要な変更点をここに記載します。  
このプロジェクトは Keep a Changelog の指針に従っています。  

## [0.1.0] - 2026-03-18

初期公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下は主な追加内容と設計上の注意点です。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `0.1.0` に設定。
  - __all__ により外部公開 API を整理（data, strategy, execution, monitoring）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数からの設定読み込みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を検索）。
  - .env のパースロジックを実装（export プレフィックス、クォート・エスケープ、インラインコメント対応）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用）。
  - 環境変数検査ユーティリティ `_require` と Settings クラスを追加（J-Quants / kabu / Slack / DB パス / env / log level 等のプロパティ）。

- データ収集・永続化 (src/kabusys/data/)
  - J-Quants API クライアント (jquants_client.py)
    - レート制限（120 req/min）を守る固定間隔 RateLimiter 実装。
    - HTTP リクエスト共通処理とリトライ（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
    - 401 受信時にリフレッシュトークンで自動的に ID トークンを再取得して 1 回再試行。
    - ページネーション対応の fetch_*** 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_*** 関数（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - 型変換ユーティリティ `_to_float` / `_to_int`。

  - ニュース収集 (news_collector.py)
    - RSS フィード取得と記事解析（defusedxml で XML 攻撃対策）。
    - URL 正規化（トラッキングパラメータ除去、ソート、スキーム小文字化）、記事 ID は正規化 URL の SHA-256 の先頭 32 文字。
    - SSRF 対策：スキーム検証、ホストのプライベートアドレス判定、リダイレクト時の検査。
    - レスポンスサイズ上限（10MB）・gzip 解凍チェック（Gzip bomb 対策）。
    - テキスト前処理（URL 除去・空白正規化）。
    - DuckDB への冪等保存（save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id、チャンク挿入、トランザクション管理）。
    - 記事と銘柄コード紐付け（extract_stock_codes / save_news_symbols / _save_news_symbols_bulk）。
    - デフォルト RSS ソース設定（Yahoo Finance のビジネス RSS を含む）。

  - DuckDB スキーマ定義 (schema.py)
    - Raw Layer テーブル DDL（raw_prices, raw_financials, raw_news, raw_executions 等）を定義。
    - DataSchema に基づくレイヤ分離（Raw / Processed / Feature / Execution）を想定。

- リサーチ（特徴量・ファクター） (src/kabusys/research/)
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（DuckDB の prices_daily を参照、複数ホライズン対応）。
    - スピアマンランク相関（IC）計算 calc_ic（rank 関数を内部実装）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - 外部ライブラリに依存せず、標準ライブラリと DuckDB のみで実装。
  - factor_research.py
    - momentum, value, volatility（calc_momentum / calc_value / calc_volatility）を実装。
    - 各ファクターは prices_daily および raw_financials を参照し、(date, code) ベースの dict リストを返す。
  - research パッケージ __init__.py で主要ユーティリティをエクスポート（calc_momentum 等と zscore_normalize の re-export）。

### 変更 (Changed)
- なし（初期リリース）。

### 直した/仕様の明確化 (Fixed / Notes)
- .env のパースや .env.local の優先順位、OS 環境変数保護の仕様を明確に実装。
- jquants_client のリトライ/リフレッシュ挙動を明確化（401 は1回リフレッシュ、それ以外は最大リトライ回数まで指数バックオフ）。
- news_collector の RSS 処理は XML パース失敗やレスポンスサイズ超過時に安全に失敗して空リストを返すように改善。

### セキュリティ (Security)
- XML パースに defusedxml を利用し XML 関連攻撃を軽減。
- RSS フィード取得時に SSRF を防ぐため、スキーム検証・リダイレクト検査・プライベートIP検査を導入。
- 外部 API トークンは環境変数経由で管理。トークンリフレッシュの際にキャッシュを用いるが、必要時に強制更新も可能。

### 既知の制約・注意点 (Known issues / Notes)
- 外部依存を抑える設計上、リサーチ周りは pandas/numpy を使わず純 Python 実装になっており、大規模データでの性能面では最適化余地がある。
- DuckDB スキーマはファイル中に定義されているが、自動でテーブルを作成する初期化関数は未公開（必要に応じて schema モジュールを拡張してください）。
- _to_int の挙動: "1.9" のような小数文字列は None を返す（意図しない切り捨て防止）。
- calc_forward_returns / calc_momentum などは営業日ベース（連続レコード数）を前提としており、カレンダー日数との扱いに注意。
- J-Quants API の rate limit および retry に関しては現行ロジックで一般的なケースに対応しているが、実運用での追加監視やメトリクス収集を推奨。

### マイグレーション / 使用上のメモ (Migration / Usage)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - KABUSYS_ENV は development/paper_trading/live のいずれか（省略時は development）
- .env 自動読み込みはプロジェクトルートの検出に基づく。配布パッケージやテスト環境で自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の保存関数は ON CONFLICT を利用して冪等性を担保します。既存データの上書きを制御する場合は save_* 関数の呼び出し方法に注意してください。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの具体的実装（発注ロジック、約定処理、監視ダッシュボード）。
- パフォーマンス最適化（大量データに対する DuckDB クエリ最適化、並列化）。
- テストカバレッジの拡充および CI ワークフローの追加。
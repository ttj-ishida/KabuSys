# CHANGELOG

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。  
リリースはセマンティックバージョニングに従います。

なお、本CHANGELOGは提供されたコードベースから実装内容を推測して作成しています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-19
初回公開リリース。

### 追加 (Added)
- パッケージ初期構成
  - kabusys パッケージのベース（__version__ = 0.1.0、パッケージ公開用 __all__ 定義）。
  - 空のサブパッケージプレースホルダ: kabusys.execution, kabusys.strategy。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの検出を .git または pyproject.toml を基準に行い、作業ディレクトリに依存しない自動ロードを提供。
  - .env / .env.local の読み込み順序（OS環境変数 > .env.local > .env）と override/protected 機能を実装。
  - .env パーサーはコメント行、export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリ内から型安全に設定値へアクセスできるインターフェースを追加。
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）。
    - 既定値を持つ設定: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）、DUCKDB_PATH, SQLITE_PATH。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証ロジックを実装。
    - is_live/is_paper/is_dev のヘルパープロパティを追加。

- データ収集・保存（kabusys.data）
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - レート制御（_RateLimiter）実装: 120 req/min を固定間隔スロットリングで遵守。
    - リトライロジック（指数バックオフ、最大3回）実装。再試行対象ステータスを指定（408, 429, 5xx）。
    - 401 Unauthorized 受信時の自動トークンリフレッシュをサポート（1回のみリフレッシュして再試行）。
    - ID トークンのモジュールレベルキャッシュを実装し、ページネーション等でトークンを共有。
    - ページネーション対応のデータ取得関数を提供:
      - fetch_daily_quotes: 日足（OHLCV）をページング取得。
      - fetch_financial_statements: 財務データ（四半期）をページング取得。
      - fetch_market_calendar: JPX マーケットカレンダー取得。
    - DuckDB へ冪等保存する関数:
      - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE で重複を排除）。
    - 汎用変換ユーティリティ: _to_float / _to_int（妥当性と安全な変換を考慮）。

  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィードから記事を取得して raw_news に保存する機能を実装。
    - セキュリティ対策:
      - defusedxml を使った XML パース（XML bomb 対策）。
      - SSRF 対策（URL スキーム検証、ホストのプライベート IP 検査、リダイレクト時の検証を行うカスタムリダイレクトハンドラ）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）の導入と gzip 解凍後の検査。
      - 許可されない URL スキームの排除（http/https のみ許可）。
    - URL 正規化（tracking パラメータ除去、クエリソート、フラグメント除去）と記事 ID（SHA-256 の先頭32文字）生成により冪等性を担保。
    - テキスト前処理（URL 除去・空白正規化）ユーティリティ。
    - extract_stock_codes: テキストから 4 桁の銘柄コードを抽出（known_codes によるフィルタ）。
    - DB 保存関数:
      - save_raw_news: INSERT ... RETURNING を用いたチャンク挿入で新規記事 ID を返す（トランザクション管理、チャンクサイズ制限）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括保存（重複排除、ON CONFLICT DO NOTHING、RETURNING で実際の挿入数を取得）。
    - run_news_collection: 複数 RSS ソースを回して収集・保存・銘柄紐付けまで実行する統合ジョブを追加。

- リサーチ（kabusys.research）
  - research パッケージの公開 API を整備（__all__ に主要関数を追加）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily を使って一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足や定数分散を考慮して None を返す挙動。
    - rank: 同順位は平均ランクを割り当てるランク関数（丸めにより ties の検出漏れを防止）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する集計ユーティリティ。
    - 設計上、pandas 等の外部ライブラリに依存せず標準ライブラリのみで実装。

  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。必要行数不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials から最新の財務データを取得して per（株価/EPS）と roe を計算。EPS=0/欠損時は per を None とする。
    - 各関数とも DuckDB の prices_daily/raw_financials を参照し、本番 API へのアクセスを行わない設計。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB のテーブル定義（Raw Layer の DDL）を実装:
    - raw_prices, raw_financials, raw_news, raw_executions（ソースコードでは raw_executions の定義が途中まで含まれる）。
  - DataLayer 設計に合わせた3層構造（Raw / Processed / Feature / Execution）に言及。

### セキュリティ (Security)
- RSS パーサで defusedxml を採用し、XML による攻撃ベクトルを軽減。
- RSS/HTTP の SSRF 対策を実装:
  - リダイレクト時にスキーム/ホストの事前検証を行う専用ハンドラ。
  - ホスト解決時に A/AAAA レコードを調べ、プライベート・ループバック・リンクローカルを拒否。
  - 許可スキームは http/https のみ。
- J-Quants クライアントはトークン自動リフレッシュおよびレート制限、リトライを実装してサービス保護とリクエスト信頼性を向上。

### パフォーマンス (Performance)
- calc_forward_returns / factor 計算では、必要範囲を限定して単一 SQL クエリで複数ホライズンを取得（パフォーマンス改善）。
- news_collector の DB 挿入はチャンク・トランザクションでまとめて実行しオーバーヘッドを削減。
- J-Quants API 呼び出しは固定間隔スロットリングでレートを厳守。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 既知の制限 / 注意点 (Notes)
- research モジュールは外部依存を避けるため pandas 等を使っていないため、大規模データでの扱いは最適化の余地がある。
- DuckDB スキーマ定義の一部（Execution Layer など）はソース提供分で途中までのため、完全なテーブル定義はソース全体を参照して確認してください。
- 環境変数の必須項目が未設定だと起動時に ValueError が発生します。必要な環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- J-Quants API のレート制限・リトライ挙動は実運用環境の制約により調整が必要な場合があります。
- news_collector のホスト名検査は DNS 解決に依存します。解決失敗時は「安全側」に見なし通過させる実装になっています（設計上のトレードオフ）。

### 開発（今後の改善候補）
- research モジュールに pandas / numpy を依存可能な実装とするオプション（高速化、可読性向上）。
- schema モジュールで Processed / Feature / Execution レイヤの完全な DDL を追加。
- テストスイート（ユニット/統合）と CI 設定の追加（環境変数やネットワーク依存部分のモックを含む）。
- ニュース記事の日本語形態素解析による銘柄抽出精度向上や、シグナル生成フローの追加。

---

このCHANGELOGはコードベースの内容をもとに推測して作成しています。実際のリリースノートに反映する際は、追加の変更やリリース日・メタ情報を適宜更新してください。
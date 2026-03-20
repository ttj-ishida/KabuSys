Keep a Changelog に準拠した CHANGELOG.md（日本語）を作成しました。リポジトリのコード内容から推測して記載しています。必要があれば追記・修正します。

# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティック バージョニングに従います。

## [Unreleased]

- （現時点では未リリースの変更なし）

## [0.1.0] - 2026-03-20

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンは 0.1.0。
  - モジュールの公開 API を定義（strategy, execution, data, monitoring を意図）。

- 環境設定 / ロード (src/kabusys/config.py)
  - .env と .env.local をプロジェクトルートから自動読み込み（OS 環境変数が優先、.env.local は上書き可能）。
  - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .git または pyproject.toml を基準にプロジェクトルートを検出するロジックを実装（CWD 依存回避）。
  - .env パーサを独自実装（export 形式、シングル/ダブルクォート、エスケープ、行内コメント処理に対応）。
  - Settings クラスを追加し、必須環境変数の検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）や既定値（KABU_API_BASE_URL、データベースパス、LOG_LEVEL、KABUSYS_ENV）を提供。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値列挙）を実装。is_live / is_paper / is_dev のユーティリティプロパティを追加。

- データ収集 / 保存機能 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。日足（OHLCV）、財務データ、マーケットカレンダーをページネーション対応で取得。
  - レート制限制御（固定間隔スロットリング, 120 req/min）を実装（内部 RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回）を導入。HTTP 408/429/5xx に対するリトライ、429 の Retry-After を尊重。
  - 401 受信時に自動でリフレッシュトークンを使って ID トークンを取得して 1 回再試行する仕組みを実装。
  - データ保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）: DuckDB に対して冪等的に保存（ON CONFLICT DO UPDATE）し、fetched_at を UTC で格納。
  - 型変換ユーティリティ(_to_float, _to_int) を実装して不正データを許容・正しく扱う。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集モジュールを実装（デフォルト: Yahoo Finance のビジネス RSS）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）を実装し、記事 ID を一意にハッシュ化して冪等性を担保。
  - defusedxml を用いた XML パースでセキュリティ対策を実施（XML Bomb 等）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定しメモリ DoS を防止。
  - DB 保存はバルク/チャンク処理とトランザクション化を想定（INSERT チャンクサイズ制御）。
  - 不正な URL スキームや SSRF を防ぐためのチェックを想定した実装（コメント/設計に記載）。

- 研究用 / ファクター計算 (src/kabusys/research/)
  - factor_research モジュールを追加:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算ロジックを実装。DuckDB のウィンドウ関数を使用。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算（EPS が 0/欠損 の場合は None）。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算するユーティリティ。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位（ties）を平均ランクで扱うランク変換ユーティリティ。
  - research パッケージの公開 API を定義。

- 戦略（Strategy） (src/kabusys/strategy/)
  - feature_engineering モジュールを追加:
    - 研究環境の生ファクターをマージし、ユニバースフィルタ（最低株価、20日平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクションで原子性を確保）。
    - ユニバース条件・正規化・アップサート処理を含む一連のフローを実装。
  - signal_generator モジュールを追加:
    - features と ai_scores を統合し、複数コンポーネント（momentum/value/volatility/liquidity/news）から final_score を算出（デフォルト重みを実装）。
    - シグモイド変換、欠損コンポーネントの中立補完(0.5)、重みの検証（負値や NaN を排除、合計が 1 に正規化）を実装。
    - Bear レジーム判定（ai_scores の regime_score の平均が負）により BUY シグナルを抑制。
    - BUY/SELL のシグナル生成ロジックを実装し、signals テーブルへ日付単位で置換（トランザクション）。
    - SELL 判定ロジックにストップロス（-8%）とスコア低下条件を実装。未実装のエグジット（トレーリングストップ / 時間決済）はコメントで明記。

- ログとエラー処理
  - 各モジュールで適切なログ出力を追加（info/warning/debug）。
  - DB 操作時のトランザクションロールバックの退避ログを実装。

### 変更 (Changed)
- -（初回リリースのため過去からの変更なし）

### 修正 (Fixed)
- -（初回リリースのため過去からの修正なし）

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML による攻撃を防止。
- ニュース取得時の URL 正規化・トラッキング除去処理や受信サイズ制限により SSRF / DoS のリスクを軽減。
- J-Quants クライアントで認証トークンの自動リフレッシュと限定された再試行を実装（無限再帰対策あり）。

### パフォーマンス (Performance)
- DuckDB のウィンドウ関数を多用して複数ホライズン/移動平均を SQL 側で一括計算することで Python 側処理のオーバーヘッドを低減。
- jquants_client のページネーションループでトークンキャッシュを共有し、ページ間の認証オーバーヘッドを減らす。
- news_collector のバルクINSERTチャンク処理で DB オーバーヘッドを抑制。

### 既知の問題・制約 (Known issues / Limitations)
- signal_generator の一部エグジット条件（トレーリングストップ / 時間決済）は未実装で、positions テーブルに peak_price / entry_date が必要（コメント参照）。
- execution パッケージは空の __init__.py のみであり、実際の注文発注ロジック（kabu API 連携など）は未実装。
- zscore_normalize は kabusys.data.stats から利用しているが、stats モジュールの実装は本差分で確認できない（別ファイルに存在する想定）。
- news_collector の完全な RSS パース / 記事抽出ロジックの続き（XMLパース→記事構築→DB保存の細部）はコード断片の最後で切れているため、具体的な実装はリポジトリ内の残りの実装を参照する必要あり。
- 一部の DB テーブル（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news など）はスキーマが前提として用いられているため、データベース初期化・マイグレーション手順が必要。

### マイグレーション / 注意事項 (Migration / Upgrade notes)
- 動作に必要な必須環境変数を設定すること:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB / SQLite のファイルパスは環境変数 DUCKDB_PATH / SQLITE_PATH で上書き可能（デフォルトは data/kabusys.duckdb / data/monitoring.db）。
- KABUSYS_ENV は development / paper_trading / live のいずれかを指定。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか。

### 将来対応予定（コメント / ドキュメントに示唆）
- execution 層の実装（実際の注文送信、注文状態の追跡、kabu API クライアント実装）。
- 信号のポートフォリオ最適化・ポジションサイズ計算ロジック。
- news_collector の記事→銘柄マッピング処理（news_symbols）と自然言語処理に基づく AI スコア算出 pipeline。
- より詳細な DB スキーマ定義とマイグレーションスクリプトの提供。
- 単体テスト・統合テストの追加（特に API クライアントのモックによるテスト、DB 操作のトランザクションテスト）。

---

（注）本 CHANGELOG は提供されたコードスニペットの内容・コメント・設計方針から推測して作成しています。リポジトリ全体の実体や追加ファイルによっては記載が不完全な場合があります。追記・修正したい点があれば教えてください。
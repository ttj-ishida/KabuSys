# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - モジュール公開 API: data, strategy, execution, monitoring を __all__ として公開。

- 環境設定/ローディング (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを追加。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - プロジェクトルート検出: 現在ファイル位置から .git または pyproject.toml を探索してプロジェクトルートを特定（配布後も動作）。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、行内コメント処理などに対応。
  - 設定クラス Settings を提供。必須値の取得（_require）で未設定時は ValueError を送出。
  - 管理対象の環境変数例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証あり）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証あり）
  - Settings に is_live / is_paper / is_dev のヘルパーを追加。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - データ取得機能を追加:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - 認証/トークン管理:
    - get_id_token(refresh_token) 実装（リフレッシュトークンから id token を取得）。
    - モジュールレベルで id token をキャッシュし、ページネーション間で再利用。
    - 401 を受けた場合は id token を自動リフレッシュして 1 回だけリトライ。
  - レート制御とリトライ:
    - 固定間隔スロットリングによるレート制限（デフォルト 120 req/min）。
    - ネットワーク/HTTP エラーに対する指数バックオフリトライ（最大 3 回）。408/429/5xx を再試行対象に含む。
    - 429 の場合は可能なら Retry-After を尊重。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - 保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING を利用）。
    - fetched_at を UTC ISO8601 で記録（Look-ahead バイアス追跡対応）。
    - PK 欠損行はスキップし、スキップ件数をログ警告。

- ニュース収集 (kabusys.data.news_collector)
  - RSS から記事を収集して raw_news へ保存するフローを実装。
  - セキュリティ対策:
    - defusedxml を利用して XML 関連の攻撃を緩和。
    - HTTP(S) スキーム以外の URL を拒否する方針（SSRF 対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
  - URL 正規化:
    - トラッキングパラメータ（utm_* 等）を除去、スキーム/ホストを小文字化、フラグメント削除、クエリパラメータソート。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）などにより冪等性を確保（説明あり）。
  - バルク挿入のチャンク化とトランザクションで性能と一貫性を考慮。
  - デフォルト RSS ソースとして Yahoo Finance ビジネスカテゴリを登録。

- データ処理・研究用ユーティリティ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research):
    - calc_momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
    - calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - calc_value（per, roe。raw_financials から最新財務を結合）
    - 実装は DuckDB の SQL ウィンドウ関数と最小限の Python により行う。
    - 日付スキャン範囲バッファやデータ不足時の None 処理を考慮。
  - 特徴量探索 (kabusys.research.feature_exploration):
    - calc_forward_returns（将来リターン: デフォルト horizons=[1,5,21], horizons のバリデーションあり）
    - calc_ic（ランク相関による Spearman の ρ を計算。サンプル数不足時は None を返す）
    - factor_summary（count/mean/std/min/max/median を計算）
    - rank（同順位は平均ランクを採用。浮動小数丸めによる ties 対策あり）
  - zscore_normalize を data.stats から再エクスポート（パッケージ __all__ に含む）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を提供:
    - research モジュールの生ファクター（momentum / volatility / value）を取得、統合。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 数値ファクターの Z スコア正規化（対象カラム指定）と ±3 でのクリップ。
    - features テーブルへ日付単位で置換（DELETE + bulk INSERT をトランザクションで行い原子性を保証）。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を提供:
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - コンポーネント: momentum, value, volatility, liquidity, news（デフォルト重みを採用）。ユーザー指定の weights は検証・補完・再スケール処理を行う。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）で BUY シグナルを抑制。
    - SELL 条件（ストップロス: -8% / スコア低下）を実装。SELL は BUY より優先され、signals テーブルへの書き込みは日付単位で置換。
    - positions テーブルの情報を参照し、価格欠損時の SELL 判定スキップやログを出力。

### 変更 (Changed)
- （初回リリースのため過去からの変更はなし）

### 修正 (Fixed)
- （初回リリースのため修正履歴はなし）

### セキュリティ (Security)
- ニュース収集で defusedxml を使用、RSS パース時の脆弱性軽減。
- URL 正規化とスキーム制限により SSRF 等のリスクを低減。
- J-Quants クライアントでリトライ制御とトークン自動更新を実装し、認証周りのレジリエンスを向上。

### 既知の制限 / TODO
- positions テーブルに peak_price / entry_date 等の情報がないため、signal_generator ではトレーリングストップや時間決済など一部のエグジット条件は未実装（注記あり）。
- 一部のユーティリティ（例: ID の生成ロジック・news と銘柄紐付けの詳細）は説明のみで実装詳細の拡張が想定される。
- 実運用では外部 API キー・パスワードの管理に注意（.env の保護など）。

---

注: 本 CHANGELOG はコードベースからの推測に基づく初期リリースの要約です。実際の変更履歴や日付はプロジェクトのリリース運用に従って更新してください。
# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（現在のリポジトリ状態は最初の公開リリースに対応しています。次のリリースに向けた変更はここに記載してください。）

---

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システムのコアライブラリを提供します。設計上の重点は「ルックアヘッドバイアスの回避」「冪等性」「DuckDB を用いたローカルデータ管理」「外部 API の安全な呼び出し（レート制御・リトライ・トークンリフレッシュ）」「研究(R&D)と実行層(Execution)の分離」です。

### 追加（Added）
- パッケージ基盤
  - kabusys パッケージ初期実装（バージョン 0.1.0）。
  - public インターフェースとして data, strategy, execution, monitoring を __all__ に公開。

- 環境・設定管理（kabusys.config）
  - .env ファイル自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を基準）。
  - .env と .env.local の優先順位および OS 環境変数保護機能（.env.local は上書き、既存 OS 環境は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
  - .env 行パーサの強化:
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理（クォートの有無に応じた振る舞い）
  - Settings クラスによる型付プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須に設定（未設定時は ValueError）
    - KABUSYS_ENV（development / paper_trading / live）の検証
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - データベースパスのデフォルト（DUCKDB_PATH, SQLITE_PATH）と Path 型での取得

- Data 層（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - API 呼び出し共通処理：固定間隔レートリミッタ（120 req/min）、ページネーション対応
    - 再試行（指数バックオフ、最大 3 回）：408/429/5xx およびネットワークエラーを対象
    - 401 受信時の自動トークンリフレッシュ（1 回のみリトライ）
    - トークンキャッシュ（モジュールレベル）によりページング間でトークンを共有
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar の実装（ページネーション対応）
    - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）
      - INSERT の冪等化（ON CONFLICT DO UPDATE / DO NOTHING）
      - fetched_at を UTC ISO 形式で記録（Look-ahead バイアスのトレース）
      - 型変換ユーティリティ (_to_float, _to_int) による安全なパース
  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS からニュースを収集して raw_news に保存するための処理
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）
    - defusedxml を用いた安全な XML パース（XML Bomb 等の防御）
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES: 10MB）でメモリ DoS を防止
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を保証
    - DB バルク挿入のチャンク処理（_INSERT_CHUNK_SIZE）および 1 つのトランザクションにまとめる方針
    - デフォルト RSS ソース（yahoo_finance）を提供
    - SSRF 対策（スキーム検証等）やトラッキングパラメータ除去ロジックを実装

- 研究（Research）層（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を DuckDB の SQL とウィンドウ関数で計算
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（true range の NULL 伝播制御）
    - calc_value: 最新の raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0/欠損時は None）
    - 各関数は prices_daily / raw_financials のみを参照し、本番 API に依存しない設計
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（既定: [1,5,21] 営業日）に対する将来リターンを一括取得
    - calc_ic: スピアマンの rho（ランク相関）により IC を計算（有効サンプル 3 件未満は None）
    - factor_summary: 各ファクター列の統計量（count/mean/std/min/max/median）を算出
    - rank: 同順位は平均ランクを返す安定したランク付け（浮動小数の丸めで ties 対応）
  - 研究層は外部ライブラリ（pandas 等）に依存しない実装

- 戦略（Strategy）層（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research 側で計算した生ファクターを統合・正規化して features テーブルへ UPSERT
    - ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 5 億円）
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、 ±3 でクリップ
    - 日付単位での置換処理（DELETE → BULK INSERT）をトランザクションで実行し冪等性を確保
    - ルックアヘッドバイアスを避けるため target_date 時点のデータのみ使用
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して銘柄ごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - コンポーネントの変換:
      - Z スコアをシグモイドで [0,1] にマップ
      - PER は逆数スコア（低 PER = 高 score）
      - ATR は反転した Z スコアをシグモイド変換（低ボラ = 高スコア）
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）
    - 重みはユーザ指定で上書き可（検証・再スケール処理あり、無効値は無視）
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY 抑制、ただしサンプル数閾値あり）
    - BUY シグナル閾値デフォルト 0.60、SELL（エグジット）条件:
      - ストップロス: 終値/avg_price - 1 < -8%
      - スコア低下: final_score < threshold
    - SELL を優先して BUY から除外する方針
    - 日付単位での signals テーブル置換（トランザクション＋バルク挿入）

### 変更（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### セキュリティ（Security）
- news_collector で defusedxml を用い XML 攻撃を軽減。
- J-Quants クライアントでリトライ制御とトークン自動リフレッシュを実装し、不正トークン状態での端末影響を低減。

### 注意事項 / 必須設定
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかでなければならず、LOG_LEVEL は許容値に従う必要があります。未設定や不正な値は ValueError を発生させます。
- DuckDB / SQLite のデフォルトパスは DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。必要に応じて環境変数で上書きしてください。

---

今後の予定（例）
- execution 層の実装（発注ロジックと kabu API 連携）
- モデル学習・AI スコアリングパイプラインの整備
- テストカバレッジ拡充と CI/CD の追加

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のコミット履歴やリリースポリシーに応じて適宜編集してください。）
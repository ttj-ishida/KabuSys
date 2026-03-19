Changelog
=========

すべての注目すべき変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。  

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-19
-------------------

Added
- 初期リリース: kabusys パッケージ（バージョン 0.1.0）。
  - パッケージ構成: data, research, strategy, execution, monitoring（__all__ を公開）。
- 環境設定
  - robust な .env ローダー実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して自動ロード。
    - .env / .env.local の読み込み順序と上書きルールを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env パーサはコメント行、export プレフィックス、クォート付き値、エスケープ、インラインコメント処理に対応。
    - Settings クラスで必須環境変数取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や型変換（Path）・検証（KABUSYS_ENV, LOG_LEVEL）を提供。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH）を Path 型プロパティで取得。
- Data: J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）は冪等性を考慮した INSERT ... ON CONFLICT を使用。
  - 型変換ユーティリティ（_to_float / _to_int）を提供。
- Data: ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集の骨格。記事の正規化・トラッキングパラメータ除去・URL 正規化・ID の SHA-256 ベース採番方針。
  - セキュリティ対策: defusedxml を使用、受信サイズ制限（10 MB）、HTTP/HTTPS スキーム検査、SSRF 注意喚起、チャンク化したバルクINSERT。
  - デフォルト RSS ソース定義（Yahoo Finance のカテゴリ RSS をデフォルトに設定）。
- Research（src/kabusys/research/*）
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、MA200 乖離率（ma200_dev）を計算。
    - calc_volatility: ATR(20)、atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: target_date 以前の最新財務データと価格を組み合わせて PER / ROE を算出。
    - 各関数は prices_daily / raw_financials テーブルのみ参照し、結果を (date, code) ベースの dict リストで返す。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）計算（ties の平均ランク処理を含む）。
    - factor_summary, rank: 基本統計量とランク変換ユーティリティ。
  - research パッケージの __all__ を整備。
- Strategy（src/kabusys/strategy/*）
  - feature_engineering.build_features:
    - research の生ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化（zscore_normalize）→ ±3 でクリップ→ features テーブルへ日付単位で置換（トランザクションで atomic）。
    - 休場日や欠損に対応するため、target_date 以前の最新終値を参照。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み（momentum 0.40 等）を提供し、ユーザ指定重みは検証・補正（合計を 1.0 に再スケール）。
    - Sigmoid や中立補完（欠損コンポーネントは 0.5）を用いて final_score を算出。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）により BUY シグナル抑制。
    - BUY（threshold=0.60）/SELL（ストップロス -8% / スコア低下）生成、signals テーブルへの日付単位置換（トランザクションで atomic）。
    - SELL 対象は BUY から除外し、ランクを再付与するポリシーを実装。
- 汎用/実装方針
  - ルックアヘッドバイアス回避のために target_date 時点までのデータのみ参照する設計。
  - 外部依存を極力避け、標準ライブラリ + duckdb による実装を目指す（research/feature_exploration は pandas など非依存）。
  - トランザクション管理とロールバック処理を追加し、DB 書き込みの原子性を確保。
  - ロギング（logger.debug/info/warning）を各処理に配置し実行時のトラブルシュートを支援。

Fixed
- （初期リリースのため既知のバグ修正履歴はなし。ただし多くの箇所で入力検証・エラーハンドリング・ロールバック処理を強化。）

Security
- RSS パースに defusedxml を使用して XML 攻撃を緩和。
- ニュース収集で受信サイズ制限や URL 正規化を実装してメモリ DoS / トラッキング対策、SSRF のリスク軽減に配慮。
- J-Quants クライアントでトークンの自動リフレッシュとレートリミットを実装し、不正なリトライ/過負荷を抑制。

Notes / Known limitations / TODO
- signal_generator の未実装・制限事項（コード内コメント参照）
  - トレーリングストップ（直近最高値から -10%）は未実装（positions テーブルに peak_price が必要）。
  - 時間決済（保有 60 営業日超過）も未実装（entry_date 情報が必要）。
- calc_value では PBR・配当利回りは未実装。
- news_collector: RSS のパース～DB保存の流れは整備されているが、ソース追加や記事→銘柄紐付けロジック等は拡張の余地あり。
- execution / monitoring パッケージはインタフェースが存在するが、外部ブローカー接続や実際の発注ロジックは本バージョンでは含まれない設計（依存分離）。
- 外部ライブラリ最小化の方針により、分析用ユーティリティは手作り実装（パフォーマンスや高度な統計処理は将来要改善の可能性あり）。

依存関係（注）
- DuckDB をデータ層に使用。外部 HTTP リクエスト実行のため標準ライブラリ urllib を利用。
- セキュリティ目的で defusedxml を利用（news_collector）。

---

以上がコードベース（バージョン 0.1.0）から推測できる主要な変更点・特徴です。必要であれば各機能ごとにより詳細なリリースノート（SQL スキーマ要件、環境変数一覧、例外メッセージ一覧、API 使用例など）を追記できます。どの情報を優先して追加しますか？
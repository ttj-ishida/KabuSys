# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のリリース: 0.1.0

Unreleased
- なし

[0.1.0] - 2026-03-19
Added
- パッケージ初版を追加
  - src/kabusys/__init__.py
    - パッケージ名・公開 API を定義。バージョン __version__ = "0.1.0"。

- 環境設定・自動 .env ローダー
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする機能を実装。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可。
    - 複数形式の .env 行パースに対応（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなど）。
    - .env を読み込む際の上書きロジック（.env は OS 環境変数を保護、.env.local は上書き）を実装。
    - Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境モード / ログレベル等）。バリデーション（KABUSYS_ENV, LOG_LEVEL）と利便性プロパティ（is_live / is_paper / is_dev）付き。
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

- データ取得・永続化（J-Quants API）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。主な特徴:
      - 固定間隔の RateLimiter（120 req/min を想定）でスロットリング。
      - リトライ（指数バックオフ、最大3回）。HTTP 408/429/5xx およびネットワークエラーに対する再試行処理。
      - 401 Unauthorized 受信時の自動トークンリフレッシュ（1回のみ）を実装。
      - ページネーションに対応した fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
      - DuckDB への冪等的保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT / DO UPDATE を用いた重複除去。
      - データフォーマット変換ユーティリティ（_to_float, _to_int）。
      - ログや fetched_at（UTC ISO8601）を記録して Look-ahead バイアスの追跡を容易に。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集し raw_news に保存するためのユーティリティを実装。
    - セキュリティ対策: defusedxml を利用して XML Bomb 等を防止、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、HTTP/HTTPS スキーム検証、SSRF 緩和のためのホストチェック方針準備。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装。記事ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）を利用する設計。
    - テキスト前処理（URL 除去・空白正規化）、バルク INSERT チャンク処理などパフォーマンス考慮の実装。

- リサーチ用ファクター計算・解析
  - src/kabusys/research/factor_research.py
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクターを実装。すべて DuckDB の prices_daily / raw_financials テーブルのみを参照。
    - 各計算は営業日ベースの窓・ラグを利用。データ不足時の None 処理、ウィンドウサイズやスキャン範囲のバッファ設計あり。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）でのリターンを一度のクエリで取得する実装。
    - IC（Information Coefficient）計算（calc_ic）：Spearman の ρ をランクに基づき計算。サンプル不足時の None 返却。
    - factor_summary / rank 実装：基本統計量（count/mean/std/min/max/median）と同順位処理（平均ランク）を提供。
  - src/kabusys/research/__init__.py
    - 上記関数群をパッケージ公開。

- 特徴量エンジニアリング（本番戦略向け）
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で計算した生ファクターを正規化・合成し、features テーブルへ保存する処理（build_features）。
    - フロー: calc_momentum / calc_volatility / calc_value を統合、株価/流動性に基づくユニバースフィルタ（最低株価300円、20日平均売買代金 >= 5億円）、Zスコア正規化（kabusys.data.stats.zscore_normalize）→ ±3 でクリップ、日付単位での置換（DELETE → INSERT）による冪等性を確保。
    - features へ挿入するカラム名を明示（momentum_20/momentum_60/volatility_20/volume_ratio/per/ma200_dev など）。

- シグナル生成エンジン（戦略層）
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成（generate_signals）。
    - デフォルト重みと閾値（DEFAULT_WEIGHTS, DEFAULT_THRESHOLD）を実装。ユーザー重み入力のバリデーションと再スケーリングを行う。
    - スコア計算: モメンタム（sigmoid + 平均）、バリュー（per に基づく関数）、ボラティリティ（逆転シグモイド）、流動性（出来高比率のシグモイド）、AI（s_news）を統合。欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かどうか。ただしサンプル数が少ない場合は Bear とみなさない）。
    - 保有ポジションに対するエグジット判定（ストップロス -8% / スコア低下）。SELL 対象は BUY から除外し、ランク付けを再割り当て。日付単位での置換（DELETE → INSERT）による冪等性を確保。
    - 未実装のエグジット条件としてトレーリングストップ・時間決済が注記（positions テーブル側に peak_price/entry_date が必要）。

- パッケージ公開
  - src/kabusys/strategy/__init__.py / src/kabusys/research/__init__.py
    - 主要 API を __all__ で公開（build_features / generate_signals / calc_momentum / ... / zscore_normalize 等）。

Security
- ニュース収集で defusedxml 利用、HTTP スキーム検証、受信サイズ制限などを導入して外部入力に対する安全性を考慮。
- J-Quants クライアントでのトークン管理およびリトライ制御により認証やネットワークエラーでの安全な挙動を確保。

Notes / Known limitations
- signal_generator の一部のエグジット条件（トレーリングストップ、時間決済）は未実装で、positions テーブルに peak_price/entry_date が必要。
- feature_engineering では avg_turnover をユニバースフィルタ用に利用するが、features テーブルには保存していない（ドキュメント注記）。
- zscore_normalize の実体は kabusys.data.stats 側に依存しており、本リリースではその実装を前提としている（本コードベースの一部ファイルに含まれていない場合がある）。
- NewsCollector のネットワークリクエストや RSS パースの外部エッジケース（特殊エンコーディング等）は追加テストが推奨される。
- config の自動 .env ロードはプロジェクトルート検出に依存するため、配布形態やインストール方法によっては手動で環境変数を設定する必要がある。

リリースノート作成者
- 自動生成（コードベースから推測）による CHANGELOG。実際のリリースや公開前に内容をプロジェクト責任者が確認してください。
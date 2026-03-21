CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。セマンティック バージョニングを採用します。

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-21
-------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
  - モジュール群: data, research, strategy, execution, monitoring（execution は空のイニシャライザを含む）
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装
  - 自動読み込みの判定にプロジェクトルート（.git または pyproject.toml）を使用して CWD に依存しない設計
  - .env パーサを独自実装（コメント／export 形式、シングル/ダブルクォートとバックスラッシュエスケープ対応、行末コメント処理）
  - .env と .env.local の読み込み順序と override 挙動を実装（OS 環境変数は protected）
  - テスト用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意
  - Settings クラスを提供し、必須変数チェック（_require）、型変換（Path）や値検証（KABUSYS_ENV, LOG_LEVEL）を実装
  - 設定キー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH など
- データ取得クライアント: J-Quants API (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装（_request）
  - レート制限制御 (固定間隔スロットリング) を実装する _RateLimiter（120 req/min に対応）
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の Retry-After ヘッダ尊重
  - 401 (Unauthorized) 受信時の自動トークンリフレッシュ処理（1 回のみ）とモジュールレベルの ID トークンキャッシュ
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装
  - DuckDB への冪等保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT を用いた更新、PK 欠損行のスキップとログ出力を行う
  - 型変換ユーティリティ (_to_float / _to_int) を実装し、不正な入力を安全に扱う
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集機能、記事正規化・保存処理の土台を実装
  - URL 正規化機能（トラッキングパラメータ除去、クエリソート、小文字化、フラグメント削除）
  - セキュリティ考慮: defusedxml を用いた XML パース、HTTP/HTTPS スキームチェック、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）など設計指針を採用
  - バルク INSERT のチャンク処理、挿入された件数を正確に返す想定の設計
  - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを追加
- 研究（research）モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日移動平均乖離）を DuckDB のウィンドウ関数で算出
    - calc_volatility: ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を算出。true_range を NULL 伝播で正確に扱う
    - calc_value: raw_financials から最新財務を結合し PER / ROE を計算
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）を一度のクエリで取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（同順位は平均ランク）
    - factor_summary / rank: 基本統計量算出、ランク変換ユーティリティを提供
  - research パッケージの __all__ を整備
- 戦略（strategy）モジュール (src/kabusys/strategy/)
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - research モジュールで計算した生ファクターをマージ、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップし、features テーブルへ日付単位の置換（トランザクションで原子性）
    - ユニバースフィルタ基準（_MIN_PRICE=300 円, _MIN_TURNOVER=5e8 円）を実装
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付き合算で final_score を計算
    - デフォルト重みと閾値を実装（デフォルト閾値 _DEFAULT_THRESHOLD=0.60）
    - Bear レジーム判定（ai_scores.regime_score の平均が負かつサンプル数閾値）により BUY を抑制
    - BUY / SELL シグナル生成ロジック（ストップロス -8%、スコア低下等）および signals テーブルへの日付単位の置換（トランザクション）
    - weights のバリデーション・スケーリングロジックを実装し、無効な重みを警告して除外
  - strategy パッケージの公開関数 build_features / generate_signals を __all__ に追加
- 共通ユーティリティ・設計方針
  - DuckDB を主体としたデータフロー設計、SQL と Python を組み合わせた計算手法
  - 冪等性（ON CONFLICT / 日付単位での DELETE→INSERT）とトランザクション管理（BEGIN / COMMIT / ROLLBACK）によるデータ整合性確保
  - ロギング（logger）を随所に導入して運用観測を容易に

Changed
- 初回リリース (初期実装のため変更履歴はなし)

Fixed
- 初回リリース (初期実装のため修正履歴はなし)

Security
- ニュース収集で defusedxml を利用して XML 攻撃を軽減
- ニュース収集で受信サイズ上限（10MB）やスキーム検証、トラッキングパラメータ除去など SSRF / DoS 対策を考慮
- 環境変数読み込みで OS 環境変数を protected として .env による上書きを回避

Performance
- J-Quants API クライアントに固定間隔レートリミッタを導入し、API レート上限に合わせて呼び出しを平滑化
- DuckDB への保存は executemany を活用したバルク挿入設計、news_collector はチャンク挿入を想定

Reliability
- _request における再試行・指数バックオフ・Retry-After 処理と 401 自動リフレッシュで外部 API 呼び出しの堅牢性を向上
- 各種データ保存処理でトランザクションと例外発生時のロールバック処理を実装
- settings のバリデーションで不正な設定値を早期検出

Notes / Known limitations
- execution / monitoring 層は未実装（パッケージ構成上のプレースホルダ）
- news_collector の完全な RSS パースおよび銘柄紐付け処理は設計方針が記載されているが、このリリースでは基盤実装の一部（URL 正規化等）まで
- signal_generator の一部のエグジット条件（トレーリングストップ、時間決済）は positions テーブルの追加情報（peak_price / entry_date 等）が未実装のため対応されていない
- research モジュールは pandas 等に依存せず標準ライブラリ + DuckDB で実装されており、非常に大規模データでのメモリ特性は実運用での確認が必要

Authors
- このリリースの主要実装は kabusys コードベースに含まれる docstring とモジュール設計に基づき作成されました。

お問い合わせ
- バグ報告・改善提案は issue を立ててください。
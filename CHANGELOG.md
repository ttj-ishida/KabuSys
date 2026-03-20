# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このリポジトリはセマンティックバージョニングを採用しています。

なお、以下の内容はコードベース（src/ 以下）の実装内容から推測して作成した変更履歴です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-20
初回リリース

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダーを実装（読み込み順: OS 環境変数 > .env.local > .env）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .git または pyproject.toml を基準にプロジェクトルートを検出する実装により、CWD に依存しない .env 探索を実現。
  - .env ファイルのパース機能を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等に対応）。
  - 環境設定を取得する Settings クラスを提供。必須値取得時のエラー (_require) と各種プロパティを定義:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須項目。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH のデフォルト値を定義。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API との HTTP 通信ユーティリティを実装。
  - レート制限制御（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
  - リトライロジック（最大 3 回、指数バックオフ）を実装。HTTP 408 / 429 / 5xx に対する再試行を行う。
  - 401 Unauthorized を検知した場合、自動的にリフレッシュトークンで id_token を再取得して 1 回のみリトライする仕組みを搭載。
  - ページネーション対応のデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。
    - 保存は冪等（ON CONFLICT DO UPDATE）で重複を排除。
    - fetched_at を UTC ISO8601 で記録し、データ取得時刻をトレース可能に。
    - 入力パースの補助ユーティリティ _to_float / _to_int を提供し、型変換時の安全性を確保。
  - ネットワーク・HTTP エラー時のログ出力と待機戦略を備える。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news テーブルへ保存する基礎実装。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリのソート）を実装。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）などで生成し冪等性を担保する設計（ドキュメントに明記）。
  - defusedxml を用いた XML パース（XML Bomb 等の防御）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 緩和、バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）。
  - 設計段階で SSRF 防止・HTTP/HTTPS スキーム制限、トラッキングパラメータ除去などの考慮があることを明記。

- 研究用ファクター計算（kabusys.research）
  - ファクター計算 API を提供（calc_momentum, calc_volatility, calc_value）。
  - 研究用ユーティリティ（zscore_normalize を再エクスポート）。
  - 特徴量探索モジュール（feature_exploration）を実装:
    - calc_forward_returns: 指定日から各ホライズン先の将来リターンを一括で取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効サンプルが 3 未満なら None）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとなるランク付け（round(..., 12) による安定化）。
  - DuckDB を用いた SQL ベースの集計処理で、prices_daily / raw_financials の参照に限定。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）:
    - research モジュールが算出した生ファクターをマージし、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定列を Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位の置換（DELETE + INSERT、トランザクション）で冪等に保存。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。
  - シグナル生成（signal_generator.generate_signals）:
    - features と ai_scores を統合して各種コンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - シグモイド変換と重み付けで final_score を計算。デフォルト重みを持ち、ユーザー渡しの weights は検証・正規化される（未知キーや無効値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）により BUY を抑制。
    - BUY は threshold（デフォルト 0.60）を超えた銘柄に対して発生。SELL は保有ポジションに対してストップロス（-8%）やスコア低下を判定して発生。
    - 欠損ファクターは中立値（BUY 側: 0.5）で補完し、不当な降格を防止。保有銘柄で features が欠ける場合は SELL 判定時に final_score=0.0 と見なす。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等に保存。
    - SELL 優先ポリシー（SELL 対象を BUY から除外しランクを再付与）を実装。

- データ品質 / トランザクション設計
  - 複数の書き込み処理（features, signals, raw_prices, raw_financials, market_calendar）でトランザクション（BEGIN/COMMIT/ROLLBACK）を用いて原子性を確保。ROLLBACK 失敗時は警告ログ出力。
  - SQL 側でウィンドウ関数等を活用し、効率的に過去データ参照・集計を実行。

### Changed
- N/A（初回リリースのため過去バージョンからの変更は無し）。

### Fixed
- N/A（初回リリースのため修正履歴は無し）。

### Security
- ニュースパーサーで defusedxml を使用し、XML 関連の脆弱性（XML Bomb 等）への対応が図られている点を明記。
- J-Quants クライアントは認証トークンを安全にリフレッシュし、取得時刻を UTC で記録することでデータの「知り得た時刻」を追跡可能にしている。

### Breaking Changes
- なし（初回リリース）。

---

注記:
- 本 CHANGELOG はコード内容を基に自動的に推測して作成しています。実際の運用上の変更点やリリースノートと差異がある場合があります。必要に応じて日付・表現・追加の詳細（リリース手順、既知の制限事項、マイグレーション手順等）を追記してください。
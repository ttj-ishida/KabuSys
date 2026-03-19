CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

[Unreleased]
------------

（なし）

0.1.0 - 初回リリース
-------------------

リリース概要:
  - 初期バージョンとして日本株自動売買システム "KabuSys" のコアモジュール群を実装。
  - 主にデータ収集・保存（DuckDB）、ファクター算出・解析、外部 API 連携、ニュース収集、環境設定を提供。

Added（追加）
  - パッケージ初期化
    - kabusys.__init__ にバージョン情報と主要サブパッケージ（data, strategy, execution, monitoring）を公開。
  - 設定管理（kabusys.config）
    - .env ファイルと環境変数を統合して読み込む自動ロード機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml を起点）により、CWD に依存しない自動 .env ロードを実現。
    - 高度な .env パーサを実装（export 形式対応、クォート内エスケープ、インラインコメント処理）。 
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
    - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_* 等）取得と妥当性チェックを実装。
    - デフォルト値（KABUSYS_ENV=development、LOG_LEVEL=INFO、データベースパス等）を定義。
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 汎用 HTTP リクエストユーティリティ（_request）にリトライ（指数バックオフ）、429 の Retry-After 処理、401 時のトークン自動リフレッシュを実装。
    - ページネーション対応のデータ取得関数を提供:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB へ冪等的に保存する関数を提供（ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - 型変換ユーティリティ _to_float / _to_int を用意（堅牢な変換とエッジケース処理）。
    - ID トークンのキャッシュ／共有機構を導入し、ページネーション間で再利用可能。
  - ニュース収集モジュール（kabusys.data.news_collector）
    - RSS フィードからニュースを収集し raw_news へ保存する一連の処理を実装。
    - defusedxml を用いた安全な XML パース（XML Bomb 等の防御）。
    - RSS レスポンスの最大バイト数制限（MAX_RESPONSE_BYTES）および gzip 解凍後のサイズチェック（Gzip bomb 対策）を導入。
    - URL 正規化（トラッキングパラメータ削除、ソート、フラグメント削除）と記事 ID（SHA-256 の先頭32文字）生成で冪等性を保証。
    - SSRF 対策:
      - 許可スキームを http/https のみに制限。
      - リダイレクト時にスキーム・ホスト検証を行うカスタム RedirectHandler を導入。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであればアクセスを拒否。
    - テキスト前処理（URL 除去、空白正規化）を実装。
    - raw_news へのバルク INSERT をチャンク（_INSERT_CHUNK_SIZE）分割で行い、INSERT ... RETURNING で新規挿入された記事 ID を正確に返す。
    - 銘柄コード抽出（4桁数字、既知コードとの突合）と news_symbols への紐付け機能を提供（バルク挿入、ON CONFLICT による重複排除）。
    - run_news_collection により複数 RSS ソースからの収集を統合（ソース単位で独立してエラーハンドリング）。
  - Data schema（kabusys.data.schema）
    - DuckDB 用のスキーマ DDL を追加（Raw Layer など）。raw_prices, raw_financials, raw_news 等のテーブル定義を含む（raw_executions の雛形含む）。
  - Research（kabusys.research）
    - 研究向けユーティリティとファクター計算を公開するパッケージ API を提供（calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank などを __all__ に記載）。
  - ファクター探索・計算（kabusys.research.feature_exploration, factor_research）
    - calc_forward_returns: DuckDB の prices_daily を参照して複数ホライズンの将来リターンを一括取得する最適化クエリを実装。ホライズン入力チェック（1〜252）あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。欠損や有限性チェック、最小サンプル数（3未満は None）を実装。
    - rank: 同順位は平均ランクで扱う安定したランク関数（丸め誤差対策の round(v, 12) を使用）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計要約。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を DuckDB ウィンドウ関数で計算。足りないデータは None。
    - calc_volatility: 20日 ATR（true_range の平均）、atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播制御により過大評価を防止。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER/ROE を計算（EPS 0 または欠損時は None）。
  - テスト/モック向けの差替えポイント
    - news_collector._urlopen をテストでモック可能（ネットワーク依存の分離）。

Changed（変更）
  - （初版のため該当なし）

Fixed（修正）
  - （初版のため該当なし）

Security（セキュリティ）
  - RSS パーサに defusedxml を採用して XML 攻撃に耐性を持たせた。
  - ニュース収集において SSRF を考慮した複数の防御策を実装（スキーム制限、プライベートホスト拒否、リダイレクト検査）。
  - J-Quants クライアントはトークン管理とリトライポリシーを実装し、401/429/5xx に対する安全な再試行を行う。

Performance（パフォーマンス）
  - DuckDB へのバルク挿入をチャンク化してオーバーヘッドを低減。
  - calc_forward_returns 等で必要最小限の期間に絞ったクエリを発行（スキャン範囲にカレンダーバッファを使用）し、SQL 内で一括計算することで処理を高速化。

Developer notes（開発者向けメモ）
  - Settings オブジェクト（settings）はモジュールロード時に利用可能。必須環境変数未設定時は ValueError を発生させる。
  - research モジュール設計方針として外部ライブラリ（pandas 等）に依存しない純粋 Python / DuckDB 実装を目指している（Feature Exploration モジュールに明記）。
  - 一部の DDL（raw_executions など）はスニペット内で途中まで定義されているため、実運用前に完全なスキーマ確認が必要。

Deprecated（非推奨）
  - （初版のため該当なし）

Removed（削除）
  - （初版のため該当なし）

Notes（注意事項）
  - 現バージョンは「データ収集・保存」「ファクター計算」「ニュース収集」「設定管理」「J-Quants API クライアント」を中心とした基盤実装です。発注・実行ロジック（execution パッケージ）やストラテジ実装（strategy）はまだパッケージの枠組みがある状態で具体実装は含まれていません。
  - DuckDB スキーマやテーブルの完全性、マイグレーション戦略、実運用での監視・ロギング設定は次フェーズでの整備を推奨します。
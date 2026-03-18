CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
（なし）

0.1.0 - 2026-03-18
-----------------
初回公開リリース。以下の主要機能・実装を含みます。

Added
- パッケージ骨組み
  - kabusys パッケージを追加。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - サブパッケージのエントリを用意: data, strategy, execution, monitoring（空の __init__ は一部サブパッケージに含む）。

- 環境設定管理
  - .env ファイルおよび環境変数の自動読み込み機能を実装（src/kabusys/config.py）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - プロジェクトルート検出は __file__ から .git または pyproject.toml を探索して行う（CWD 非依存）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート（エスケープ対応）、インラインコメントを扱う。
  - Settings クラスを提供し、必須変数の取得や検証を行う:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証
    - 各種パス（DUCKDB_PATH, SQLITE_PATH）を Path オブジェクトで扱う

- データ取得クライアント（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔の RateLimiter によるレート制御（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回）。429 の場合は Retry-After を尊重。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（再帰防止フラグあり）。
    - ページネーション対応（pagination_key を使った収集）。
    - 取得データを DuckDB に冪等に保存するユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - fetched_at は UTC で記録し、Look-ahead bias の追跡を容易にする。
    - 型変換ユーティリティ _to_float/_to_int を実装し、不正な値は None とする。

- ニュース収集（RSS）
  - RSS フィード収集・正規化・保存機能を実装（src/kabusys/data/news_collector.py）。
    - RSS 取得（gzip 対応）、XML パース（defusedxml を使用して攻撃を軽減）。
    - レスポンス上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 防御、gzip 解凍後もサイズ検査。
    - SSRF 対策:
      - リダイレクト時にスキーム／ホストを検証するカスタムリダイレクトハンドラ。
      - ホスト（A/AAAA レコード）を DNS 解決してプライベート/ループバック/リンクローカルか判定し拒否。
      - http/https 以外のスキームを拒否。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事 ID（URL 正規化後の SHA-256 先頭 32 文字）生成により冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
    - raw_news へのチャンク挿入（INSERT ... RETURNING）と news_symbols 紐付けの一括挿入。トランザクションでまとめて処理。
    - 銘柄抽出: テキスト中の 4 桁数字パターンに対し、known_codes に基づくフィルタリング・重複除去。

- DuckDB スキーマ初期化（DDL）
  - Data 層の初期スキーマ DDL を追加（src/kabusys/data/schema.py）。
    - raw_prices, raw_financials, raw_news, raw_executions（途中まで定義）などのテーブルを定義。
    - PK／型チェック制約を含む設計。DataSchema.md に基づく 3 層（Raw / Processed / Feature）設計を想定。

- リサーチ / ファクター計算
  - factor_research（src/kabusys/research/factor_research.py）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）ファクターを DuckDB 上の SQL ウィンドウ関数で計算。
    - スキャン範囲のバッファ設定（カレンダー日での余裕）により週末・祝日を吸収。
    - 不足データに対しては None を返す安全な設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（Spearman の ρ を自前ランクで実装）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部ライブラリに依存せず、標準ライブラリと DuckDB 接続で完結する設計。
  - research/__init__.py に主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- SSRF や XML 攻撃対策を実装
  - defusedxml を用いた XML パースで XML Bomb 等のリスクを低減（news_collector）。
  - リダイレクト先検査・プライベート IP 判定・スキーム検証で SSRF を軽減。
  - .env 読み込みでは OS 環境変数を保護する protected オプションを導入（上書き制御）。

Performance / Reliability
- API レート制御とリトライ（jquants_client）で連続リクエスト時の安定性を確保。
- DuckDB への挿入はバルク・チャンク処理および ON CONFLICT で冪等性を確保。news_collector ではチャンクサイズ（1000）を設けた挿入で SQL 長・パラメータ数を抑制。
- SQL 側ではウィンドウ関数と最小スキャン範囲（calendar buffer）を使い不要なスキャンを抑える設計。

Internal
- 設計方針の明文化: 本番口座や発注 API へは直接アクセスしない（リサーチ/特徴量計算はデータベース上で完結）。
- 多くのユーティリティ関数（URL 正規化、日時パース、型変換、ランク付けなど）を提供し、再利用可能な内部 API を整備。
- ロギングを各モジュールで利用（デバッグ/警告/情報ログを適切に出力）。

Known limitations / Notes
- research モジュールは pandas や NumPy を使用せず標準ライブラリで実装しているため、大規模データでの最適化は今後の課題。
- 一部テーブル定義（例: raw_executions）はファイル末尾で未完の箇所がある（DDL の続きがある想定）。運用前にスキーマを最終確認してください。
- strategy / execution / monitoring はパッケージの枠組みを用意しているが、実装は未完成（今後の追加予定）。

貢献・作者情報
- 初期実装として、データ取得・保存、ニュース収集、リサーチ系の基礎を構築しました。今後は戦略実装・発注ロジック・監視機能の追加を予定しています。

ライセンス
- 本プロジェクトのライセンス情報はリポジトリの LICENSE を参照してください（このリリースでは明示なし）。

追記
- 実装の詳細や設計方針は各モジュールの docstring / コメントに記載されています。必要に応じてドキュメント化や API 仕様の追加を行ってください。
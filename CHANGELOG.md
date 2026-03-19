# Changelog

すべての注目すべき変更点をこのファイルに記載します。フォーマットは「Keep a Changelog」準拠です。

全般的な方針：
- セキュリティ（SSRF対策、XMLパースの安全化、トラッキング除去）やデータの冪等性を重視して実装しています。
- Research / Data モジュールは本番発注 API にアクセスしない設計です（データ取得・特徴量計算に限定）。
- DuckDB を主要な永続化層として利用し、INSERT の冪等化（ON CONFLICT）やトランザクション制御を行っています。

## [0.1.0] - 2026-03-19

### 追加
- パッケージ初期リリース。以下の主要コンポーネントを追加。
  - kabusys.config
    - .env ファイルおよび環境変数の読み込み機能を提供。
    - プロジェクトルート（.git または pyproject.toml）を自動検出して .env / .env.local を読み込む自動ロードを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 解析は export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱い（クォートあり／なしでの挙動差分）に対応。
    - Settings クラスを公開し、J-Quants / kabuステーション / Slack / DB パス等の必須/既定設定をプロパティとして取得可能。
    - KABUSYS_ENV と LOG_LEVEL の検証（有効値チェック）を実装。
  - データ取得・保存（kabusys.data）
    - jquants_client
      - J-Quants API クライアントを実装。
      - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
      - リトライロジック（指数バックオフ、最大 3 回）を実装。408/429/5xx を再試行対象に設定。
      - 401 受信時はリフレッシュトークンで自動的に ID トークンを更新して 1 回再試行する仕組みを実装。
      - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。
      - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供し、ON CONFLICT による冪等化を実現。
      - 数値変換ユーティリティ（_to_float, _to_int）を用意し、受信データの型安全な変換を行う。
    - news_collector
      - RSS フィード収集モジュールを実装（デフォルトソースに Yahoo Finance のカテゴリ RSS を登録）。
      - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント削除）、SHA-256 による記事ID生成を実装し冪等性を確保。
      - defusedxml を利用した安全な XML パースを採用（XML ボム対策）。
      - SSRF 対策：URL スキーム検証、リダイレクト検査用ハンドラ、ホストのプライベートアドレス判定を実装。
      - 受信サイズ上限（10 MB）と gzip 解凍後の上限チェックを実装（メモリ DoS 対策）。
      - raw_news / news_symbols への保存はチャンク化・トランザクション化して INSERT ... RETURNING により実際に挿入された件数を正確に取得。
      - テキスト前処理（URL 除去・空白正規化）と記事中からの銘柄コード抽出（4桁数字、既知コードのみ、重複除去）を実装。
      - 高レベルジョブ run_news_collection を提供し、各ソースごとの例外を局所的に扱って継続収集を可能に。
  - データスキーマ（kabusys.data.schema）
    - DuckDB 用スキーマ定義を追加（Raw Layer のテーブル定義を含む）。
    - raw_prices, raw_financials, raw_news, raw_executions など Raw Layer のDDLを定義（テーブル制約・型・主キーを含む）。
  - 研究用モジュール（kabusys.research）
    - feature_exploration
      - calc_forward_returns: 指定日から各ホライズン先の将来リターンを DuckDB の prices_daily テーブルを使って一度のクエリで取得する実装。
      - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を、欠損/非有限値・最小レコード判定（3件未満で None）を考慮して計算。
      - rank: 同順位は平均ランクを返すランク変換を実装（丸めによる ties 検出精度向上のため round(v, 12) を適用）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - factor_research
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を計算。ウィンドウ不足時に None を返す。
      - calc_volatility: 20日 ATR、ATR の割合（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御に注意。
      - calc_value: raw_financials の最新財務データを用い、PER（EPS が 0/欠損なら None）、ROE を計算。prices_daily と組み合わせて取得。
    - research パッケージの __all__ に必要関数を公開（zscore_normalize は kabusys.data.stats からの再公開）。
  - パッケージ初期化
    - src/kabusys/__init__.py にてバージョン (0.1.0) と主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

### セキュリティ
- news_collector:
  - defusedxml を用いた安全な XML パース（XML エクスプロイト対策）。
  - リダイレクト毎にスキームと到達先のホストを検査する専用 RedirectHandler を導入し、内部アドレスや許可外スキームをブロック。
  - URL のスキームチェック（http/https のみ）とホストのプライベートアドレス検査を事前に行う。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES 10 MB）と gzip 解凍後の再チェックによる DoS 対策。
- jquants_client:
  - API トークンの自動リフレッシュとキャッシュにより誤った使い方での再帰を防ぐ設計（allow_refresh フラグ、_get_cached_token）。
  - レート制限ロジックで API ルールを尊重。

### パフォーマンス／信頼性
- DuckDB への大量挿入はチャンク化・executemany/プレースホルダを用いて効率化。
- save_* 関数は ON CONFLICT DO UPDATE（または DO NOTHING）を使って冪等性を担保。
- news_collector の保存はトランザクション単位でまとめ、例外時はロールバックして安全に失敗を伝播。

### 内部実装上の注意点 / 設計判断
- research モジュール（特徴量計算）は外部ライブラリ（pandas 等）に依存せず、標準ライブラリ＋DuckDB SQL で完結する実装を採用（移植性と解析トレーサビリティを重視）。
- 日数・スキャン範囲は週末・祝日を考慮してカレンダーバッファを用いる（営業日ベースのホライズンをカバーするため）。
- .env パーサーは細かいエッジケース（クォート内のエスケープ、コメント判定の差）に対応するよう実装。

### 既知の未実装 / 将来の改善点
- Strategy / Execution / Monitoring パッケージは初期骨組みのみ（実稼働の発注ロジックや監視ロジックは今後追加予定）。
- Feature: PBR・配当利回りなどのバリューファクターは現バージョンで未実装（calc_value に注記あり）。
- News の記事本文からの高度な NLP 処理やエンティティ抽出は未実装。

### バグ修正
- 初リリースのため、過去のバグ修正履歴はありません。

---

今後のリリースでは、戦略実装・発注周りの統合テスト・監視アラート機能の追加、より詳細なログ/メトリクス出力、テストカバレッジの強化を予定しています。必要であれば、CHANGELOG の出力や記載内容を英語版・簡潔版に変換します。
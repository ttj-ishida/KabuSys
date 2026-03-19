# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初期リリース（v0.1.0）に関する主要な変更点・特徴をコードベースから推測してまとめています。

※ バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-03-19

### Added
- パッケージ基盤
  - kabusys パッケージを導入し、公開 API として data, strategy, execution, monitoring を __all__ に登録。
- 設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動ロードする仕組みを実装（プロジェクトルート判定は .git / pyproject.toml を基準）。
  - .env パーサーはコメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントなどを考慮して堅牢に実装。
  - 自動ロード抑止のための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須環境変数取得時の検証（_require）と、KABUSYS_ENV / LOG_LEVEL 等の値検証ロジックを追加。
  - DBパス設定（DUCKDB_PATH/SQLITE_PATH）や Slack / kabu API / J-Quants 用設定プロパティを提供。
- Data 層: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API 用クライアントを実装（トークン取得、ページネーション対応の取得関数）。
  - API レート制御（固定間隔スロットリング）を実装して 120 req/min を遵守する RateLimiter を導入。
  - リトライ戦略（指数バックオフ、最大リトライ回数、429/408/5xx の再試行対応）と 401 発生時の自動トークンリフレッシュを実装。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への冪等的保存（ON CONFLICT DO UPDATE）を行う save_* 関数を実装。fetched_at を UTC ISO タイムスタンプで記録して Look-ahead バイアス追跡可能に。
  - 入力値変換ユーティリティ (_to_float / _to_int) を実装し、不正値や空文字列を安全に扱う。
- Data 層: ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集パイプラインを実装（フェッチ → 前処理 → DB保存 → 銘柄紐付け）。
  - XML パースに対して defusedxml を利用して安全性を確保。gzip 圧縮対応と受信サイズ上限（10MB）による DoS 対策を実装。
  - SSRF 対策: URL スキーム検証、リダイレクト時の検査ハンドラ、プライベートアドレス判定（IP/ホスト名の DNS 解決とアドレス判定）を導入。
  - 記事 ID を URL 正規化（トラッキングパラメータ除去、クエリソート）後に SHA-256 の先頭32文字で生成し冪等性を担保。
  - テキスト前処理（URL除去、空白正規化）と銘柄コード抽出（4桁数字の検出と known_codes によるフィルタ）を実装。
  - DB への保存はチャンク化・トランザクションで実行し、INSERT ... RETURNING を使って実際に挿入された件数を正確に返却。
  - run_news_collection により複数ソースを独立して収集し、エラーが発生しても他ソースの処理を継続する堅牢なジョブを提供。
- Data 層: DuckDB スキーマ (src/kabusys/data/schema.py)
  - Raw レイヤー用テーブル定義（raw_prices, raw_financials, raw_news, raw_executions 等）を DDL 文字列で定義。初期化時に利用可能な設計を含む。
  - 各テーブルに適切な型・制約（NOT NULL、PRIMARY KEY、CHECK）を設定し、データ整合性を確保。
- Research 層: ファクター計算・解析 (src/kabusys/research/*.py)
  - feature_exploration:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB 上で一クエリで効率的に計算。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を、欠損や ties を考慮して計算。
    - rank: 同順位は平均ランクにする実装。丸め誤差対策として round(..., 12) を使用。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算する集計ユーティリティ。
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB ウィンドウ関数で計算（スキャンレンジのバッファを設けて営業日ギャップを吸収）。
    - calc_volatility: ATR(20) / atr_pct / avg_turnover / volume_ratio を計算。true_range の NULL 伝播を厳密に扱い、部分窓の場合の扱いを定義。
    - calc_value: raw_financials と prices_daily を結合して PER（EPSが0/欠損なら None）や ROE を計算。最新の target_date 以前の財務レコードを銘柄ごとに取得。
  - research パッケージの __init__ で主要関数群をエクスポート（zscore_normalize を含む）。
- その他ユーティリティ
  - ロギング呼び出しを随所に配置し、処理件数や警告・例外発生時に詳しい情報を出力する設計。

### Changed
- 初期リリースのため該当なし（新機能追加が主体）。

### Fixed
- 初期リリースのため該当なし（バグ修正は将来のリリースで記載）。

### Security
- ニュース収集での XML 関連攻撃対策に defusedxml を使用。
- RSS フェッチ時の SSRF 対策（スキーム検証、プライベートIP判定、リダイレクト検査）を実装。
- J-Quants クライアントはトークン管理と再取得処理を厳密に実装し、不正な認証状態に対して安全に対処するよう設計。

---

開発者向けノート（コードからの推測）
- DB 操作は DuckDB を前提としているため、初期化処理や接続管理ユーティリティが別途存在する可能性が高い（schema の DDL を用いた初期化等）。
- Strategy / Execution / Monitoring の各サブパッケージの中身はこのスナップショットでは最小限（もしくは未実装）に見えるが、research と data 周りは比較的完成度が高い。
- 今後のリリースでは tests、CLI、運用用ジョブ（cron/スケジューラ）や CI 用設定、詳細なドキュメント（StrategyModel.md, DataPlatform.md 等の参照資料）を追記すると良い。

（必要であれば、各ファイルごとのより詳細な変更点や挙動の注意点、サンプル設定例 (.env.example) なども追記できます。）
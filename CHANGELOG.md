CHANGELOG
=========
すべての重要な変更点を保持するため、Keep a Changelog の記法に準拠しています。  
フォーマット: https://keepachangelog.com/（日本語訳）に基づく簡潔な要約です。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-18
-------------------

Added
- 初期リリース。パッケージ名: kabusys、バージョン 0.1.0 を公開。
- パッケージ公開情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュール __all__ = ["data", "strategy", "execution", "monitoring"] を定義。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数からの設定自動読み込み機能を実装。
  - プロジェクトルート検出ロジック (_find_project_root): .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env パース機能: コメントや export 形式、シングル/ダブルクォート内のエスケープ対応を含む堅牢な _parse_env_line を実装。
  - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり）。
  - Settings クラス: J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル検証などのプロパティを提供。必須変数未設定時は明確なエラーを投げる。
- データ取得・保存（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - 固定間隔スロットリングによるレート制御（120 req/min）を実装（内部 RateLimiter）。
    - 再試行（指数バックオフ、最大 3 回）、408/429/5xx を対象。429 の場合は Retry-After ヘッダを優先する挙動。
    - 401 レスポンス時はリフレッシュトークンによる自動トークン更新を1回試行する保護付き実装。
    - ページネーション対応のフェッチ関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE により重複を排除。
    - 型変換ユーティリティ _to_float / _to_int を用意し、不正フォーマットを安全に扱う。
  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィード取得、前処理、DuckDB への冪等保存ワークフローを実装（DEFAULT_RSS_SOURCES を定義）。
    - セキュリティ対策: defusedxml を利用した XML パース、SSRF 対策（リダイレクト先のスキーム/プライベートIP検査）、URL スキーム検証。
    - メモリ DoS 対策: レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後サイズ検査。
    - URL 正規化（トラッキングパラメータ除去）、記事ID は正規化 URL の SHA-256（先頭32文字）で生成。
    - テキスト前処理: URL 除去、空白正規化。
    - DB 保存: チャンク分割による INSERT ... RETURNING を用いた新規挿入ID取得、トランザクション管理（コミット/ロールバック）。
    - 銘柄コード抽出ユーティリティ（4桁数字の抽出と known_codes フィルタ）。
    - 全ソース一括収集ジョブ run_news_collection を実装（個別ソースの例外は他ソースに影響させない）。
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw レイヤーの DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等の CREATE TABLE 文）。
  - スキーマ初期化用途のモジュール化（DataSchema.md に基づくレイヤ分割の設計に準拠）。
- 研究（Research）モジュール（src/kabusys/research）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL 一括取得による効率化）。
    - スピアマンランク相関に基づく IC 計算 calc_ic（欠損値・finite チェック、最小サンプル数チェック）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、浮動小数の丸め処理で ties を安定化）。
    - factor_summary（count/mean/std/min/max/median を計算）。
    - 設計上、外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum, Volatility, Value などの定量ファクターを DuckDB の prices_daily / raw_financials テーブルから計算する関数群を提供:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日平均乖離、データ不足時 None）。
      - calc_volatility: atr_20（20日 ATR、true range の NULL 伝播制御）、atr_pct、avg_turnover、volume_ratio。
      - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し per / roe を計算（EPS=0 や欠損時は None）。
    - スキャン範囲のバッファやウィンドウ要件（ATR/MOV/MAs）を明記して効率を配慮。
  - research パッケージの __all__ を通じて主要関数をエクスポート（calc_momentum 等と zscore_normalize の連携を想定）。
- 研究/データ連携
  - duckdb 接続を受け取り SQL と Python を組み合わせた実装で、実運用の DB/外部 API に直接アクセスしない（Look-ahead 回避の方針）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS/HTTP 関連で複数のセキュリティ対策を実装:
  - defusedxml を用いた XML パース（XML Bomb 対策）。
  - SSRF 対策: リダイレクト先のスキーム・ホスト検査、IP のプライベート判定。
  - レスポンスサイズ制限・gzip 解凍後のチェックによるメモリ DoS 緩和。
- J-Quants API クライアントは 401 の取り扱いに注意し、無限再帰を避けつつトークンを自動更新する実装になっている。

Notes / Known limitations
- research モジュールは標準ライブラリのみで実装しているため、大規模データ処理において pandas 等の高速化手段は未導入。
- strategy/execution/monitoring パッケージはパッケージエントリを用意しているが、具体的な発注ロジックや監視機能はこのバージョンでは実装が薄い（雛形）。
- schema.py の raw_executions テーブル定義はファイル末尾で継続を想定するが、リリース時点のDDLは必要箇所のみ提供。
- DuckDB に依存する部分はローカルデータベースの存在や権限に依存するため、初期化手順やマイグレーションは別ドキュメントを参照する必要あり。

開発者向け補足
- 環境変数の自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストでの isolation に有用）。
- jquants_client のトークン取得は settings.jquants_refresh_token を使用するため、テストでは get_id_token をモックすることを推奨します。
- news_collector._urlopen をモックすることで HTTP 層のテストが容易になります。

--- 
（この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴・リリース手順に基づいて適宜調整してください。）
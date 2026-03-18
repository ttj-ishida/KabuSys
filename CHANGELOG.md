CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。
リリースはセマンティックバージョニングに従います。

0.1.0 - 2026-03-18
-----------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本モジュールを実装。
- パッケージ初期化:
  - src/kabusys/__init__.py によりパッケージ名とバージョンを定義。公開 API: data, strategy, execution, monitoring。
- 設定管理:
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートは .git / pyproject.toml で検出）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env の行パースを強化（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの制御などに対応）。
    - 環境変数取得用ユーティリティ Settings を提供。必須変数取得時は未設定で ValueError を送出。
    - 設定検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）のバリデーションを実装。
    - 便利プロパティ: is_live / is_paper / is_dev。
- Data 層（DuckDB 関連）:
  - src/kabusys/data/schema.py
    - DuckDB 用スキーマ定義（Raw レイヤーのテーブル DDL を実装: raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。
    - スキーマ初期化用モジュールとして設計（DDL の管理と初期化に使用）。
- J-Quants API クライアント:
  - src/kabusys/data/jquants_client.py
    - J-Quants API からデータ取得（株価日足、財務データ、マーケットカレンダー）のクライアント関数を実装。
    - レート制限管理（固定間隔スロットリングで 120 req/min を遵守する RateLimiter）。
    - リトライロジック（指数バックオフ、最大試行回数 3、対象ステータス 408/429 と 5xx）、かつ 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時はリフレッシュトークンで id_token を自動更新し 1 回リトライ（無限再帰防止）。
    - ページネーション対応で全ページを取得。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等性を確保。
    - 型変換ユーティリティ _to_float / _to_int を追加（不正値や空値を安全に None に変換、int 変換の厳密処理）。
- ニュース収集:
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集し raw_news に保存するモジュールを実装。
    - セキュリティ対策: defusedxml を利用した XML パース、SSRF 対策（リダイレクト検査・ホストがプライベートか判定）、許可スキームは http/https のみ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）や Gzip 解凍後サイズ検査を実装し、Gzip Bomb / メモリ DoS を緩和。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト正規化、フラグメント削除）と、正規化 URL の SHA-256 ハッシュ先頭 32 文字を記事 ID として採用し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）を実装。
    - DB 保存はチャンク化して 1 トランザクションで実行し、INSERT ... RETURNING を使って実際に挿入された ID/件数を正確に返す（重複は ON CONFLICT でスキップ）。
    - 銘柄コード抽出ロジック（正規表現で 4 桁数字を抽出し known_codes でフィルタ）と、news_symbols テーブルへの紐付けバルク保存を実装。
    - デフォルト RSS ソースとして Yahoo Finance のビジネス RSS を定義。
- Research（特徴量・因子計算）:
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズンをまとめて1クエリで取得、欠損は None）。
    - スピアマンランク相関による IC 計算 calc_ic（欠損値除外、有効レコード < 3 の場合は None）。
    - ランク関数 rank（同順位は平均ランク、丸めによる ties 検出漏れ対策で round(v, 12) を使用）。
    - ファクター統計量要約 factor_summary（count/mean/std/min/max/median 計算、None 除外）。
  - src/kabusys/research/factor_research.py
    - モメンタムファクター calc_momentum（1M/3M/6M リターン、MA200 乖離率、データ不足は None）。
    - ボラティリティ/流動性 calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）。
    - バリューファクター calc_value（raw_financials から最新財務データを取得し PER/ROE を計算）。
    - 各関数は DuckDB の prices_daily/raw_financials テーブルのみを参照し、本番発注 API 等にはアクセスしない設計。
  - src/kabusys/research/__init__.py により主要ユーティリティをエクスポート（calc_momentum 等、zscore_normalize の再エクスポートを含む）。
- その他モジュール:
  - 空のパッケージ初期化ファイルを配置（strategy, execution パッケージのプレースホルダ）。

Security
- news_collector と RSS フェッチ周りで SSRF 対策を多層的に実装（事前ホストチェック、リダイレクト時の検査、許可スキーム制限）。
- defusedxml を使用して XML 関連の攻撃を軽減。
- API クライアントでトークンの自動リフレッシュやリトライ制御を実装し、認証・ネットワーク障害への堅牢性を向上。

Changed
- （初版のため変更履歴はなし）

Fixed
- （初版のため修正履歴はなし）

Notes / Known limitations
- DuckDB スキーマ定義は Raw レイヤー中心に実装。Processed / Feature / Execution 層の完全な DDL は今後拡張予定。
- 外部依存の最小化設計により、Research モジュールは標準ライブラリのみで実装されているため、pandas 等の利便性は現状含まれない。
- news_collector の URL 正規化や銘柄抽出は簡便化された実装（例外的なケースは今後調整の余地あり）。
- jquants_client のレート制限は固定間隔（スロットリング）方式。将来的にトークンバケツ等の導入を検討。

Commit / release
- バージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に対応。

--- 
この CHANGELOG はコードベースから推測して作成しています。実際のコミットログやリリースノートに合わせて追記・修正してください。
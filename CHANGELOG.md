CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。
このファイルはパッケージのソースコードから推測して作成した初期の変更履歴です。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-18
------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎機能群を追加。
  - パッケージエントリポイント
    - kabusys/__init__.py にてバージョン (0.1.0) と主要サブパッケージの __all__ を定義。

  - 設定管理 (kabusys.config)
    - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
      - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
      - 読み込み優先順位: OS環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは以下に対応:
      - コメント行・空行の無視、export KEY=val 形式、クォート文字とバックスラッシュエスケープ処理、インラインコメントの取り扱い。
    - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境種別・ログレベル等のプロパティを安全に取得。
      - 必須環境変数未設定時は ValueError を送出。
      - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装（許容値制約）。
      - パス系は pathlib.Path を返却（expanduser 対応）。

  - Data モジュール
    - J-Quants クライアント (kabusys.data.jquants_client)
      - API レート制御: 固定間隔スロットリング（120 req/min）を実装する RateLimiter を導入。
      - リクエストのリトライロジック（指数バックオフ、最大3回）。408/429/5xx 系をリトライ対象に。
      - 401 (Unauthorized) 受信時に自動でリフレッシュトークンを使ってトークンを更新し 1 回リトライ。
      - ページネーション対応の fetch_* 関数:
        - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
      - DuckDB への保存関数（冪等性を考慮、ON CONFLICT DO UPDATE を使用）:
        - save_daily_quotes (raw_prices), save_financial_statements (raw_financials), save_market_calendar (market_calendar) を実装。
      - レスポンスパースと型変換ユーティリティ: _to_float, _to_int（不正値に対する安全処理）。

    - ニュース収集 (kabusys.data.news_collector)
      - RSS フィード収集と前処理パイプラインを実装。
        - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
        - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
        - テキスト前処理: URL 除去、空白正規化。
      - セキュリティ・堅牢性のための対策:
        - defusedxml による XML パース（XML Bomb 等の防御）。
        - SSRF 対策: リダイレクト時のスキーム検証とプライベートアドレス判定（DNS 解決含む）。
        - レスポンスサイズ上限 (MAX_RESPONSE_BYTES=10MB) と gzip 解凍後の再検査。
      - DB 保存:
        - save_raw_news: INSERT ... RETURNING を使いチャンク単位でトランザクション内に保存し、実際に挿入された記事 ID を返す。
        - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入（ON CONFLICT DO NOTHING）で行う。
      - 銘柄コード抽出ユーティリティ: テキストから 4 桁コードを抽出し known_codes によりフィルタ。
      - run_news_collection: 複数ソースの収集をまとめて実行、各ソースは独立して失敗をハンドル。

  - Research モジュール (kabusys.research)
    - feature_exploration:
      - calc_forward_returns: DuckDB の prices_daily から将来リターンを一括 SQL で取得（ホライズン指定可）。
      - calc_ic: ファクター値と将来リターンを code で結合し Spearman（ランク相関）を計算。データ不足・ ties 対応あり。
      - rank: 同順位は平均ランクで処理（丸め誤差対策として round(v, 12) を使用）。
      - factor_summary: 各ファクター列に対して count/mean/std/min/max/median を標準ライブラリのみで算出。
    - factor_research:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を DuckDB で計算（窓関数使用、必要データ不足時は None）。
      - calc_volatility: 20 日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出（true_range の NULL 伝播を正しく扱う）。
      - calc_value: raw_financials から最新財務を取得して PER（EPS が 0/欠損時は None）と ROE を計算。
    - research/__init__.py で主要関数をエクスポート。

  - スキーマ定義 (kabusys.data.schema)
    - DuckDB の Raw Layer 用テーブル DDL を定義 (raw_prices, raw_financials, raw_news, raw_executions の雛形を含む)。
    - DataSchema.md に基づく 3 層構造（Raw / Processed / Feature / Execution）を想定した設計。

  - パッケージ構造
    - 空のサブパッケージプレースホルダ: kabusys.execution, kabusys.strategy（将来の機能拡張用）。

Changed
- 初期リリースのため過去の変更はなし。

Fixed
- 初期リリースのためなし。

Notes / 設計上の留意点
- 外部解析ライブラリ（pandas 等）に依存せず、標準ライブラリ + duckdb で主要処理を実装しているため、軽量かつ配布しやすい設計。
- DuckDB への依存が前提（関数群は DuckDB 接続を受け取る形）。実行・テスト時は DuckDB 接続を渡す必要あり。
- .env パーサは POSIX シェル風の書式に広く対応するが、特殊ケースは想定外の動作となる可能性があるため既知の .env.example を参照して環境を準備すること。
- news_collector における SSRF 判定は DNS 解決失敗時に安全側（非プライベート）とみなす挙動を採用している点に注意。

Acknowledgements / Dependencies
- DuckDB を利用（duckdb パッケージが必要）。
- defusedxml を RSS パースに使用しセキュリティを強化。

今後の予定（想定）
- Strategy / Execution 層の実装（発注ロジック、ポジション管理、kabuステーション連携等）。
- Feature 層から Strategy へのインターフェース整備（モデル保存・ロード、バッチ処理）。
- テストカバレッジ拡充と CI パイプライン整備。

---
(注) 本 CHANGELOG は提供されたソースコードの内容から推測して自動生成した要約です。実際のコミット履歴やリリースノートと差異がある場合があります。
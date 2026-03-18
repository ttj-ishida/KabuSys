# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装しました。

### Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__）。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
  - バージョン情報を __version__ = "0.1.0" に設定。

- 設定管理
  - 環境変数/設定ロード機能を実装（kabusys.config）。
    - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env/.env.local を読み込む。
    - .env 解析機能: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 環境変数の自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
    - 必須変数取得時に未設定なら ValueError を送出する _require メソッドを提供。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェック（許容値の検証）と便利なプロパティ（is_live/is_paper/is_dev）を追加。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）や kabu API ベース URL のデフォルト値を提供。

- データ取得 / 永続化（J-Quants）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対応）。
    - 401 受信時にリフレッシュトークンから自動で id_token を再取得して 1 回だけリトライする仕組み。
    - ページネーション対応のデータ取得関数（fetch_daily_quotes, fetch_financial_statements）。
    - API 応答の JSON デコード検証とエラー報告。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE により冪等性を確保。
    - 型変換ユーティリティ _to_float / _to_int を実装し、不正データに対する寛容性を向上。

- ニュース収集（RSS）
  - RSS ベースのニュース収集モジュールを実装（kabusys.data.news_collector）。
    - defusedxml を用いた安全な XML パースで XML Bomb 等に対処。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート）と SHA-256 ハッシュ（先頭32文字）による記事 ID 生成で冪等性を保証。
    - SSRF 対策:
      - リダイレクト検査用のカスタム RedirectHandler を導入（スキーム検証、プライベート IP のブロック）。
      - フェッチ前のホスト検証と、最終リダイレクト先の検証を実施。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェックでメモリDoS対策。
    - 記事テキスト前処理（URL 除去、空白正規化）。
    - 銘柄コード抽出（4桁数字）と既知銘柄リストに基づくフィルタリング。
    - DB 保存:
      - raw_news へのチャンク INSERT + RETURNING により実際に挿入された記事 ID を取得。
      - news_symbols への紐付けをチャンク化して一括保存（ON CONFLICT DO NOTHING）し、挿入数を正確に取得。
      - トランザクション単位でのロールバック処理を実装。

- 研究用 / 特徴量
  - 研究用モジュール群（kabusys.research）を実装し、以下を提供。
    - 特徴量探索（kabusys.research.feature_exploration）
      - calc_forward_returns: target_date から複数ホライズンの将来リターンを一括 SQL で取得。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（欠損と ties を考慮）。
      - rank: 同順位は平均ランクを返すランク関数（丸めで ties 検出漏れを防止）。
      - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
      - 設計上、外部ライブラリ（pandas 等）に依存しないことを明記。
    - ファクター計算（kabusys.research.factor_research）
      - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離率（MA200）を計算。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正しく制御。
      - calc_value: raw_financials から最新財務データを取得し、PER・ROE を計算（EPS が無効な場合は None）。
      - SQL ウィンドウ関数を多用し、計算を DuckDB 側で効率的に行う設計。
    - 研究用パッケージ初期エクスポート（calc_momentum 等と zscore_normalize の re-export）。

- スキーマ / 初期化
  - DuckDB スキーマ定義モジュールを追加（kabusys.data.schema）。
    - Raw レイヤー用の DDL を含む（raw_prices, raw_financials, raw_news, raw_executions の一部など）。
    - DataLayer の多層構造（Raw / Processed / Feature / Execution）設計を明記。

- ロギング
  - 各モジュールに logger を導入し、情報/警告/例外ロギングを行うように実装。

### Performance
- データ取得/保存において以下を最適化:
  - J-Quants API のページネーションを一ループで取得（pagination_key 管理）。
  - calc_forward_returns 等では最大ホライズン + マージンでスキャン範囲を限定し、DuckDB のスキャン量を削減。
  - news_collector の DB 挿入はチャンク化して一括 INSERT、INSERT ... RETURNING で実際に挿入された件数のみを扱う。
  - raw_prices/raw_financials 保存は ON CONFLICT で UPDATE することで冪等性と不要重複の回避。

### Security
- RSS 収集で SSRF 対策を実装（リダイレクト先検証、プライベート IP の拒否、スキーム検証）。
- XML パースに defusedxml を使用して XML 関連攻撃を緩和。
- HTTP タイムアウトやレスポンスサイズ制限を導入して外部入力の DoS リスクを低減。
- 環境変数の取り扱いは OS 環境を保護する仕組み（protected set）を採用。

### Breaking Changes
- なし（初回リリース）。

### Notes / Migration
- 本バージョンを使用するために以下の環境変数が必要:
  - JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD（Settings の必須プロパティを参照）。
- DuckDB のスキーマ初期化（kabusys.data.schema の DDL 実行）を行ってから save_* 関数を利用してください。
- .env 自動ロードはデフォルトで有効です。テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

今後のリリースでは、Strategy / Execution / Monitoring の具象実装、追加のファクター・指標、テストやドキュメントの拡充、外部依存の明確化を計画しています。
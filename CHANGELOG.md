# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、本リリースはパッケージ内部のコードから推測して作成した初期の変更履歴です（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-03-18

### Added
- パッケージ初回リリース相当の機能群を追加。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0" を定義。
    - パッケージの公開 API として data / strategy / execution / monitoring を __all__ に登録。
  - 環境設定管理（kabusys.config）
    - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
      - プロジェクトルート検出: .git または pyproject.toml を基準に探索（__file__ を起点に探索するため CWD 非依存）。
      - 読み込み順序: OS環境変数 > .env.local > .env。
      - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env の独自パーサを実装（export プレフィックス対応、クォート内エスケープ、インラインコメント取り扱い等）。
    - 環境値の保護機構: .env 読み込み時に既存 OS 環境変数を保護する protected セットを導入。
    - Settings クラスを提供（プロパティで必須値を取得・検証）。
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須取得。
      - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック。
      - データベースパスのデフォルト（DUCKDB_PATH / SQLITE_PATH）の取得。
  - データ取得・保存（kabusys.data）
    - J-Quants クライアント（kabusys.data.jquants_client）
      - API 呼び出しユーティリティと高レベル関数を実装:
        - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
      - 認証トークン取得: get_id_token（リフレッシュトークンから id_token を POST）。
      - レート制限（固定間隔スロットリング）を導入（120 req/min、min interval を自動待機）。
      - リトライロジック（指数バックオフ、最大 3 回）および 401 時の自動トークンリフレッシュ処理を実装。
      - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）:
        - save_daily_quotes → raw_prices
        - save_financial_statements → raw_financials
        - save_market_calendar → market_calendar
      - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換ルール）。
    - ニュース収集モジュール（kabusys.data.news_collector）
      - RSS フィード取得（fetch_rss）と記事整形および DB 保存機能を実装:
        - RSS の XML パースに defusedxml を使用し XML 攻撃を緩和。
        - URL 正規化（トラッキングパラメータ除去）、SHA-256 ベースの記事 ID 生成（先頭32文字）。
        - SSRF 対策: URL スキーム検証のみならず、リダイレクト時にスキームとホストが許可されているか検査。
        - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
        - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING）と挿入済み ID を返す実装（INSERT ... RETURNING を用いたチャンク挿入）。
        - news_symbols（記事と銘柄の紐付け）保存ロジック（チャンク挿入、ON CONFLICT DO NOTHING、トランザクション管理）。
        - 銘柄コード抽出ユーティリティ（4桁数字パターン）と run_news_collection（複数ソースを独立処理し集約保存）。
  - Research（kabusys.research）
    - feature_exploration モジュール:
      - calc_forward_returns: 指定日から将来 N 営業日後のリターンを DuckDB の prices_daily から一度に取得する実装。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。ties（同順位）は平均ランクで処理し、データ不足時は None を返す。
      - rank ユーティリティ（同順位の平均ランク、丸めで ties 検出の安定化）。
      - factor_summary: 各カラムの count/mean/std/min/max/median を計算（None を除外）。
      - これらは外部依存ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB のみで実装される設計。
    - factor_research モジュール:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
      - calc_volatility: 20日 ATR（atr_20）、atr_pct（atr / close）、20日平均売買代金、volume_ratio を計算（NULL 伝播や不足行数の処理を慎重に行う）。
      - calc_value: raw_financials から直近の財務データを取得して per（株価/EPS）や roe を計算（EPS = 0/欠損時は None）。
      - 各関数は prices_daily / raw_financials テーブルのみを参照し、本番 API へのアクセスを行わない設計。
    - kabusys.research.__init__ で主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - スキーマ定義（kabusys.data.schema）
    - DuckDB のテーブル DDL を追加（raw layer の raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。
    - 各テーブルは主キー・CHECK・デフォルト値を設定しデータ整合性を強化。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- ニュース収集の RSS 処理で SSRF 対策を導入（スキーム検査、ホストのプライベートアドレス判定、リダイレクト先の事前検証）。
- XML パースに defusedxml を利用して XML に対する既知脆弱性を緩和。
- 外部 API 呼び出しに対して適切なリトライ・バックオフ・トークン更新ロジックを実装し、意図せぬ認証エラーや過負荷からの復旧を試みる設計。

### Notes / Implementation details
- J-Quants クライアントはモジュールローカルで id_token をキャッシュし、ページネーションや複数呼び出し間で共有する。
- API レート制限は固定間隔（スロットリング）で実装され、単純な sleep ベースで間引きを行う（120 req/min に相当）。
- DuckDB への挿入は可能な限り冪等性を確保（ON CONFLICT ... DO UPDATE / DO NOTHING を多用）。
- research モジュールはデータ分析用に標準ライブラリだけで記述されており、本番発注系 API にはアクセスしないことを明記。
- .env パーサは export キーワード、クォート内エスケープ、インラインコメントルールなどを考慮した実装で、一般的な .env の書式に堅牢に対応。

### Breaking Changes
- なし（初回リリース）。

---

今後のリリース案内（例）
- 未実装/拡張候補:
  - Feature 層（特徴量テーブル）と Execution 層の完全実装および関連モジュール（strategy/execution/monitoring）の具体的処理追加。
  - テストカバレッジの追加と CI ワークフローの整備。
  - パフォーマンス改善（DuckDB クエリ最適化、並列 fetch の導入等）。
  - より詳細なログ/メトリクス収集（Prometheus 等）や Slack 通知連携の実装。
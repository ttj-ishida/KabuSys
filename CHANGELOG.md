# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
特定のリリース日付はリポジトリの現状（初回リリース相当）を反映しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-19
初回公開リリース。日本株自動売買システム「KabuSys」の基盤部分を実装しました。主要な追加点は以下の通りです。

### Added
- パッケージ公開情報
  - パッケージルートにバージョンを定義（kabusys.__version__ = "0.1.0"）および公開 API（__all__）を設定。

- 環境設定 / ローダ
  - kabusys.config: .env/.env.local や環境変数読み込み機能を実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点）により CWD に依存しない自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env 行パーサは export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理などをサポート。
    - .env.local を .env の上に上書き（override）ロードする挙動を実装。
  - Settings クラスによる型付きアクセスを提供（J-Quants トークン、kabu API 設定、Slack トークン・チャンネル、DB パス、環境種別、ログレベルなど）。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実施。
    - is_live / is_paper / is_dev のヘルパープロパティを追加。

- データアクセス（J-Quants クライアント）
  - kabusys.data.jquants_client: J-Quants API クライアントを実装。
    - 固定間隔の RateLimiter による 120 req/min のスロットリング制御。
    - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx を再試行対象に設定。429 の場合は Retry-After を考慮。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）を実装。トークンのモジュールレベルキャッシュを保持。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）を実装。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT を用いた冪等的な upsert を行う。
    - 日付フォーマット処理や型変換ユーティリティ（_to_float, _to_int）を追加（不正値に対して安全に None を返す等）。

- ニュース収集（RSS）
  - kabusys.data.news_collector: RSS 収集/前処理/DB 保存パイプラインを実装。
    - RSS 取得（fetch_rss）:
      - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
      - リクエスト時の最大読み取りサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
      - リダイレクト時および初回 URL についてスキーム検証（http/https のみ）とプライベート IP 検出による SSRF 対策。
      - カスタム RedirectHandler によるリダイレクト前検証。
      - コンテンツ前処理（URL 除去、空白正規化）と pubDate の安全なパース。
      - URL 正規化（tracking パラメータ除去、クエリソート、fragment 削除）と SHA-256 による記事 ID 生成（先頭32文字）。
      - デフォルト RSS ソース定義（Yahoo Finance のビジネスカテゴリ等）。
    - DB 保存:
      - save_raw_news: チャンク化して INSERT ... RETURNING id を使うことで実際に挿入された記事 ID のみを返す実装。トランザクション管理（begin/commit/rollback）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（ON CONFLICT DO NOTHING + RETURNING）で実装。
    - 銘柄コード抽出: 正規表現で 4 桁の数字を抽出し、known_codes にあるもののみ返す関数 extract_stock_codes を実装。
    - run_news_collection: 複数ソースを順次処理して新規保存数を集計、ソース単位でのエラーハンドリングを行う。

- 研究用 / 特徴量
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト 1,5,21 営業日）先のリターンを一括 SQL で計算。ホライズン検証（正の整数かつ <= 252）を実装。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を実装。欠損・非有限値を除外し、有効レコードが 3 未満の場合は None を返す。
    - rank: 同順位は平均ランクを返す実装。丸め（round(v, 12)）で浮動小数の ties 検出漏れを低減。
    - factor_summary: count/mean/std/min/max/median を求める統計サマリー関数。
  - kabusys.research.factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev を DuckDB 上のウィンドウ関数で計算。200 日MA 欠如時は None を返す等の安全設計。
    - calc_volatility: ATR(20)、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range 計算で NULL 伝播を制御し欠損制約を適切に扱う。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得して PER（EPS 条件付き）と ROE を算出。ROW_NUMBER による latest_fin の取得。

- データスキーマ
  - kabusys.data.schema: DuckDB 用 DDL を実装（raw_prices, raw_financials, raw_news, raw_executions の定義を含む）。データレイヤ（Raw / Processed / Feature / Execution）設計に対応したスキーマ定義の骨組みを提供。

### Security
- news_collector: SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト先検査）、defusedxml の使用、レスポンスサイズ制限による DoS 対策を導入。
- jquants_client: トークン処理時に無限再帰を避ける設計（allow_refresh フラグ）を導入。

### Performance / Reliability
- 一括処理・チャンク化:
  - news_collector のバルク INSERT をチャンク処理して SQL パラメータ上限とパフォーマンスを配慮。
  - jquants_client のページネーション対応とモジュールレベルでのトークンキャッシュにより、効率的な API 呼び出し管理を実現。
- DuckDB へのアップサート（ON CONFLICT DO UPDATE / DO NOTHING）を多用して冪等性を確保。

### Notes
- 外部依存は最小限（標準ライブラリ中心）で実装されている箇所が多く、外部ライブラリに依存するコンポーネントは defusedxml・duckdb 等に限定されています。
- research モジュールは「本番口座・発注 API には一切アクセスしない」ことを設計方針としており、 DuckDB の prices_daily / raw_financials テーブルのみを参照します。
- 一部の DDL（raw_executions）定義はファイル末尾で途切れているため、今後のリリースで続き（残りのカラムやインデックス等）の追加を予定しています。

## 今後の予定（例）
- 実行（execution）モジュールの実装（kabu ステーション連携、注文管理、ポジション管理）。
- モニタリング・Slack 通知周りの実装拡充。
- schema の残りテーブル・インデックス・マイグレーション対応の追加。
- 単体テスト、統合テストの整備と CI パイプラインの導入。

---

（注）本CHANGELOGは提供されたソースコードから機能・挙動を推測して作成しています。実際のコミット履歴や変更履歴の管理は Git の履歴に基づいて行うことを推奨します。
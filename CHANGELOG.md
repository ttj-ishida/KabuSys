# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
リリースバージョンはパッケージ内の __version__（0.1.0）に基づき作成しています。

## [Unreleased]
（現在のリポジトリ内容は初回リリース相当の機能を含むため、Unreleased の未記載変更はありません）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買プラットフォーム KabuSys の基礎機能を実装しました。以下は、コードベースから推測できる主要な追加・設計方針・注意点の概要です。

### Added
- パッケージ基盤
  - kabusys パッケージのエントリポイントを定義（src/kabusys/__init__.py）。public なサブパッケージとして data, strategy, execution, monitoring を公開。
  - バージョン情報: 0.1.0

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出: .git / pyproject.toml 基準）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パース処理の強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行内コメントの扱い、無効行スキップ等をサポート。
  - Settings クラスを実装し、J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス（DuckDB/SQLite）、実行環境（development/paper_trading/live）やログレベルのバリデーションを提供。
  - 必須環境変数未設定時は ValueError を投げるヘルパー _require を提供。

- データ取得・保存（src/kabusys/data/）
  - J-Quants API クライアント（jquants_client.py）
    - API 呼び出しの共通処理を提供。固定間隔のレートリミッタ（120 req/min に準拠）、ページネーション対応、JSON デコード、リトライ（指数バックオフ、最大3回）を実装。
    - 401 Unauthorized 受信時は自動でリフレッシュトークン経由の id_token 再取得を行い1回だけリトライする仕組みを実装（キャッシュを保持）。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar 等の取得関数を実装。
    - DuckDB への保存用ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、冪等性を保つために ON CONFLICT DO UPDATE を使用。
    - 入出力変換ユーティリティ（_to_float, _to_int）を実装し、不正データや空値を安全に扱う。

  - ニュース収集モジュール（news_collector.py）
    - RSS フィードから記事を収集して raw_news / news_symbols へ保存するワークフローを実装。
    - セキュリティ・堅牢性対策:
      - defusedxml を用いた XML パース（XML Bomb 対策）。
      - SSRF 対策: リダイレクト先のスキーム検証、ホスト/IP がプライベート/ループバック/リンクローカルでないことの検証（DNS 解決して A/AAAA を確認）、リダイレクトハンドラ経由で事前検査。
      - URL スキームの制限（http/https のみ）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）および正規化 URL の SHA-256（先頭32文字）による記事ID生成で冪等性を確保。
      - テキスト前処理（URL 除去、空白正規化）や日時パースのフォールバック。
    - DB 保存はチャンク化・トランザクション内で実行し、INSERT ... RETURNING で実際に挿入された件数を取得。
    - 銘柄コード抽出ユーティリティ（4桁数字の検出と known_codes によるフィルタリング）を実装。
    - run_news_collection により複数ソースの独立した処理と集約をサポート。

  - DuckDB スキーマ定義（data/schema.py）
    - Raw Layer のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions 等の初期定義）。
    - DataSchema.md に基づく 3 層（Raw / Processed / Feature）構造の方針を明示。

- 研究（research）モジュール（src/kabusys/research/）
  - feature_exploration.py
    - calc_forward_returns: 指定日から n 営業日先の将来リターンを DuckDB の prices_daily テーブルを用いて一括計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。欠損や非有限値の除外、レコード数閾値（3件未満は None）に対応。
    - rank: 同順位は平均ランクで処理（丸めによる ties 検出の安定化のため round(..., 12) を利用）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出（None 値は除外）。
    - 研究モジュールは標準ライブラリのみで動作する設計（pandas などに依存しない）。
  - factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。ウィンドウ不足の際は None を返す。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。true_range の NULL 伝播に配慮。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0 または欠損の場合は None）。
  - research パッケージは data.stats.zscore_normalize など既存ユーティリティと連携するためのエクスポートを実装。

### Changed
- （初回リリースのため過去バージョンからの変更履歴は無し。ただし設計上の選択やバリデーション強化を明記）
  - env / log level のバリデーション追加により、不正な環境設定で早期にエラーが出るようになっています（KABUSYS_ENV 値チェック、LOG_LEVEL 値チェック）。
  - .env の自動ロード順序: OS 環境変数 > .env.local > .env（.env.local は既存環境変数を上書きするが OS の環境変数は保護）。

### Fixed
- （コードから明示的なバグ修正は記録されていません。実装時点での注意点を以下に記載）
  - .env パーサでクォート内のバックスラッシュエスケープや行内コメント判定を明確化しているため、従来の単純実装でのパース不整合を回避。

### Security
- ニュース収集における SSRF 対策（リダイレクト検査・ホスト/IP プライベート判定）と defusedxml による XML パース安全化を実施。
- RSS 取得時のレスポンスサイズ制限と gzip 解凍後の検査を行い、DoS / zip bomb を軽減。
- J-Quants クライアントはトークン自動リフレッシュの際の無限再帰を防ぐため allow_refresh フラグを採用。

### Notes / Migration
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings から必須取得されます。未設定時は ValueError が発生します。
- DuckDB をデータレイヤに採用しているため、実行環境に duckdb パッケージが必要です。
- news_collector の初期 DEFAULT_RSS_SOURCES は Yahoo Finance のビジネスカテゴリ RSS を含みますが、ソースは引数で拡張可能です。
- research モジュールは外部依存を避ける設計のため、pandas 等が無くても動作しますが、大量データ処理のパフォーマンス要件に応じて利用者での最適化を検討してください。
- jquants_client のレートリミットは固定間隔スロットリング実装です。高精度なスループット制御や並列呼び出しを行う場合は外部のレート制御層の導入を検討してください。

---

この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートにはコミット単位の変更点・作者・影響範囲（BREAKING CHANGES 等）を追記してください。必要であれば、各モジュールごとの公開 API（関数・クラス一覧）や利用例を追記することもできます。
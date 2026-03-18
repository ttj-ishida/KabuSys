Keep a Changelogに準拠した形式で、コードベースから推測した変更履歴を日本語で作成しました。初回公開リリース（v0.1.0）としての構成・機能が中心です。

CHANGELOG.md
=============

すべての重要な変更点をこのファイルに記載します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（互換性のある改善など）
- Fixed: バグ修正（リリース前の想定修正も含む）
- Security: セキュリティ関連の修正・強化

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース。
- 基本パッケージエントリポイント:
  - kabusys.__version__ を "0.1.0" に設定。
  - 公開モジュール: data, strategy, execution, monitoring

- 環境変数/設定管理 (kabusys.config):
  - .env ファイルまたは環境変数から設定を読み込む自動ロードを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）により CWD に依存しない読み込み。
  - .env と .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - export KEY=val、クォートされた値、インラインコメント処理などをサポートする .env パーサを実装。
  - 必須環境変数チェック用の Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - 環境（KABUSYS_ENV）とログレベルの妥当性チェック（development / paper_trading / live、DEBUG/INFO/...）。

- データ取り込み/保存関連 (kabusys.data):
  - J-Quants API クライアント (kabusys.data.jquants_client) を実装:
    - レート制限制御（120 req/min 固定間隔スロットリング）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時にリフレッシュトークンで自動的に id_token を再取得して 1 回リトライ。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar。
    - 値変換ユーティリティ: _to_float, _to_int。
    - 取得時刻(fetched_at)を UTC で記録し Look-ahead bias の追跡を可能に。

  - ニュース収集モジュール (kabusys.data.news_collector):
    - RSS フィード取得・パース・正規化・DB保存のワークフローを実装。
    - defusedxml を利用した安全な XML パース。
    - URL 正規化（トラッキングパラメータ除去、フラグメント削除、キーソート）と記事ID生成（SHA-256 の先頭32文字）。
    - SSRF 対策:
      - 初期ホスト検証、リダイレクト時のスキーム/ホスト検査を行うカスタム RedirectHandler を導入。
      - _is_private_host による IP/ホストのプライベートアドレス検出。
      - 許可スキームは http / https のみ。
    - 応答サイズ制限（MAX_RESPONSE_BYTES = 10 MiB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - テキスト前処理（URL 除去、空白正規化）。
    - 銘柄コード抽出ユーティリティ（4桁数字パターン）と既知銘柄セットによるフィルタリング。
    - DB 保存はチャンク化してトランザクションで実行し、INSERT ... RETURNING を使って実際に挿入された件数/ID を取得。
    - 全ソースからの統合収集ジョブ run_news_collection を実装（個々のソースは独立してエラー処理）。

- DuckDB スキーマ定義 (kabusys.data.schema):
  - Raw レイヤーのテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の一部を含む）。
  - Data Platform の3層（Raw/Processed/Feature）設計に基づく初期スキーマ整備の基礎を提供。

- リサーチ / ファクター計算 (kabusys.research):
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から各ホライズン先の将来リターンを DuckDB の prices_daily テーブル参照で一括計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（ランク関数を含む）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位の平均ランクを扱うランク付け実装（丸めによる ties 誤差対策あり）。
    - 実装方針として pandas 等の外部依存を避け、標準ライブラリのみで完結。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を DuckDB の prices_daily 参照で計算（ウィンドウ/遅延関数利用）。
    - calc_volatility: ATR（20日）/atr_pct/avg_turnover/volume_ratio 等を計算（true_range の NULL 伝播に配慮）。
    - calc_value: raw_financials から直近財務を取得して PER/ROE を計算（prices_daily と結合）。
    - 各関数は date, code をキーにした dict リストを返す設計。

- モジュール初期化と公開:
  - kabusys.research.__init__ で主要関数と zscore_normalize (kabusys.data.stats から) を公開。

Changed
- （初回リリースのため「変更」は限定的）設計上の明確化・安全性重視の実装（.env パーサ、HTTP リクエストの堅牢化、DuckDB への冪等保存など）。

Fixed
- （リリース前想定のハードニング）RSS の不正スキーム/不正レスポンスサイズや XML パース失敗時に安全にスキップする実装を反映。

Security
- ニュース収集での SSRF 防止:
  - リダイレクト先の事前検査、ホストのプライベートアドレス判定、許可スキーム制限を導入。
- defusedxml を使用した XML パースによる XML 関連攻撃防止。
- レート制限の遵守とリトライによる API 側との安全な通信。

Notes / Migration
- DuckDB のスキーマは初期状態のみ提供。運用前に必要なテーブル（processed/feature/execution 層など）の DDL を schema モジュールに追加してください（raw の一部のみが現在定義済）。
- 環境変数に必須項目があるため、.env.example を参考に .env を作成してください。必須の未設定は Settings プロパティで ValueError を投げます。
- J-Quants トークン周りはモジュールレベルでキャッシュされます。テスト時など自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

Acknowledgements
- 本パッケージは外部依存（pandas 等）を可能な限り排除し、標準ライブラリ＋duckdb を中心に実装されています。将来の拡張で CSV/Parquet I/O、並列化、外部 ML ライブラリの導入を検討できます。

----
必要であれば、個々の関数/モジュールごとの簡易使用例（API 参照サンプル）や、今後のロードマップ（次バージョンでの追加予定機能）も追記できます。どの情報を追加しますか？
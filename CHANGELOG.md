CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- セキュリティ (Security)
- 破壊的変更 (Removed / Deprecated) — 必要に応じて記載

Unreleased
----------

- 今後の変更予定を記載するセクションです。

0.1.0 - 2026-03-18
------------------

Added
- 初回リリース。以下の主要コンポーネントを実装。
  - パッケージ初期化
    - kabusys パッケージを導入。__version__ = 0.1.0。
  - 環境/設定管理 (kabusys.config)
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - プロジェクトルートの検出 (pyproject.toml または .git) を実装し、CWD 非依存で .env を検索。
    - .env パーサを厳密に実装（export 形式対応、クォート処理、インラインコメント処理）。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の設定をプロパティ経由で取得。値検証（env 値・ログレベル）を実施。
  - データ取得 & 永続化 (kabusys.data)
    - J-Quants API クライアント (jquants_client)
      - レート制御（120 req/min）を固定間隔スロットリングで実装。
      - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
      - 401 受信時のトークン自動リフレッシュ（1 回）と、モジュールレベルのトークンキャッシュ。
      - ページネーション対応の取得関数（株価/財務/カレンダー）。
      - DuckDB への冪等保存関数を実装（raw_prices / raw_financials / market_calendar 等、ON CONFLICT で更新）。
      - 型変換ユーティリティ (_to_float / _to_int) を実装し、不正値を None に落とす挙動を明確化。
    - ニュース収集モジュール (news_collector)
      - RSS フィードを取得して raw_news テーブルへ冪等保存する処理を実装。
      - URL 正規化（tracking パラメータ削除・ソート・スキーム小文字化・フラグメント除去）と記事 ID（SHA-256 先頭32文字）生成。
      - defusedxml を使った XML パース（XML Bomb 等に備えた防御）。
      - SSRF 対策: URL スキーム検証、リダイレクト先のプライベートアドレス検査、独自の redirect handler による事前検査。
      - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10 MB）、gzip 解凍後の再チェック（Gzip bomb 対策）。
      - テキスト前処理ユーティリティ（URL 除去、空白正規化）。
      - 銘柄コード抽出ロジック（4桁数字・重複除去）と news_symbols への紐付けを一括挿入する仕組み。
      - DB への挿入はチャンク化およびトランザクションで実施し、INSERT ... RETURNING を用いて実際に挿入された件数を返す。
    - スキーマ定義 (schema)
      - DuckDB 用のテーブル定義（Raw Layer 等）を DDL 文字列として実装。raw_prices/raw_financials/raw_news/raw_executions 等の基礎スキーマを提供。
  - 研究用モジュール (kabusys.research)
    - feature_exploration
      - calc_forward_returns: 指定日から複数ホライズンの将来リターンを DuckDB の prices_daily テーブルから一括取得。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足や ties を考慮。
      - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めにより ties 検出漏れを低減）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計サマリ関数。
    - factor_research
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を DuckDB の prices_daily で計算（ウィンドウ関数利用）。
      - calc_volatility: 20日 ATR（true_range を正しく扱う）、相対 ATR、20日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（target_date 以前の最新財務レコードを使用）。
    - research パッケージ __all__ を通じて主要関数を公開（zscore_normalize を data.stats から再エクスポート）。
  - ロギング
    - 各モジュールで詳細なログ（info/warning/debug）を出力する実装。失敗時は logger.exception を適切に使用。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集に対する複数の安全対策を導入。
  - defusedxml による XML パース（安全なパーサ使用）。
  - SSRF 対策（スキーム検証、プライベートアドレス判定、リダイレクト検査）。
  - レスポンス読み取り上限（メモリ DoS / Gzip bomb 対策）。
- J-Quants クライアントにおける 401 リフレッシュ処理により、資格情報更新の扱いを明確化。

Removed / Deprecated
- （初回リリースのため該当なし）

注意事項 / マイグレーション
- settings により必須の環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）が要求されます。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化してください。
- research モジュールは設計上「DuckDB の prices_daily/raw_financials テーブルのみ」を参照し、本番発注 API 等にはアクセスしません。研究目的での利用を想定しています。
- DuckDB スキーマは初期 DDL を提供します。既存 DB を使用する場合はスキーマ整合性に注意してください（特にカラム型と制約）。

既知の制約
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指しているため、巨大データの集計でパフォーマンス面のチューニングが必要になる可能性があります。
- jquants_client の再試行ロジックはネットワーク系の 408/429/5xx を対象とするため、その他の一時的な障害パターンは呼び出し元で追加制御が必要になる場合があります。

貢献・作者
- リポジトリの初期実装に基づくリリースノートです（実装責任者情報はソース内の著作表示等を参照してください）。
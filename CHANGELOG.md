CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。

[Unreleased]
------------

- 今のところ未リリースの変更はありません。

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初期リリースとして以下の主要機能を実装・公開しました。
  - 基本パッケージ情報
    - kabusys.__version__ = "0.1.0"
    - パッケージの公開 API: data, strategy, execution, monitoring を __all__ に定義。
  - 環境設定管理 (kabusys.config)
    - プロジェクトルート自動探索: .git または pyproject.toml を基準にして .env 自動読み込みを行う実装を追加。
    - .env ファイルパーサ実装: export 形式やクォートエスケープ・インラインコメントなどを考慮した堅牢なパース処理を提供。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env / .env.local の読み込み優先度と OS 環境変数保護（protected set）を実装。
    - Settings クラスを導入し、各種設定値（J-Quants トークン、kabu API、LINE トークン、DB パス、監視閾値、環境・ログレベル等）をプロパティ経由で取得。値検証（列挙可能値チェックや数値変換）を備える。
    - Paper Trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）とその他パス設定（DUCKDB_PATH/SQLITE_PATH/PID_FILE_PATH 等）のデフォルトを提供。
  - AI ユーティリティ (kabusys.ai)
    - news_nlp モジュール
      - ニュースのタイムウィンドウ計算（calc_news_window）。
      - raw_news / news_symbols から銘柄ごとに記事集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄別センチメントを ai_scores テーブルへ書き込む score_news を実装。
      - バッチ処理（最大20銘柄 / チャンク）、1銘柄あたりのトークン肥大化対策（記事数上限、文字数トリム）を実装。
      - リトライ（429/ネットワーク断/タイムアウト/5xx）用の指数バックオフと堅牢なレスポンス検証（JSON 抽出・バリデーション・スコアクリッピング）を実装。API 失敗時は該当チャンクをスキップして処理継続するフェイルセーフ設計。
    - regime_detector モジュール
      - ETF (1321) の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
      - OpenAI 呼び出し（gpt-4o-mini）を用いたマクロセンチメント評価、API リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
      - DuckDB を用いたデータ取得（prices_daily, raw_news）と market_regime へ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を提供。
  - データプラットフォーム (kabusys.data)
    - calendar_management モジュール
      - JPX カレンダー取得とマーケットカレンダー管理機能（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
      - market_calendar が欠落している場合の曜日ベースフォールバックをサポートし、最大探索範囲のガードやバックフィル・健全性チェックを実装。
      - 夜間バッチ更新ジョブ calendar_update_job により J-Quants から差分取得 → 保存（save_market_calendar 経由）を実行。
    - ETL パイプライン (pipeline)
      - ETL の差分更新・保存・品質チェックのための設計に基づくユーティリティを実装。
      - ETLResult データクラスを実装して ETL 結果（取得数/保存数/品質問題/エラー等）を構造化して返却・シリアライズ可能にした。
    - etl モジュールで ETLResult を再エクスポート。
  - research パッケージ (kabusys.research)
    - factor_research モジュール
      - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金／出来高変化率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials から計算する calc_momentum / calc_volatility / calc_value を実装。
      - データ不足時の None ハンドリングや計算対象のスキャン期間制御を実装。
    - feature_exploration モジュール
      - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
      - 外部ライブラリに依存せず、標準ライブラリのみで実装。
  - パッケージの公開シンボル
    - ai.__init__.py で score_news を公開。
    - research.__init__.py で主要関数群を再エクスポート。

Changed
- 新規初期リリースのため該当なし。

Fixed
- 初版リリースに含めた安全策・堅牢化点:
  - OpenAI API 呼び出しに対して詳細なリトライ戦略と 5xx 判定ロジックを実装し、API 失敗時に致命的な例外としない（フェイルセーフ）仕様にした。
  - DuckDB 互換性のため executemany に空リストを渡さない分岐を追加（DuckDB 0.10 の制約回避）。
  - market_calendar の NULL 値や未登録日を検出してログ出力・フォールバックする処理を追加。

Security
- セキュリティ関連:
  - OpenAI API キーや各種トークンは環境変数経由で取得。Settings は未設定時に ValueError を投げることでキーの不備を明示。
  - .env 自動ロードでは OS 環境変数を保護（上書き不可）する仕組みを導入。

Notes / Implementation details
- OpenAI モデルは現時点で gpt-4o-mini を使用し、JSON mode（response_format={"type": "json_object"}）を想定して実装しています。
- 日付処理においてはルックアヘッドバイアス防止のために datetime.today()/date.today() を直接参照しない方針を各モジュールで採用（target_date を明示的に受け取る）。
- 多くの処理は DuckDB 接続を受け取り SQL と Python を組み合わせて実装。外部発注 API や本番口座操作はこのリポジトリの研究・データ処理コンポーネントでは行わない設計です。

今後の予定（例）
- strategy / execution / monitoring パッケージの具体的実装の公開・テストカバレッジ追加。
- OpenAI 呼び出しのモック化を前提とした単体テスト整備。
- J-Quants / kabu API のクライアント実装・認証まわりの拡充。

---

注: 上記 CHANGELOG は提供されたソースコードの構成・ドキュメント文字列から推測して作成しています。実際の変更履歴やリリースノートはバージョン管理履歴（Git）やプロジェクトのリリース手順に基づいて調整してください。
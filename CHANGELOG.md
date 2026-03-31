# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-31

### Added
- 初期リリース。パッケージ名: `kabusys`、バージョン `0.1.0`。
- パッケージの公開 API（__all__）:
  - data, strategy, execution, monitoring（パッケージトップにてエクスポート）。
- 環境/設定管理（kabusys.config）
  - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサの実装: コメント/export 構文・クォート・エスケープ・インラインコメント処理に対応。
  - Settings クラスを公開（プロパティ経由で設定値取得）:
    - JQUANTS_REFRESH_TOKEN（必須）、KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（開発環境判定: development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパープロパティ: is_live, is_paper, is_dev
- AI モジュール（kabusys.ai）
  - news_nlp モジュール:
    - 公開 API: score_news(conn, target_date, api_key=None)
    - 機能:
      - ニュースの時間ウィンドウ計算（JSTベース: 前日15:00～当日08:30）。
      - raw_news と news_symbols を集約して銘柄ごとに最大記事数・最大文字数でトリム。
      - OpenAI (gpt-4o-mini) を JSON mode でバッチ（最大 20 銘柄/リクエスト）送信。
      - リトライ/バックオフ戦略（429・ネットワーク断・タイムアウト・5xx を対象、指数バックオフ）。
      - レスポンス検証（JSON 構文・"results" 配列・コード整合性・スコア数値性）。
      - スコアは ±1.0 にクリップ。成功分のみ ai_scores テーブルに冪等的に書き込み（DELETE→INSERT、トランザクション）。
      - 戦略的なフェイルセーフ: API 失敗時はスキップして他銘柄処理を継続。
  - regime_detector モジュール:
    - 公開 API: score_regime(conn, target_date, api_key=None)
    - 機能:
      - ETF 1321 の 200 日移動平均乖離（ma200_ratio）を計算。
      - マクロ経済キーワードで raw_news をフィルタしてタイトルを抽出。
      - OpenAI (gpt-4o-mini) によりマクロセンチメントを -1.0〜1.0 で評価（記事が無ければ LLM 呼び出しを行わず macro_sentiment=0.0）。
      - 重み付け合成: ma(70%) と macro(30%) を合成しレジームスコアを算出、閾値により 'bull'/'neutral'/'bear' を決定。
      - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
      - API エラー・パース失敗時は macro_sentiment=0.0 にフォールバックして継続（例外を必ずしも投げない）。
    - 注意点:
      - OpenAI API 呼び出しは内部で OpenAI クライアントを生成（api_key を引数で注入可能）。
      - テスト用に _call_openai_api をパッチ可能に設計。
- Data モジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理機能（market_calendar テーブルを想定）。
    - 営業日判定: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等保存する処理を実装（バックフィル・健全性チェック含む）。
    - DB にカレンダーが無い場合は曜日ベース（週末は非営業日）でフォールバック。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）により無限ループを回避。
  - pipeline / etl:
    - ETLResult dataclass を実装し、ETL 実行結果の構造を定義（取得件数・保存件数・品質問題・エラー一覧など）。
    - データ取得の差分計算、バックフィル（デフォルト再取得日数）や品質チェックとの連携設計を反映。
    - data.etl にて ETLResult を再エクスポート。
- Research モジュール（kabusys.research）
  - ファクター計算・特徴量探索機能を提供:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev を計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: PER, ROE を raw_financials と prices_daily から計算（最新の報告日までの財務データを使用）。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクを返すランク関数（丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - すべて DuckDB 接続を受け取り、外部 API には依存しない設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の必須項目（トークン・パスワード等）を Settings で明示し、未設定時に ValueError を送出することで秘密情報の誤設定を早期検出。

### Notes / Implementation details
- 全体設計上の共通ポリシー:
  - lookahead バイアス防止のため、各関数は内部で datetime.today()/date.today() を参照せず、必ず引数の target_date を基準に処理を行う。
  - DuckDB をデータストアとして想定（DuckDB API 型注釈を使用）。一部処理は DuckDB の executemany の挙動を考慮して空リストバインドをチェック。
  - OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を使用。レスポンスの安全なパースと復元ロジックを備える。
  - IDEMPOTENT な DB 書き込みを基本方針とし、トランザクション（BEGIN/COMMIT/ROLLBACK）および局所的 DELETE → INSERT による部分的保護を行う。
  - API 呼び出しに対してはリトライ（指数バックオフ）を導入し、致命的でないエラーはログ記録の上でフォールバックまたはスキップするフェイルセーフを採用。
  - テスト容易性: OpenAI API 呼び出し箇所を内部関数に切り出し、unit test で差し替え可能にしている。
- OpenAI モデル: gpt-4o-mini を想定（news_nlp・regime_detector 共通）。リトライ回数・バッチサイズ等はソース内定数で調整可能。
- J-Quants クライアント（kabusys.data.jquants_client）はカレンダー取得・保存などで利用することを想定（実装は外部モジュールに依存）。

---

今後のリリースでは、以下を想定しています:
- strategy / execution / monitoring の具体的な取引ロジック・発注ラッパーの実装およびドキュメント化
- テストカバレッジ向上、型注釈の拡充、CI への統合
- パフォーマンス改善（大規模データ処理時のメモリ/クエリ最適化）
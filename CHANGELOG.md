# CHANGELOG

すべての重大な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、このファイルはリポジトリ内のコードから推測して作成しています。実際のリリース日や細部は実装状況に合わせて調整してください。

## [Unreleased]

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティ群を提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。パッケージバージョンは 0.1.0。
  - パブリックモジュールエクスポート: data, strategy, execution, monitoring（__all__ 指定）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
    - プロジェクトルート検出は __file__ から親ディレクトリを探索し、.git または pyproject.toml を基準に判定するため CWD に依存しない。
  - .env パーサ実装（export prefix、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - 環境値の検証とラッパー Settings クラスを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須チェック）。
  - 各種既定値と検証:
    - KABU_API_BASE_URL のデフォルト、データベースパスのデフォルト（DUCKDB_PATH, SQLITE_PATH 等）。
    - PAPER_FILL_MODE の許容値検証（instant/partial/never/reject）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証。
  - 監視用設定（PID ファイル・kill flag・CPU/メモリ/ディスク閾値など）を提供。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news, news_symbols を読み、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信してスコアを生成。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime に変換）。
    - バッチサイズ、1銘柄あたりの記事上限、文字数トリムなどトークン肥大化対策を実装。
    - JSON Mode を利用した厳密な JSON レスポンス検証とパース・バリデーション処理を実装（未知コード無視、数値変換・クリップ）。
    - 429／接続断／タイムアウト／5xx での指数バックオフリトライ実装。失敗時は安全にスキップ（フェイルセーフ）。
    - DuckDB 互換性のための executemany 空リスト回避等の実装（部分成功時に既存スコアを保護するため、対象コードのみ DELETE → INSERT）。
    - 公開 API: score_news(conn, target_date, api_key: Optional[str]) -> 書き込み銘柄数
    - テスト容易性: _call_openai_api を unittest.mock.patch で差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からマクロキーワードでフィルタしたタイトルを抽出して LLM に送信。
    - OpenAI 呼び出しは JSON mode を利用し、リトライ戦略と 5xx 判定対応を実装。失敗時は macro_sentiment=0.0 で継続。
    - レジーム判定結果は market_regime テーブルに冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key: Optional[str]) -> 1（成功）

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を元に営業日判定、次営業日・前営業日取得、期間内営業日リスト取得、SQ 判定等を実装。
    - DB 登録がない場合は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - カレンダー夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由の差分取得と保存、バックフィル/健全性チェックを実装）。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得/保存件数、品質問題、エラー等の集約）。
    - 差分更新・backfill・品質チェックの設計方針を実装（J-Quants クライアント連携を前提）。
    - jquants_client と quality モジュールとの連携を想定したインターフェース。

- リサーチ / ファクター（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）等を DuckDB 上の prices_daily / raw_financials から計算。
    - 関数: calc_momentum, calc_volatility, calc_value（いずれも target_date を受け取り (date, code) ベースの dict リストを返す）。
    - データ不足時の None 扱いとデバッグログ。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンを受け取り一括クエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関の実装（同順位は平均ランク）。
    - ファクター統計要約（factor_summary）: count/mean/std/min/max/median を計算。
    - ランク変換ユーティリティ（rank）: 同順位処理を含む堅牢な実装。

### Changed
- （初回リリースのため既存コードの「変更」はなし。設計上の注意点をドキュメント内に明記）
  - 全体: ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照せず、外部から与えられた target_date ベースで処理する設計を採用（AI スコアリング・ファクター計算等）。
  - DuckDB への互換性対応: executemany に空リストを渡さない、list 型バインドの不安定性回避などの実装上の工夫。

### Fixed
- （該当なし：初回リリース）

### Security
- 環境変数の取り扱いに関する注意
  - API キー（OpenAI）は api_key 引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出して明示的に失敗させる設計。
  - .env ロード時、OS の既存環境変数は保護される（読み込み時 protected set を使用）。

### Notes / Implementation details
- OpenAI 連携は gpt-4o-mini を使用する想定。JSON Mode（response_format={"type": "json_object"}）で厳密な JSON 出力を期待しつつ、実装上は前後余計な文字列が混入するケースへの耐性（{} 抽出）を持たせている。
- API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx をリトライ対象とし、指数バックオフを採用。非 5xx の APIError は再試行せず安全にスキップする挙動。
- 多くの DB 書き込みは「冪等」化（既存行の DELETE → INSERT、ON CONFLICT 相当）を意識して実装されている。
- テスト容易性のため、AI モジュールの内部 API 呼び出し関数（_kabusys.ai.*._call_openai_api）はパッチ可能な設計になっている。

もしリリースノートの公開日やバージョン管理の方針（例: プレリリース・ベータ表記）を現行の運用に合わせて調整する場合は、日付・バージョン・カテゴリ分けを更新してください。
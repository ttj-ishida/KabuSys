# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
初期リリース（0.1.0）はパッケージのソースコードから推定された機能・設計・挙動に基づき記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルート: src/kabusys/__init__.py
    - __version__ = "0.1.0"
    - 公開モジュール: data, strategy, execution, monitoring（__all__）

- 環境設定管理モジュール（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み
  - 自動ロード順序:
    1. OS 環境変数
    2. プロジェクトルートの .env（override=False）
    3. プロジェクトルートの .env.local（override=True）
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動ロードをスキップ可能
  - プロジェクトルート検出: __file__ を基準に親ディレクトリから .git または pyproject.toml を探索
  - .env パーサーで下記に対応:
    - 空行・コメント行（#）のスキップ
    - export KEY=val 形式のサポート
    - シングル/ダブルクォートを含む値とバックスラッシュエスケープの処理
    - クォートなし値のインラインコメント認識（直前が空白/タブの場合のみ）
  - 環境変数の読み取りユーティリティ Settings を提供（settings インスタンス）
    - J-Quants / kabu API / Slack / DB パス等のプロパティを提供
    - 必須変数が未設定の場合は ValueError を送出する _require を実装
    - KABUSYS_ENV の値検証（development, paper_trading, live のみ許容）
    - LOG_LEVEL の値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL のみ許容）
    - duckdb/sqlite のデフォルトパスをサポート

- AI 関連モジュール（kabusys.ai）
  - news_nlp（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いてセンチメントスコアを算出
    - タイムウィンドウは JST 基準で「前日 15:00 ～ 当日 08:30」（内部は UTC に変換）
    - 1 銘柄あたり最大 10 記事、最大 3000 文字にトリム
    - 1 コールあたり最大 20 銘柄のバッチ処理（_BATCH_SIZE = 20）
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装（最大リトライ回数 _MAX_RETRIES）
    - レスポンスの堅牢なバリデーション:
      - JSON パース（前後余分テキストが混入した場合の復元ロジック含む）
      - "results" リストと各要素の code/score 検証
      - 未知コードは無視、スコアは ±1.0 にクリップ
    - DB 書き込みは部分失敗に備え、取得済みコードのみを DELETE → INSERT で置換（冪等性を考慮）
    - score_news(conn, target_date, api_key=None) を公開。戻り値は書き込んだ銘柄数
    - テスト容易性: OpenAI 呼び出し部分は内部関数を patch できるように設計

  - regime_detector（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を統合して市場レジーム（bull/neutral/bear）を日次で判定
    - ma200 のスケーリング係数や閾値:
      - _MA_SCALE = 10.0, _MA_WEIGHT = 0.7, _MACRO_WEIGHT = 0.3
      - bull 閾値 >= 0.2, bear 閾値 <= -0.2
    - マクロ記事抽出はキーワードリスト（日本・米国系）に基づき raw_news から取得（最大 20 記事）
    - OpenAI（gpt-4o-mini）を用いた JSON レスポンスパース。API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等性を確保。書き込み失敗時は ROLLBACK を試行して例外を再送出
    - score_regime(conn, target_date, api_key=None) を公開。戻り値は成功で 1、キー未設定時は ValueError

- 研究（research）モジュール（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date)
      - mom_1m / mom_3m / mom_6m（営業日ベース）および ma200_dev（200 日 MA 乖離率）を計算
      - データ不足時は None を返す設計
    - calc_volatility(conn, target_date)
      - 20 日 ATR（atr_20）/ 相対 ATR（atr_pct）/ 20 日平均売買代金（avg_turnover）/ 出来高比率（volume_ratio）を計算
    - calc_value(conn, target_date)
      - raw_financials から最新財務（report_date <= target_date）を取り、PER（EPS 有効時）と ROE を算出
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None)
      - デフォルト horizons = [1,5,21]。horizons のバリデーション（正の整数かつ <= 252）
      - まとめて LEAD を用いて複数ホライズンを取得
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマン（ランク）による IC を実装。有効レコードが 3 件未満の場合は None
    - rank(values)
      - 同順位は平均ランク（ties は round(v,12) で事前丸めして安定化）
    - factor_summary(records, columns)
      - count/mean/std/min/max/median を返す
  - すべての Research 関数は DuckDB 接続を受け取り、外部 API や pandas などに依存しない実装

- データ（data）モジュール（kabusys.data）
  - calendar_management
    - 市場カレンダーの管理と営業日判定ヘルパ群:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB（market_calendar）が存在しない場合は曜日ベースでフォールバック（週末は非営業日）
    - next/prev の探索には上限 _MAX_SEARCH_DAYS（60 日）を導入し無限ループを防止
    - calendar_update_job(conn, lookahead_days=90)
      - J-Quants API（jquants_client）から差分取得して market_calendar を保存
      - バックフィル日数 _BACKFILL_DAYS（7 日）を含めて再フェッチして API 側の訂正を取り込む
      - 最終日が極端に未来（_SANITY_MAX_FUTURE_DAYS）であれば安全のためスキップ
  - pipeline / etl
    - ETLResult dataclass を定義し ETL 実行結果を収集・表現
      - target_date, fetched/saved カウント、quality_issues、errors を保持
      - has_errors / has_quality_errors プロパティを提供
      - to_dict() で品質問題の簡易表現に変換
    - ETL の設計方針:
      - 差分更新（最終取得日から未取得範囲のみ取得）
      - backfill による後出し修正吸収（デフォルト _DEFAULT_BACKFILL_DAYS = 3）
      - 品質チェック（quality モジュール）で問題を収集し、呼び出し元が判断できるようにする（Fail-Fast ではない）
      - jquants_client による保存は冪等（ON CONFLICT DO UPDATE）を前提

- その他ユーティリティ
  - data.etl で ETLResult を再エクスポート
  - research.__init__ で主要関数を再エクスポート（公開 API を整備）

### Changed
- （初回リリースのため該当なし）  

### Fixed
- （初回リリースのため該当なし）  

### Security
- 環境変数取り扱いに注意喚起:
  - 必須の API キー（OPENAI_API_KEY 等）が未設定の場合は明示的に ValueError を投げる箇所を実装（呼び出し側で安全に管理することを想定）
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストや CI での切り替えを容易にする）

### Notes / Implementation details / Migration hints
- OpenAI API（gpt-4o-mini）との統合は JSON mode（response_format={"type":"json_object"}）を利用して厳密な JSON レスポンスを期待する実装になっているが、現実のレスポンスに余分テキストが混ざる場合を想定した復元ロジックやパースフォールバックが入っている
- DuckDB を主要なデータストアとして使用する設計（関数の引数には duckdb.DuckDBPyConnection を期待）
- API の失敗やパース失敗は「継続可能なデグレード（フェイルセーフ）」として扱い、致命的でない場合はスキップして処理を続行する設計
- 各モジュールは「ルックアヘッドバイアス防止」の観点で datetime.today()/date.today() へ直接依存しないように実装（target_date を明示的に渡す方式）

---

（注）本 CHANGELOG は提示されたソースコードの内容から推定して作成したものであり、実際のリリースノートやドキュメントと差異がある可能性があります。必要であれば、リリース日や追加変更点の反映、より詳細な Breakage / Deprecation 情報の追記を行います。
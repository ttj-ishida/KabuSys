# Changelog

すべての変更は「Keep a Changelog」形式に従い、セマンティックバージョニングを使用しています。  

## [0.1.0] - 2026-04-04

初回リリース — 日本株自動売買/リサーチ/データ基盤ライブラリの基本機能を実装。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装（export プレフィックス、引用符内のエスケープ、インラインコメントの取り扱いなどに対応）。
  - Settings クラスを導入し、各種設定プロパティを環境変数から取得:
    - J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供。
    - 必須値取得時のエラー（_require）や値検証（env, log_level の許容値検査）を実装。
    - Path 型でのデフォルトパス（例: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH など）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news + news_symbols を元に、銘柄ごとに記事を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄別 sentiment/ai_score を ai_scores テーブルへ書き込み。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window 関数で提供。DB 比較は UTC naive datetime を使用。
    - バッチ処理（最大 20 銘柄/回）、記事トリム（最大記事数・最大文字数）を実装。
    - OpenAI 呼び出しは JSON Mode を利用し、レスポンスのバリデーション／抽出ロジックを実装（レスポンスの前後余計な文字を許容する復元処理含む）。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他はスキップして処理継続（フェイルセーフ）。
    - DuckDB に対して冪等保存（対象コードのみ DELETE → INSERT）を行い、部分失敗時に既存スコアを保護。
    - テスト容易性: OpenAI 呼び出し部分は置き換え可能に設計（_call_openai_api が差し替え可能）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - マクロ記事の抽出はニュース NLP の窓計算を再利用（calc_news_window）。
    - OpenAI 呼び出し（gpt-4o-mini, JSON Mode）およびリトライロジック、API エラー時のフォールバック（macro_sentiment=0.0）を実装。
    - レジーム算出後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策: datetime.today() / date.today() を参照せず、prices_daily クエリは target_date 未満を使用。

- データ基盤 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装（J-Quants から差分取得 → 保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。DB 未取得日の曜日フォールバックロジックを含む。
    - 最大探索範囲や健全性チェック、バックフィル日数などの安全策を実装。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを追加（ETL 実行結果の集計・シリアライズ機能）。
    - 差分取得、保存（jquants_client の save_* を使用して冪等保存）、品質チェックを行う設計方針を実装。
    - デフォルトのバックフィルやカレンダー先読み等の設定を導入。
  - jquants_client / quality などのクライアント層と連携する設計（実装は別モジュール想定）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR / 相対 ATR）、流動性（20 日平均売買代金・出来高比）およびバリュー（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL とウィンドウ関数を用いて効率的に計算。データ不足時の None 扱いを明示。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランキング関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を避け、標準ライブラリのみで統計処理を実装。
  - data.stats の zscore_normalize を再エクスポート。

### Changed
- 初回実装のため「変更」はなし（初出）。

### Fixed
- 初回実装のため「修正」はなし。

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY から解決。未設定時は明示的に ValueError を投げ、誤った動作を避ける。

### Notes / 実装上の重要点
- ルックアヘッドバイアス対策として、全てのスコアリング / レジーム判定 / ファクター計算関数は内部で現在時刻を参照せず、必ず caller が与える target_date に基づいて処理します。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なバリデーション（JSON 抽出、キー検証、型チェック）を行います。API エラー時は部分的にフォールバックし、例外を投げずに処理継続する箇所が多く存在します（フェイルセーフ設計）。
- DuckDB を用いた DB 操作は冪等性を重視（DELETE → INSERT、ON CONFLICT 相当）しており、部分失敗による既存データの喪失を避ける設計になっています。
- テスト容易性を意識して、外部 API 呼び出し箇所（OpenAI 呼び出し関数など）を差し替え可能に実装しています（unittest.mock.patch 等でのモックが可能）。

### Backwards incompatible changes
- 初回リリースのため該当なし。

--- 

今後のリリースでは、発注（execution）やモニタリング関連の実装拡充、性能チューニング、さらに詳細な品質チェックレポート出力などを予定しています。
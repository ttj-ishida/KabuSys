# CHANGELOG

すべての主な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠とし、セマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-03

### Added
- パッケージ初期リリース。パッケージ名: kabusys, バージョン: 0.1.0。
- 基本パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ情報と __version__ を定義。
  - __all__ に data, strategy, execution, monitoring を公開予定 API として設定。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイル（.env / .env.local）およびOS環境変数から設定を自動読み込みする実装を追加。
    - プロジェクトルートの検出（.git または pyproject.toml を基準）により、CWD に依存しない自動読み込み。
    - export KEY=val 形式、クォート付き／クォートなし、インラインコメント等に耐える .env パーサを実装。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / データベース / 監視 / システム関連の設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL 等）を公開。値検証（有効な env 値や log level の検査）を実装。
    - 必須環境変数未設定時は ValueError を送出する _require() を提供。

- AI（LLM）関連
  - src/kabusys/ai/news_nlp.py
    - ニュース記事群を銘柄ごとに集約し、OpenAI（gpt-4o-mini）に JSON Mode でバッチ送信してセンチメント（ai_score）を算出、ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ定義（前日 15:00 JST～当日 08:30 JST を UTC に変換）を提供（calc_news_window）。
    - バッチサイズ、最大記事数/文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx の指数バックオフ）を実装。
    - レスポンスの厳格なバリデーションと ±1.0 のクリッピングを実装。部分成功時に既存データを保護するため書き込みは取得済み銘柄のみ DELETE→INSERT する冪等方式。
    - テスト用に内部の _call_openai_api を差し替え可能（mock を想定）。
  - src/kabusys/ai/regime_detector.py
    - ETF (1321) の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルに冪等書き込みする機能を実装。
    - マクロニュース抽出のキーワードリストを実装、最大記事数上限、LLM の呼び出しとリトライ／エラー時のフェイルセーフ（macro_sentiment=0.0）。
    - ルックアヘッドバイアス防止を重視（価格・ニュース取得は target_date 未満のみ使用、datetime.today() を参照しない）。
    - OpenAI クライアント生成時に api_key を引数で注入可能。API 呼び出し失敗時も安全に継続する設計。

- データ関連
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の関数群を提供。market_calendar が無い場合は曜日ベースでフォールバック。
    - calendar_update_job を実装し、J-Quants クライアントから差分取得して冪等に保存（バックフィル、健全性チェック含む）。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの骨格を実装。差分取得、保存（jquants_client 経由の冪等保存）、品質チェック（quality モジュール）を想定した設計。
    - ETLResult dataclass（結果集約）を実装（to_dict により品質問題を辞書化）。
    - DuckDB 固有の注意点（executemany に空リスト渡せない点など）に対応する実装を含む。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

- リサーチ（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB クエリで計算する関数群（calc_momentum, calc_volatility, calc_value）を追加。データ不足時の None 扱い、結果は辞書リストとして返す。
  - src/kabusys/research/feature_exploration.py
    - 将来リターンの計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。外部依存を持たない純粋 Python 実装。Spearman（ランク相関）をランク平均処理で正確に算出。

- 研究用公開API整理
  - src/kabusys/research/__init__.py に主要関数をまとめて再エクスポート。

- テスト性・ロバストネス
  - OpenAI 呼び出しのラッパー関数をモジュール内で独立して実装し、テスト時に patch できるように設計。
  - DuckDB クエリ・トランザクションは BEGIN/DELETE/INSERT/COMMIT の冪等パターンを採用。例外時は ROLLBACK を試行し、ROLLBACK 失敗はログに記録して上位へ伝搬。
  - Lookahead バイアス回避（target_date 未満条件の厳守）やタイムウィンドウの UTC/日本時間整合を明示。

### Changed
- 新規リリースのため該当なし

### Fixed
- 新規リリースのため該当なし

### Security
- 環境変数の自動ロード時、既存の OS 環境変数は protected として上書きされないように設計（.env の override 処理と protected キー機構）。
- OpenAI API キーは明示的に引数で注入可能。未設定時は ValueError を送出して安全に検知できる。

### Notes / 既知の挙動・制約
- DuckDB に依存する実装が多く、DuckDB のバージョン差異（特に executemany に関する仕様）を考慮したワークアラウンドを含む。
- OpenAI のレスポンスは JSON Mode を期待するが、稀に前後余計なテキストが含まれる可能性を考慮して最外の JSON 部分を抽出する耐性を持つ。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api を持ち、モジュール間でプライベート関数を共有しない設計（結合度低減）。
- 日時の扱いはすべて date / naive UTC datetime を使用し、タイムゾーン混入を避ける方針。ニュースウィンドウ等は JST ベースの定義を内部で UTC に変換して DB クエリに利用する。
- API 呼び出し失敗時はフェイルセーフとしてスコアを 0.0（中立）にフォールバックする箇所がある（部分的な情報欠落時に処理継続するため）。
- 本バージョンは「データ取得・処理・解析」コアロジックを主に実装しており、実際の発注（execution）やモニタリング用の永続プロセス制御等は別モジュール（execution, monitoring）での実装を想定。パッケージ __all__ にこれらを含めているが、今回のリリースでの実装状況はコードベース参照のこと。

---

（今後のリリースでは、バグ修正・パフォーマンス改善・API互換性やドキュメント追加などを順次記録します。）
# Changelog

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本リリースはパッケージ内部の初期実装に基づく変更履歴です（コードから推測して作成）。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - 読み込み順序: OS環境変数 > .env.local > .env
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD 非依存）。
    - 自動ロードの無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env のパースは export 形式、クォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants、kabuステーション、LINE、データベース、監視、システム設定等のプロパティを定義。
    - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
    - 既定値の提供（例: KABU_API_BASE_URL, DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db など）。
    - 必須設定（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定時に ValueError を投げる。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols から銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）の Chat JSON Mode を用いて銘柄ごとに -1.0〜1.0 のセンチメントスコアを付与。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、1 銘柄あたり最大記事数・文字数制限（デフォルト: 10 件、3000 文字）。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ（最大試行回数の制御）。
    - レスポンス検証: JSON パース、results 配列、code/score の存在確認、未知コードの無視、スコアの有限性チェック、±1.0 にクリップ。
    - DB への書き込みは部分的失敗を考慮した置換方式（対象コードのみ DELETE → INSERT）。DuckDB の executemany の挙動に配慮。
    - テスト用フック: OpenAI 呼び出しを差し替え可能（関数単位で patch 可能）。
    - 公開関数: score_news(conn, target_date, api_key=None) -> 書込件数を返す。
    - calc_news_window(target_date) を提供（JST ベースのニュース収集ウィンドウを UTC naive datetime で返す）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - ma200_ratio の算出（ルックアヘッドバイアス回避のため target_date 未満のみ使用、データ不足時は中立=1.0 を採用）。
    - マクロニュース取得はニュースタイトルに対するキーワードフィルタ（デフォルトキーワード群あり）。
    - OpenAI 呼び出し（gpt-4o-mini / JSON Mode）で macro_sentiment を取得。API エラー時は 0.0 をフェイルセーフに採用。
    - レジームスコア合成式と閾値（スコアを -1..1 にクリップ、閾値で bull/bear/neutral を判定）。
    - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を採用。
    - 公開関数: score_regime(conn, target_date, api_key=None) -> 1（成功）を返す。

- データ処理（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを使った営業日判定、SQ日判定、next/prev/get_trading_days の一連機能を提供。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants から差分取得して market_calendar を冪等的に更新（バックフィルや健全性チェックを実装）。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) を設けて無限ループを防止。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー等を格納）。
    - データ差分取得・保存・品質チェックの設計に対応するユーティリティを用意。
    - jquants_client（外部モジュール）を用いた fetch/save を前提とした設計。
    - デフォルトのバックフィルやカレンダー先読みなどの定数を定義（例: _DEFAULT_BACKFILL_DAYS=3, _CALENDAR_LOOKAHEAD_DAYS=90）。
    - ETLResult.to_dict() により品質問題を辞書化して出力可能。

- リサーチ機能（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m, ma200_dev を計算。データ不足時は None。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio を計算。データ不足時は None。
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせて PER, ROE を算出。最新の財務レコード取得ロジックあり。
    - 全関数は DuckDB を使った SQL ベース実装で、外部 API へのアクセスを行わないことを保証。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を計算。horizons の妥当性チェックあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。サンプル不足時は None。
    - rank(values): 同順位を平均ランクで扱うランク化ユーティリティ（丸めによる ties 回避）。
    - factor_summary(records, columns): 各ファクターの count/mean/std/min/max/median を算出。
    - 追加: kabusys.data.stats.zscore_normalize を research パッケージで再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーやその他機密情報は環境変数経由で取得する設計。必須値未設定時は早期にエラーを出す実装（安全性の向上）。

### Design / Implementation Notes（コードから読み取れる重要な設計判断）
- ルックアヘッドバイアスの防止: 各スコアリング・ファクター計算で datetime.today() / date.today() を使わず、明示的な target_date を受け取る設計。
- 冪等性: DB 書き込みは可能な限り冪等（DELETE → INSERT、ON CONFLICT など）を採用。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）の失敗時は例外でプロセスを停止させず、代替値（0.0 やスキップ）で継続する箇所が多い（運用継続性重視）。
- DuckDB 前提: 分析・ストレージは DuckDB を主要なバックエンドと想定。
- テストしやすさ: OpenAI 呼び出しを関数単位で差し替え可能にしてユニットテストでモック可能。
- ロギング: 各主要処理で詳細なログ出力（info/debug/warning）が入っており、障害解析に配慮。

### 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (OpenAI を使う処理で必要)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化

### 既知の制限 / TODO（コードから推測）
- jquants_client は外部モジュール依存で、実際の API 呼び出し実装はこの差分に含まれない（ETL や calendar_update_job が依存）。
- strategy / execution / monitoring パッケージ実装の有無はコードベース上で示唆されているが、今回提示されたファイル群に具体的な戦略・発注ロジックは含まれていない。
- 一部処理は DuckDB バージョン依存（executemany の空リスト扱いなど）に注意。

---

作成元: ソースコード内のモジュール・コメント・実装に基づく推測的 CHANGELOG。実際のリリースノートは運用上の追加情報（互換性、既知のバグ、マイグレーション手順など）を追記してください。
# Changelog

すべての注記は「Keep a Changelog」形式に準拠します。慣例に従い重要な変更点をカテゴリ別に記載しています。

全般的な方針:
- 日付はリリース日を示します。
- API の呼び出し失敗時はフェイルセーフで継続する設計が各所に導入されています（OpenAI 呼び出しのフォールバック等）。
- すべての日時計算はルックアヘッドバイアスを避けるため date / datetime の直接参照（datetime.today() 等）を避け、関数引数で基準日を受け取る設計になっています。

[0.1.0] - 2026-03-29
Added
- パッケージ初回リリース: kabusys 0.1.0
  - パッケージバージョンは src/kabusys/__init__.py にて `__version__ = "0.1.0"` を定義。
  - __all__ によりサブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定モジュール（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点にプロジェクトルートを探索する `_find_project_root()` を実装し、CWD に依存せず自動ロードが可能。
  - .env パーサ実装: `_parse_env_line()` は export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメント等に対応する堅牢なパースを実装。
  - .env 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き可）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - Settings クラスを提供（settings インスタンスを公開）:
    - J-Quants、kabuステーション、Slack、DB（DuckDB/SQLite）やシステム設定を環境変数から取得。
    - 必須項目未設定時は ValueError を送出する `_require()` 実装。
    - KABUSYS_ENV / LOG_LEVEL の検証ロジック（許容値チェック）と便利な判定プロパティ（is_live / is_paper / is_dev）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - target_date に対するニュース収集ウィンドウ計算 `calc_news_window()`（JST を考慮した UTC naive datetime を返す）。
    - raw_news と news_symbols から銘柄ごとに記事を集約する `_fetch_articles()`。
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出し、複数銘柄をチャンク（最大 _BATCH_SIZE=20）で評価する `_score_chunk()` を実装。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）や指数バックオフの実装（最大リトライ回数・待機系パラメータを定義）。
    - レスポンス検証とスコアクリップ（±1.0）を行う `_validate_and_extract()`。
    - 成果を ai_scores テーブルへ冪等（DELETE → INSERT）で書き込む公開関数 `score_news()`（API キー注入可能、未設定時は ValueError）。
    - DuckDB 特性への互換処理（executemany に空リストを渡さない等）を導入。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する `score_regime()` を実装。
    - MA200 乖離計算 `_calc_ma200_ratio()` は target_date 未満データのみ使用し、データ不足時のフォールバック（1.0）を実装。
    - マクロニュース抽出 `_fetch_macro_news()` はキーワードマッチでタイトルを取得、最大記事数を制限。
    - OpenAI 呼び出しは専用の `_call_openai_api()` と `_score_macro()`（リトライ、5xx 判定、JSON パースフォールバック）を用いて堅牢化。API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフを採用。
    - 市場レジーム結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）する。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - ボラティリティ／流動性（calc_volatility）: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。NULL 伝播に配慮した true_range 実装。
    - バリュー（calc_value）: raw_financials から直近財務を取得し PER / ROE を算出（EPS が 0 または欠損時は None）。
    - DuckDB SQL を活用した高効率実装。関数は prices_daily / raw_financials のみ参照し安全に実行。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: LEAD を利用し複数ホライズン（デフォルト [1,5,21]）のリターンを一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン（ランク相関）を実装。有効レコードが 3 未満なら None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、丸めによる ties 判定漏れ対策あり。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。

  - 再利用可能なユーティリティ: kabusys.data.stats の zscore_normalize を再公開（kabusys.research.__init__ でエクスポート）。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day など、DB 優先かつ未登録日は曜日フォールバックする一貫した営業日判定 API を実装。
    - カレンダー先読み、バックフィル、健全性チェックを含む夜間バッチ更新 `calendar_update_job()` を実装。J-Quants クライアント経由で差分取得 → 保存（冪等）を行う。
    - 最大探索日数や異常検知（未来日付の健全性チェック）により無限ループや誤った更新を防止。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入し、ETL の各種メトリクス（取得件数、保存件数、品質問題、エラー）を整形して返す仕組みを用意。
    - テーブル存在チェックや最大取得日取得ユーティリティを実装。
    - デフォルトの差分更新とバックフィル戦略をコメントで明示（_MIN_DATA_DATE / _DEFAULT_BACKFILL_DAYS 等）。
    - kabusys.data.etl から ETLResult を再エクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- OpenAI 呼び出しや JSON レスポンスパースの失敗に対するフォールバックを一貫して導入（news_nlp と regime_detector で macro_sentiment や chunk 処理が失敗しても例外を上位に投げず、ロギングして処理を継続）。
- DuckDB の executemany に対する互換性問題へ対策（空 params を渡さないガードを追加）。

Security
- 環境変数必須項目（API トークン等）は Settings で厳格にチェックし、未設定時には明確な ValueError を発生させることで誤設定を早期検出。

Notes / Implementation details
- 日時の扱い
  - ルックアヘッドバイアス防止の設計方針により、関数はすべて target_date 等を受け取り内部で現在時刻を参照しない実装。
- OpenAI
  - gpt-4o-mini を想定した JSON Mode（response_format={"type": "json_object"}）での呼び出しを行う。
  - テスト容易性のため `_call_openai_api` をモック差し替え可能にしている（ユニットテストでの置き換えを想定）。
- ロギング
  - 各処理において情報/警告/例外ログを適切に出力するようになっているため、運用時のトラブルシュートが容易。
- DuckDB
  - SQL は DuckDB を前提に最適化（ウィンドウ関数利用、executemany の扱い等）。

将来の作業候補（ドキュメント上で示唆）
- ai スコアリングやレジーム判定のパラメータ化（重み、閾値、モデル名等を環境変数や設定で上書き可能にする）。
- news_nlp のレスポンス検証をより厳密にして、部分的に有効なレスポンスを最大限活用する拡張。
- ETL 実行フロー（差分範囲算出・品質チェックの取り扱い）を公開 API として整備し、監査ログ・メトリクスを充実させる。

----- 
（初回リリース: 機能実装と基本的な堅牢化を優先。運用・拡張は次バージョンで順次追加予定）

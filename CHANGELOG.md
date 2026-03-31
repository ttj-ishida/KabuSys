Keep a Changelog に準拠した形式でこのコードベースから推測される変更履歴を日本語で作成しました。初回リリース 0.1.0 を想定し、各モジュールの追加機能・設計方針・重要な実装上の注意点を記載しています。

なお日付はコード解析時点（2026-03-31）を使用しています。必要に応じて日付や細部を調整してください。

CHANGELOG.md
============

すべての変更は "Keep a Changelog" の形式に従って記載しています。  
慣例: 重大度の高い変更は Breaking changes として明記します。

Unreleased
----------

- 今後の変更・修正をここに記載します。

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - src/kabusys/__init__.py によりサブパッケージを公開: data, strategy, execution, monitoring。
  - パッケージバージョン __version__ = "0.1.0" を設定。

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの自動検出: .git または pyproject.toml を起点に検索。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーは以下に対応:
    - コメント行と export KEY=val 形式の処理。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの取り扱い（クォート有無で異なる挙動）。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須値チェック（未設定時は ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV 等にデフォルトと検証ロジックを用意。
    - is_live / is_paper / is_dev 判定ユーティリティ。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を基に銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱う（calc_news_window 提供）。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄ずつ API へ送信し、1 銘柄ごとに最新 N 記事（_MAX_ARTICLES_PER_STOCK）・文字数制限でトリム。
    - 再試行とバックオフ: 429, ネットワーク断, タイムアウト, 5xx を対象に指数バックオフのリトライ。
    - レスポンス検証: JSON 抽出・構造検証（"results" リスト、各要素に code と score）、未知コードは無視、スコアを ±1.0 にクリップ。
    - DB 書き込みは部分成功に配慮: 成功したコードのみ DELETE → INSERT（executemany で個別 DELETE）して既存スコアを保護。
    - テスト容易性: OpenAI 呼び出しをラップする内部関数を定義し unittest.mock.patch で差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム ('bull' / 'neutral' / 'bear') を判定し market_regime テーブルへ冪等書き込み。
    - ma200_ratio は過去 200 日の終値を使用（ターゲット日未満のみを参照しルックアヘッドを防止）。データ不足時は中立値 1.0 を返す。
    - マクロニュースは news_nlp の calc_news_window を利用して取得。記事がなければ LLM 呼び出しを行わず macro_sentiment=0.0。
    - OpenAI 呼び出しは個別関数で実装し、429/ネットワーク/タイムアウト/5xx のリトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）を備える。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理、失敗時は ROLLBACK を試行して例外を上位に伝播。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー管理ロジックを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar がない場合は曜日ベース（平日のみ営業）でフォールバック。DB 登録値優先で未登録日は一貫して曜日フォールバック。
    - 夜間バッチ更新 job (calendar_update_job)：J-Quants から差分取得して market_calendar に冪等保存。バックフィル・健全性チェックを実装。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題とエラーのコレクション、to_dict）。
    - 差分更新、backfill、品質チェック（quality モジュール呼び出し）などの設計方針を実装。
    - 内部ユーティリティ: DuckDB のテーブル存在チェック、最大日付取得、トレーディングデイ調整等。
  - jquants_client 経由でのデータ取得/保存ロジックを想定した実装と連携ポイントを用意（fetch/save 関数を外部依存として利用）。

- リサーチ / ファクター (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離率）を prices_daily から計算。データ不足時は None。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。tr（true_range）計算で NULL 伝播を慎重に扱う。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - すべて DuckDB SQL を利用し、prices_daily / raw_financials のみ参照。実取引 API へのアクセスはしない設計。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons のバリデーションあり。
    - calc_ic: スピアマンのランク相関（IC）を実装。有効データ < 3 件なら None を返す。
    - rank, factor_summary: ランク変換（同順位は平均ランク）、統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリ & DuckDB で完結。

- 実装上の設計方針（横断）
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を内部処理で直接参照しない。すべて target_date ベースで処理。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT の想定）。
  - OpenAI 呼び出しは JSON mode として厳密な JSON 出力を想定しつつ、実際に余計な前後テキストが混ざるケースを復元可能に実装。
  - API 呼び出しの失敗はフェイルセーフ（スコアを 0.0 にフォールバック、処理継続）を優先。
  - テスト容易性のため内部 API 呼び出し（_call_openai_api 等）は差し替え可能に実装。
  - ロギングを多用し、警告や状況説明のログ出力を充実させている。

Changed
- 初回公開のため該当なし（初期追加のみ）。

Fixed
- 初回公開のため該当なし。

Deprecated
- 初回公開のため該当なし。

Removed
- 初回公開のため該当なし。

Security
- 初回公開のため該当なし。
  - 注意: OpenAI API キーや各種トークンは環境変数で管理し、Settings が必須チェックを行います。

Notes / 実運用での注意点
- 環境変数:
  - OpenAI API キーは OPENAI_API_KEY（または api_key 引数）で供給。未設定時は ValueError を発生させ処理を停止する箇所がある。
  - 自動 .env 読み込みは便利だが、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DuckDB バインド:
  - executemany に空リストを渡せない環境（例: DuckDB 0.10）の制約を回避するため、空チェックを行ってから executemany を呼ぶ実装。
- OpenAI 呼び出し:
  - モデルは gpt-4o-mini を想定。429 や一時的なネットワーク障害、5xx に対するリトライ実装あり。
  - レスポンスの厳密な検証とフォールバックロジックを備えているが、実データでのプロンプトチューニングやエラー時の取り扱いは運用で確認が必要。

Acknowledgments / 参考
- データ取得ポイントとして J-Quants API を想定（jquants_client を参照）。
- DuckDB をデータレイヤーに使用。

-- end of CHANGELOG --
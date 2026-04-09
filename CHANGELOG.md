CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、安定したリリースごとに変更点を記載します。

[Unreleased]
-------------

- （現時点のコードでは未リリース。次回リリースに向けてここに差分を記載します）

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージのエントリポイント: src/kabusys/__init__.py にてバージョンと主要サブパッケージを公開。
- 環境設定/自動 .env ローダーを実装 (src/kabusys/config.py)
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - export 形式やシングル/ダブルクォート、エスケープ、インラインコメントなどを考慮した堅牢な .env 行パーサ実装。
  - OS 環境変数の保護（protected set）や override オプション対応。
  - 設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）の取得用 Settings クラスを提供。値検証（PAPER_FILL_MODE や KABUSYS_ENV, LOG_LEVEL の許容値チェック）を追加。
  - デフォルトデータベースパス（duckdb/sqlite）や監視用パス（PID/kill flag）等の設定プロパティを提供。
- ニュースNLP（AI）モジュールを追加 (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
  - JSTベースのニュース収集ウィンドウ（前日15:00〜当日08:30）を calc_news_window に実装。DuckDB 比較用に UTC naive datetime を返す。
  - チャンク（最大20銘柄）・記事数/文字数のトリム（銘柄あたり最大10記事・3000文字）・JSON Mode を活用した応答パースを実装。
  - レート制限/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライ、及びフェイルセーフ（失敗時は該当チャンクをスキップ）を実装。
  - レスポンスの堅牢なバリデーション（JSON抽出、resultsリスト、コード照合、数値チェック、スコアクリップ ±1.0）。
  - DuckDB 0.10 の制約に配慮し、空パラメータチェック後に executemany を実行する安全な DB 書き込みロジックを採用（DELETE→INSERT の置換方式）。
- 市場レジーム判定モジュールを追加 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
  - マクロ記事抽出は news_nlp.calc_news_window を利用し、キーワードベースで最大20件取得。
  - OpenAI 呼び出しは JSON Mode を使い、リトライ・5xx 判定・フェイルセーフ（API失敗時は macro_sentiment=0.0）を実装。
  - ルックアヘッドバイアス対策: date 引数に基づいた半開区間でのクエリ、datetime.today()/date.today() を参照しない設計。
- Research（ファクター・特徴量解析）モジュールを追加 (src/kabusys/research/)
  - calc_momentum: 1M/3M/6M リターン、200日MA乖離（ma200_dev）を DuckDB 上で計算。データ不足時は None を返す仕様。
  - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金(avg_turnover)、出来高倍率(volume_ratio) を実装。NULL の伝播制御により ATR カウントを厳密に管理。
  - calc_value: raw_financials から最新の財務（EPS/ROE）を取得し PER/ROE を計算。EPS が 0/欠損の際は None。
  - calc_forward_returns: 任意ホライズン（デフォルト 1/5/21営業日）の将来リターンを一括クエリで取得。horizons 引数のバリデーションあり。
  - calc_ic, rank, factor_summary: スピアマン IC（ランク相関）、ランク付け（同順位は平均ランク）、ファクターの統計サマリーを標準ライブラリのみで実装。
  - zscore_normalize は data.stats から再エクスポート（research.__init__ で公開）。
- Data（ETL・カレンダー）モジュールを追加 (src/kabusys/data/)
  - calendar_management: market_calendar を使った営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）ロジックを実装。DB 未取得時は曜日ベースのフォールバックを採用。
  - calendar_update_job: J-Quants API からの差分取得 → 保存（jq.save_market_calendar を呼出）ルーチンを実装。バックフィル・健全性チェック（将来日異常）・ログを備える。
  - pipeline + ETLResult: ETL のインターフェースと結果集約用データクラスを実装（差分取得・保存・品質チェックの結果を保持）。
  - ETL の設計方針として id_token 注入やバックフィル日数、品質チェックの継続処理方針を反映。
  - data.etl は pipeline.ETLResult を再エクスポート。
- jquants_client / quality 等のクライアント間インターフェース（データ取得/保存/品質チェック）を利用する設計を採用（実体は外部モジュール／別ファイルで実装想定）。

Changed
- n/a （初回リリースのため変更履歴なし）

Fixed
- n/a （初回リリースのため修正履歴なし）

Security
- 環境変数読み込み時に OS 環境変数を上書きしない保護機構を導入（protected set）。自動ロードは明示フラグで無効化可能。

Notes / 実装上の重要な挙動（ドキュメント的注意点）
- OpenAI API の呼び出しは gpt-4o-mini（_MODEL）を想定しており、JSON Mode（response_format={"type": "json_object"}）を利用した厳密な JSON 出力を想定している。API 仕様の変更やキー設定がない場合は ValueError を送出する箇所あり（APIキー必須）。
- AI モジュールは API 呼び出し失敗時に例外を投げず安全側のデフォルト（macro_sentiment=0.0、チャンクのスキップ）で継続する設計になっている。
- 日付処理はルックアヘッドバイアス防止のため date 引数ベースで動作し、datetime.today()/date.today() の直接参照を避ける実装が各所で採用されている。
- DuckDB のバージョン差異（executemany の空リスト等）に配慮した互換コードを実装している。
- calendar_update_job や ETL パイプラインは外部 J-Quants クライアント（kabusys.data.jquants_client）に依存。テスト時はクライアントをモックする想定。

開発者向け補足
- テスト容易性のため、OpenAI 呼び出し部分はモジュール内部の _call_openai_api を unittest.mock.patch で差し替え可能。
- .env パースはかなり保守的に実装しているため、特殊な .env 構成を使用する場合は挙動を確認してください。

今後の予定（参考）
- モデル管理やロギングの拡張、より詳細な品質チェックルール追加、Paper Trading 用の MockBroker 実装の充実、及び監視/実行モジュールの追加（monitoring / execution） を予定。

----------------------------------------
参考: Keep a Changelog — https://keepachangelog.com/en/1.0.0/
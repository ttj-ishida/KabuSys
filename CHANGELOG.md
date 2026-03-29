CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。  
バージョン番号は PEP-0440 に従います。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-29

初回公開リリース。以下の主要機能とモジュールを導入しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。__version__ = "0.1.0"。
  - パッケージ公開用 __all__ に data/strategy/execution/monitoring を設定。

- 設定・環境変数管理
  - kabusys.config.Settings：環境変数からアプリ設定を取得する一元インターフェースを提供。
  - .env 自動読み込み機構：
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を読み込む。
    - .env.local は .env を上書き（ただし既存の OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを実装。
  - .env パーサを実装（コメント行/export プレフィックス/クォートとバックスラッシュエスケープ対応）。
  - 必須設定取得時に未設定なら ValueError を投げる `_require` を提供。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。

- データ関連（data パッケージ）
  - calendar_management：
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - calendar_update_job：J-Quants API から差分取得して冪等更新する夜間バッチ処理。
    - DB 未登録日のフォールバック（曜日ベース）、最大探索日数制限、バックフィルや健全性チェックを実装。
  - pipeline / etl：
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult、kabusys.data.etl で再公開）。
    - ETL パイプライン設計に基づく差分取得・保存・品質チェック向けユーティリティを追加。
    - DuckDB への存在チェックや最大日付取得などのユーティリティ実装。
  - jquants_client（参照実装のクライアント呼び出し箇所を準備、fetch/save の呼び出しを想定）。

- 研究（research パッケージ）
  - factor_research：
    - calc_momentum：1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility：20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value：raw_financials と prices_daily から PER、ROE を計算。
    - 計算は DuckDB SQL ウィンドウ関数を用い、結果は (date, code) をキーとした dict リストで返す。
  - feature_exploration：
    - calc_forward_returns：将来リターン（任意ホライズン）を計算。horizons 引数のバリデーションを実装。
    - calc_ic：スピアマン（ランク相関）に基づく IC 計算。十分なデータが無ければ None を返す。
    - factor_summary：カラムごとの基本統計量（count/mean/std/min/max/median）を算出。
    - rank：同順位の平均ランク付けを実装（丸めによる ties 対応）。

- AI（ai パッケージ）
  - news_nlp：
    - score_news：raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores に書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の変換）を calc_news_window で提供。
    - チャンク化（最大 20 銘柄/回）、記事トリム、レスポンス検証、スコアクリップ（±1.0）、DuckDB への部分置換（DELETE→INSERT）を実装。
    - 429/ネットワーク断/タイムアウト/5xx で指数バックオフリトライ。その他エラーはスキップして継続（フェイルセーフ）。
  - regime_detector：
    - score_regime：ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出・market_regime に保存。
    - マクロ記事抽出（マクロキーワードに基づく）と OpenAI 呼び出し、リトライ・フォールバック戦略を実装。
    - LLM が利用不可のときは macro_sentiment=0.0 で継続するフェイルセーフを装備。
  - AI モジュールは OpenAI SDK（OpenAI class）を期待。ユニットテストのために内部の _call_openai_api をモック可能。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- .env 読み込み時のファイルエラーで warnings.warn を出すようにしてプロセスを壊さない実装に修正。
- DuckDB における executemany の空リストバインド問題（DuckDB 0.10 の制約）に対応し、空リストチェックを追加してエラーを回避。

### セキュリティ (Security)
- OpenAI API キーは関数引数で注入可能（テスト容易化）かつ環境変数 OPENAI_API_KEY を利用。未設定時は明示的に ValueError を投げ、意図しないキー漏洩を防止。

### 設計上の重要な注意 / 挙動
- ルックアヘッドバイアス回避：各処理で datetime.today() / date.today() を直接参照しない設計。target_date を外部から与えることを前提としている。
- データベース書き込みはなるべく冪等性を保つ（DELETE→INSERT、ON CONFLICT を想定）。
- OpenAI 呼び出しは堅牢化（リトライ・JSON バリデーション・部分失敗時の保護）されており、API障害時もプロセス全体を停止させず継続する方針。
- news_nlp と regime_detector では内部で OpenAI を呼ぶ箇所の実装を分離し、モジュール間で private 関数を共有しないことで結合度を下げている。
- DuckDB の date 値取り扱いで互換性を意識した変換ヘルパ（_to_date）を用意。

### 既知の制約・今後の改良候補
- 一部処理は OpenAI（gpt-4o-mini）依存であり、API 仕様変更やレスポンス形式の揺らぎに脆弱になり得る（レスポンス検証は実装済みだが運用監視が必要）。
- ai モジュールは JSON mode に依存する出力を期待しているため、LLM の応答パターン変化によりパースエラーが発生する可能性がある。
- ETL の品質チェック（quality モジュール）は外部に委任される想定で、品質問題の扱いは呼び出し元に依存する設計。

---

破壊的変更 (Breaking Changes): なし（初回リリース）  

注: この CHANGELOG は、現行のコードベース（src/kabusys 配下）から推測して作成しています。運用状況や実装の追加・変更に応じて随時更新してください。
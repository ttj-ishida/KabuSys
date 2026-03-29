# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
各項目はコードベースの実装内容から推測してまとめています。

全般的な注意
- 本リリースでは DuckDB を主要なローカルデータストアとして利用し、外部依存（例: pandas）を避ける設計が取られています。
- OpenAI（gpt-4o-mini）を用いた NLP 処理を組み込み、API 呼び出しは冗長性（リトライ・バックオフ）とレスポンス検証を重視しています。
- ルックアヘッドバイアス防止のため、日付判定やウィンドウ計算は現在日時を直接参照しない設計です。
- DB 書き込みは冪等性・部分失敗耐性を考慮して実装されています（DELETE→INSERT や個別 DELETE の採用など）。

## [0.1.0] - 2026-03-29

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加: `kabusys.__version__ = "0.1.0"`、公開モジュール一覧を `__all__` に定義（data, strategy, execution, monitoring）。
- 設定・環境管理
  - `kabusys.config` モジュールを追加。
    - プロジェクトルート（.git または pyproject.toml）を基準に自動で `.env` / `.env.local` を読み込む仕組みを実装。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化をサポート（テスト用途）。
    - `.env` パーサ (`_parse_env_line`) を実装：コメント、export プレフィックス、クォートとバックスラッシュエスケープ、インラインコメントなどに対応。
    - `.env` 読み込みで既存 OS 環境変数を保護する `protected` セットを導入し、`.env.local` の上書き挙動を制御。
    - 必須環境変数取得用ヘルパ `_require` と、Settings クラスを実装（J-Quants / kabu / Slack / DB パス / env/log_level の検証付き取得）。
- AI / NLP
  - `kabusys.ai.news_nlp` を追加。
    - ニュース記事を銘柄ごとに集約して OpenAI にバッチ送信し、銘柄ごとのセンチメント（ai_score）を計算して `ai_scores` テーブルへ書き込む処理 `score_news` を実装。
    - タイムウィンドウ計算 `calc_news_window`（JST ベースの時間ウィンドウを UTC naive datetime へ変換）。
    - レスポンスの堅牢なバリデーション `_validate_and_extract`（JSON 抽出、results 構造検証、スコア数値変換、±1.0 クリップ）。
    - API 呼び出し用のリトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフを実装。
    - 1 銘柄あたりの文字数/記事数トリム（トークン肥大化対策）を導入。
  - `kabusys.ai.regime_detector` を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出する `score_regime` を実装。
    - マクロ記事抽出 `_fetch_macro_news`（キーワードマッチ）、LLM 呼び出し `_score_macro`（リトライ・フェイルセーフ、API 失敗時は macro_sentiment=0.0）を実装。
    - レジーム計算はスコアをクリップして閾値でラベル付けし、`market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
- データプラットフォーム（Data）
  - `kabusys.data.pipeline` を追加。
    - ETL 実行結果を表す dataclass `ETLResult` を公開（品質チェック結果やエラー集約を含む）。
    - データ差分取得、バックフィル、品質チェックの設計を反映（J-Quants クライアントとの連携想定）。
  - `kabusys.data.etl` で `ETLResult` を再エクスポート。
  - `kabusys.data.calendar_management` を追加。
    - JPX カレンダー管理（market_calendar）と、営業日判定ユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日非営業）でフォールバックする挙動を実装。
    - 夜間バッチの calendar_update_job を実装（J-Quants API からの差分取得、バックフィル、健全性チェック）。
- リサーチ（Research）
  - `kabusys.research` パッケージを追加し、ファクター計算・特徴量解析を提供。
  - `kabusys.research.factor_research` を実装。
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL とウィンドウ関数を駆使した実装。データ不足時の None 処理やログ出力を含む。
  - `kabusys.research.feature_exploration` を実装。
    - 将来リターン計算 calc_forward_returns（可変ホライズン、入力検証）。
    - IC（Spearman ρ）計算 calc_ic、ランク化ユーティリティ rank（同順位は平均ランク）、統計サマリー factor_summary を提供。
- その他
  - OpenAI 呼び出し箇所でテスト時に差し替え可能な内部ラッパー `_call_openai_api`（ユニットテスト容易化のため）を各モジュールに用意。
  - DuckDB の executemany に関する互換性問題（空リスト不可）を考慮して、空リストチェックを導入した上で個別 DELETE → INSERT の実装を採用（ai_scores など）。

### 変更 (Changed)
- REST/外部 API 呼び出し周りの堅牢性強化（OpenAI SDK の例外型や status_code の扱いに配慮）。
- レスポンスパースのロバスト化（JSON mode でも前後余計なテキストが混ざる場合の {} 抽出を試みる処理を導入）。
- 日付・時間処理を UTC naive / date オブジェクト中心に統一し、タイムゾーン混入を避ける設計に変更（ニュースウィンドウは JST 指定 → UTC で DB 比較）。

### 修正 (Fixed)
- OpenAI API 呼び出し失敗時のフォールバックを明確化（news_nlp: スコア未取得時は該当銘柄をスキップ、regime_detector: macro_sentiment=0.0）。
- API エラー判定の改善（APIError の status_code の有無に安全に対処）。
- DuckDB での NULL / 欠損データを正しく扱うための true_range 計算やカウント条件の修正（ボラティリティ計算）。
- market_calendar の NULL 値に対するログ出力を追加（異常検出とデバッグ性向上）。
- executemany に空パラメータを渡すと失敗する点への対処（空チェックを実装）。

### 非推奨 (Deprecated)
- なし（初版リリースのため該当なし）。

### 削除 (Removed)
- なし（初版リリースのため該当なし）。

### セキュリティ (Security)
- 環境変数読み込み時に OS 環境変数を保護する `protected` セットを導入し、誤って重要な環境変数を上書きしない挙動を確保。
- 必須トークン／パスワードは Settings のプロパティで存在チェックを行い、未設定時は明示的な例外を送出。

---

もし特定モジュールや関数に関する詳細な変更履歴（例: 引数・戻り値の仕様、ログメッセージの正確な文言、例外の型など）が必要であれば、該当箇所を指定してください。コードから推測できる実装意図に基づき、さらに細かい差分説明を作成します。
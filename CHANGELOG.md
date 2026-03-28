# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはソースコードから実装内容を推測して作成した初期のリリース履歴です。

フォーマット:
- [Unreleased] は次バージョンのためのプレースホルダです。
- 日付はリリース日を表します（ここでは検出時点の最新日を使用しています）。

## [Unreleased]
- 次のリリースに向けた未定の変更・改善点を記載します。

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装しました。主要な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージメタ情報を追加 (kabusys.__version__ = "0.1.0")。
  - パッケージ公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。
- 設定管理 (kabusys.config)
  - .env ファイルや環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数により自動読み込みを無効化可能。
    - .env と .env.local の読み込み順（OS 環境変数 > .env.local > .env）と override / protected の概念を導入。
  - .env パーサーは export 形式、クォート内のエスケープ、行末コメントなどを考慮して堅牢に実装。
  - Settings クラスを提供し、主要な設定プロパティを環境変数経由で取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH, KABUSYS_ENV, LOG_LEVEL など）。
  - 環境変数の妥当性検証（KABUSYS_ENV の許容値チェック、LOG_LEVEL のチェック）を実装。
  - settings インスタンスを公開。
- データプラットフォーム (kabusys.data)
  - ETL インターフェース: ETLResult データクラスを公開（kabusys.data.ETLResult）。
  - pipeline モジュールにて ETL の共通構造を実装（差分取得、バックフィル、品質チェック結果の集約など）。
  - market_calendar 管理：
    - 営業日判定・探索 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - calendar_update_job を実装し J-Quants からの差分取得→冪等保存（バックフィル、健全性チェック含む）を行う。
    - DB 未整備時の曜日ベースフォールバック（週末を休日と判断）を提供。
- 研究（Research）モジュール (kabusys.research)
  - ファクター計算:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離などを計算。
    - calc_value: PER / ROE を raw_financials と当日株価から計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
  - 特徴量探索:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得（複数ホライズン対応、入力検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位を平均ランクにするランク付けユーティリティ。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する統計サマリー。
  - z-score 正規化ユーティリティを data.stats から再エクスポート（kabusys.research パブリック API を構成）。
- AI（LLM）関連 (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して各銘柄ごとのニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ保存する score_news 関数を実装。
    - チャンク処理、1チャンクあたり最大銘柄数、1銘柄あたりの最大記事数/最大文字数などのトークン増大対策を実装。
    - OpenAI 呼び出しは JSON Mode を利用し、429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、code/score 検証、スコアのクリップ）を実装。
    - DuckDB の executemany の制約（空リスト不可）を回避するための保護ロジックを実装し、部分失敗時も既存スコアを保護する置換戦略（DELETE→INSERT）を採用。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定する score_regime 関数を実装。
    - マクロ記事抽出用キーワード、最大記事数、モデル（gpt-4o-mini）などを定義。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。
  - AI モジュール設計方針:
    - datetime.today()/date.today() を参照しない（ルックアヘッドバイアス防止）。
    - OpenAI 呼び出し用の内部ヘルパーはモジュール単位で独立実装（テスト時に patch して置換可能）。
    - レスポンスパース失敗や不正応答に対するログ出力とフォールバックを充実させ、処理が全体停止しない堅牢性を重視。
- DuckDB 互換性の考慮
  - DuckDB のクエリ返却値の型変換ユーティリティ（_to_date 等）や executemany の空リスト回避など、DuckDB バージョン間の差異に配慮した実装を行っています。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）
- 実装上の堅牢化（JSON パースの余分なテキスト切り出し、API エラーの分類とリトライ方針、空結果ハンドリングなど）を多数施行。

### セキュリティ (Security)
- API キーが未設定の状態での誤使用を防ぐため、OpenAI API 呼び出しを行う関数は api_key 引数または環境変数 OPENAI_API_KEY の存在を検査し、未設定時は ValueError を送出します。
- .env 読み込みでは OS 環境変数を protected として扱い、意図せぬ上書きを防ぐ仕組みを導入。

### 既知の制限 (Known issues / Notes)
- 現時点で Strategy/Execution/Monitoring の実体実装はこのコードからは読み取れず、パッケージ __all__ に名前が含まれています。今後それらのモジュールが追加される見込みです。
- ai モジュールは OpenAI のモデルと JSON Mode に依存しており、API の仕様変更に備えたエラーハンドリングは入れているが、将来的な SDK 変更に備えた追加対応が必要になる場合があります。
- DuckDB のバージョン差異に伴う挙動は考慮してあるが、実環境での互換性確認が推奨されます。

---

作成元: ソースコード解析に基づく推測的 CHANGELOG。実際のリリースノートは開発履歴を元に適宜更新してください。
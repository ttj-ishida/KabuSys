CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。

フォーマットの慣例:
- 変更は逆時系列（新しいものが上）で記載します。
- セクションは Added / Changed / Fixed / Deprecated / Removed / Security を基本とします。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点、設計上の決定、フォールバックやテストフレンドリな実装などを以下に示します。

Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加（version="0.1.0"）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定/読み込み機能（kabusys.config）
  - .env/.env.local ファイルまたは環境変数から設定を自動的にロードする機能を追加。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基に行い、CWD に依存しない実装。
  - .env の行パースを強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理に対応。
    - インラインコメントの取り扱い（クォート有無での区別）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db)
    - 環境種別 KABUSYS_ENV（development, paper_trading, live の検証）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev のヘルパー

- AI（自然文処理）機能（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news および news_symbols テーブルから指定ウィンドウのニュース記事を集約して銘柄ごとに OpenAI（gpt-4o-mini）へ送信し、ai_scores テーブルに書き込む機能を実装。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数制限、JSON Mode を利用した厳密なレスポンス期待などの制御。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - レスポンス検証ロジック（JSON 抽出、results 配列、code/score の検証、数値チェック、±1.0 でクリップ）。
    - API 呼び出し箇所をモジュールローカルに実装し、ユニットテスト時にモック差し替え可能（_call_openai_api のパッチポイント）。
    - calc_news_window により、JST 基準で前日 15:00 〜 当日 08:30 のウィンドウを UTC naive datetime に変換。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime に保存する機能を追加。
    - マクロニュース抽出はニュース NLP のウィンドウとキーワードリストに基づきタイトルを抽出。
    - OpenAI 呼び出しに対してリトライ・エラー時フェイルセーフ（macro_sentiment=0.0）を実装。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う設計。
    - ルックアヘッドバイアス対策: 関数は datetime.today()/date.today() を参照せず、target_date を明示的入力として扱う。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベース（土日除外）をフォールバックとして使用。
    - カレンダー更新ジョブ calendar_update_job を実装（J-Quants から差分取得して保存、バックフィル対応、健全性チェック）。
    - 最大探索日数やバックフィル日数などの安全パラメータを設定し無限ループや極端値に対処。

  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約。
    - 差分取得 / 保存 / 品質チェックを想定したユーティリティの基盤を実装（jquants_client と quality モジュールの利用を想定）。
    - 市場データの最小日付やデフォルトバックフィル、カレンダー先読みなどのデフォルト戦略を導入。
    - DuckDB におけるテーブル有無チェックや最大日付取得のヘルパー実装。

- リサーチ（kabusys.research）
  - factor_research モジュール:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER、ROE）ファクター計算を実装。
    - DuckDB のウィンドウ関数を活用し営業日ベースのラグや移動平均を算出。データ不足時は None を返す動作。
  - feature_exploration モジュール:
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、rank ユーティリティ、factor_summary を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで完結する実装。
    - rank 実装は同順位の平均ランク採用、浮動小数丸めにより ties の検出を安定化。

- その他
  - ロギング、詳細な docstring、設計上の注意点（ルックアヘッドバイアス防止、DuckDB の executemany 空リスト制約回避、部分失敗時の DB 上書き保護等）をコードに反映。

Fixed
- OpenAI/API 関連の堅牢化
  - 429・ネットワーク断・タイムアウト・5xx に対する再試行・バックオフを実装し、最終的に失敗した場合はスコアを 0.0（ニュース/レジーム側）にフォールバックすることで処理停止を回避。
  - APIError の status_code の有無に対応する安全な分岐を追加。
- .env パーサーの堅牢化
  - クォート内のエスケープ処理、export 前置詞、インラインコメント処理を改善。
- DuckDB の互換性回避
  - executemany に空リスト渡しによる問題を回避するため、空チェックを挟んでから実行する実装。

Changed
- 設計方針の明示
  - ルックアヘッドバイアスを避けるため、日付は関数引数で明示的に渡す方針を徹底（score_news / score_regime / 各研究関数）。
  - DB 書き込みは可能な限り冪等（DELETE→INSERT 等）で行う設計とした。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの扱いは引数オーバーライドまたは環境変数 OPENAI_API_KEY を使用する仕様。未設定時は ValueError を発生させ安全に検出できるように実装。

Notes / 開発者向けメモ
- テストフック:
  - OpenAI 呼び出しを行う関数（kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api）は unit test で patch して差し替え可能に設計。
- 未実装・依存:
  - jquants_client モジュールや quality モジュールはこのコードが利用する外部機能として想定。実際の API クライアント実装は別途提供される前提。
  - strategy / execution / monitoring パッケージ群は公開されているが（__all__ で露出）、本差分での具体的実装は限定的または別ファイルで管理。

---
以上がコードベースから推測して作成した初回リリースの CHANGELOG です。必要であれば、各モジュールごとのより詳細な変更履歴（関数単位の説明や例外仕様、環境変数一覧など）を追記します。どの粒度で追記するか教えてください。
KEEP A CHANGELOG
=================

すべての注目すべき変更をここに記載します。形式は "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- （なし）


[0.1.0] - Initial release
--------------------------

初期リリース。パッケージ全体の主要機能とユーティリティを実装しました。以下は、このリリースで追加された主な機能・モジュールの概要です。

Added
- パッケージ基盤
  - kabusys パッケージの初期バージョン (バージョン文字列: 0.1.0) を追加。
  - パッケージの公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 行パーサを堅牢化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理）。
  - 環境変数読み込み時の上書き制御（override）と OS 環境変数保護（protected set）。
  - Settings クラスを追加し、アプリ設定アクセスを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須項目取得（未設定時は ValueError）。
    - KABU_API_BASE_URL のデフォルト値、DB ファイルパス（DUCKDB_PATH, SQLITE_PATH）取得ヘルパ。
    - KABUSYS_ENV / LOG_LEVEL の検証（有効値の制約）と is_live / is_paper / is_dev ブールプロパティ。

- データ (kabusys.data)
  - ETL インターフェース: pipeline.ETLResult を公開（data.etl 経由で再エクスポート）。
  - ETL モジュール (kabusys.data.pipeline)
    - 差分取得・バックフィル・品質チェックを想定した ETLResult データクラスを実装。
    - DuckDB を用いたテーブル存在チェック、最大日付取得等のユーティリティを実装。
    - ETL の設計方針（差分更新、backfill、品質チェックの扱い）を反映。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を使った営業日判定ロジックを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB 登録値を優先しつつ未登録日は曜日ベースでフォールバックする挙動。
    - calendar_update_job: J-Quants からの差分取得 → 冪等保存（fetch/save を jquants_client 経由で呼び出し）、バックフィル、健全性チェックを実装。
    - 検索範囲制限（_MAX_SEARCH_DAYS 等）により無限ループ等を防止。

- 研究・ファクター (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB SQL ウィンドウ関数で計算。データ不足時の扱いを明確化。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。NULL を考慮した true_range 実装。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS 0 / NULL の扱いも定義）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括計算。horizons の検証を実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を実装。データ不足 (有効レコード < 3) の扱い。
    - rank: 同順位は平均順位で扱うランク関数（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリー関数。

- AI / NLP (kabusys.ai)
  - ニュースセンチメント (kabusys.ai.news_nlp)
    - score_news: raw_news と news_symbols を用い、ターゲットウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）内の記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとの sentiment/ai_score を ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの最大記事数/文字数（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）を実装し、トリミング対応。
    - API 呼び出しのリトライ（429/通信断/タイムアウト/5xx）を指数バックオフで実装。その他エラーはスキップして処理継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション処理（JSON モードでも前後余分テキストが混ざるケースの復元、results リストと各要素の型チェック、未知コードの無視、スコアの数値検証と ±1.0 でのクリップ）。
    - DuckDB の executemany の挙動対策（空リストの禁止）を考慮して DELETE/INSERT を個別に実行。
    - テストしやすさのため _call_openai_api の差し替えを想定（unittest.mock.patch に対応可能）。
  - レジーム判定 (kabusys.ai.regime_detector)
    - score_regime: ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込みする実装。
    - マクロ記事抽出（キーワードベース）、OpenAI（gpt-4o-mini）による JSON 出力パース、API リトライ、API 失敗時のフォールバック（macro_sentiment=0.0）などを実装。
    - ルックアヘッドバイアス防止のため、target_date 未満のデータのみを使用、datetime.today() を直接参照しない設計。
    - 書き込みはトランザクションで安全に行い、失敗時はロールバックを試みる。

Changed
- 初期リリースのため該当なし（すべて新規追加）。

Fixed
- 初期リリースのため該当なし。

Security
- 環境変数読み込みで OS 環境変数を保護する仕組み（protected set）を導入し、.env による上書きからシステム環境を守る設計を採用。
- OpenAI API キー未設定時に ValueError を投げ、誤った無認証呼び出しを防止。

Notes / Implementation details & caveats
- DuckDB に対する executemany の挙動（空リスト不可）を考慮し、空パラメータの場合は DB 操作をスキップする分岐を実装済み。
- OpenAI 呼び出しは JSON mode を期待するが、パーサーは前後に余分なテキストが混ざる可能性を考慮して復元処理を行う。
- API エラーやパースエラーは基本的に例外送出ではなくログ出力＋フォールバックスコア（多くは 0.0）で継続する設計（フェイルセーフ）。
- 日付/時間の扱いは意図的に timezone-naive な datetime/date を使用し、JST↔UTC のウィンドウ変換は明示的に行う方針。
- テスト容易性のため外部呼び出し（OpenAI 呼び出し等）を差し替え可能な形で実装している。

今後の予定（提案）
- strategy / execution / monitoring パッケージの具体的なトレード実装と注文ロジックの追加。
- ai モジュールのモデル選択やプロンプト改善、評価用ユニットテストとモックを整備。
- ETL の実運用向けログ・監査・リトライ戦略の強化、品質チェックからの自動アラート統合（Slack/監視システム）。

----- 

（注）本 CHANGELOG は提示されたコードベースから推測して作成しています。実際のコミット履歴やリリースノートに合わせて適宜調整してください。
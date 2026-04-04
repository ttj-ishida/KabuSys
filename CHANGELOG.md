Keep a Changelog
=================

すべての重要なリリース変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

v0.1.0 - 2026-04-04
-------------------

初回公開リリース。以下の主要機能・実装が含まれます。

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - パブリックサブパッケージ: data, strategy, execution, monitoring を __all__ で公開。

- 設定／環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - OS の既存環境変数は protected として上書きを防止。
  - .env パーサは export プレフィックス、クォート文字、エスケープ、インラインコメントなどを考慮して堅牢に実装。
  - Settings クラスを公開（settings インスタンス）:
    - J-Quants / kabu ステーション / LINE API / DB パス / 監視設定 / システム設定など多数プロパティを提供。
    - env, log_level の妥当性チェック（列挙された許容値以外は ValueError）。
    - パス系は Path 型で返す（expanduser 処理あり）。
    - 監視関連フラグや閾値（CPU/MEM/DISK）を環境変数で指定可能。

- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を元に銘柄ごとの記事を集約し、OpenAI の gpt-4o-mini（JSON Mode）により銘柄単位のセンチメントを -1.0〜1.0 にスコア化。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリに適用）。calc_news_window を提供。
    - 1銘柄あたり最大記事数・最大文字数でトリムし、最大 20 銘柄ずつバッチ送信。
    - API 失敗（429/ネットワーク断/タイムアウト/5xx）に対し指数バックオフでリトライ。部分失敗に対しては失敗チャンクのみスキップし、DB 上の既存スコアを保護する（DELETE → INSERT の置換戦略で冪等性確保）。
    - レスポンス検証（JSON パース、results 配列、code と score の型チェック、未知コードの無視、スコアの有限性チェック）を実装。
    - テスト容易性のため、OpenAI 呼び出し関数を差し替え可能（内部 _call_openai_api を patch 可能）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - 指定日について、ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成しレジーム（bull/neutral/bear）を判定・書き込み（market_regime テーブル）。
    - マクロニュースは news_nlp.calc_news_window と DB クエリで取得し、OpenAI（gpt-4o-mini）で JSON レスポンスを要求して macro_sentiment を取得。
    - API 失敗時は macro_sentiment=0.0 とするフェイルセーフ動作。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT で冪等的に実施。書き込み失敗時は ROLLBACK を試行し例外を伝播。

- Data（データ基盤）モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを利用した営業日判定と関連ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダー情報がない場合は曜日ベース（土日除外）でフォールバック。
    - next/prev/get_trading_days は DB 登録日を優先し、未登録は曜日フォールバックで一貫した結果を返す。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新（バックフィルと健全性チェックを実装）。
  - ETL パイプライン (pipeline.ETLResult, etl)
    - ETLResult dataclass を公開（取得件数・保存件数・品質検査結果・エラー概要などを保持）。
    - pipeline モジュール内で差分取得・保存・品質チェックの設計が記述済み（差分更新・バックフィル・品質チェック方針・id_token 注入可など）。
    - 複数テーブル（prices / financials / calendar）に対する取得/保存カウントと品質問題の集約を意図。

- Research（リサーチ）モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR（20日）、流動性（20日平均売買代金・出来高比）などの定量ファクターを DuckDB 上で計算する関数を提供:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB のウィンドウ関数を活用し、必要なスキャン範囲のバッファを考慮した実装。
    - データ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）までのリターンを一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関をランク処理経由で算出、十分なレコードがない場合は None。
    - 統計サマリー（factor_summary）とランク関数（rank）を実装。外部依存を使わず標準ライブラリのみで実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーおよび外部 API トークンは環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）で扱うことを前提。Settings._require による未設定チェックでエラーを出す箇所があるため、実行環境での機密情報管理に注意してください。

Notes / 設計上の重要点
- ルックアヘッドバイアス対策: 日時計算と DB クエリは target_date を明示的に受け取り、datetime.today()/date.today() を参照しない方針で実装。
- フェイルセーフ: 外部 API エラー時は例外を表面化させずにフォールバック動作（ゼロスコアやスキップ）で処理を継続する設計が多く採用されています（ただし DB 書き込み失敗時は例外を伝播）。
- 冪等性: calendar 更新や score 書き込み等、DB に対して冪等に振る舞う（DELETE → INSERT、ON CONFLICT 戦略想定）。
- テスト性: OpenAI 呼び出しや .env 自動ロードの制御は差し替えや無効化が可能で、ユニットテストを想定した設計。

今後の予定（例）
- strategy / execution / monitoring の具体的な取引ロジックと実行エンジンの実装。
- ai モデル評価の拡張（追加モデル、プロンプト改善、ベンチマーク）。
- ETL の実運用向け監査ログ・メトリクス強化。

--- 

この CHANGELOG はコード内の実装およびドキュメント文字列から推測して作成しています。実際のリリース計画や変更履歴はプロジェクトのリリース管理ポリシーに従って調整してください。
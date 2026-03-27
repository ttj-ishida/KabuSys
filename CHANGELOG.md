# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠し、Semantic Versioning を採用します。

現在のバージョン: 0.1.0

## [Unreleased]

（今後の変更記録用）

## [0.1.0] - 2026-03-27

### Added
- パッケージ基盤
  - kabusys パッケージの初期実装。トップレベルバージョンは `0.1.0`。
  - __all__ に `data, strategy, execution, monitoring` を公開。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルート判定は `.git` または `pyproject.toml` を探索して行い、CWD に依存しない実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ実装（クォート、エスケープ、インラインコメント対応、`export KEY=val` 形式対応）。
  - .env 読み込み時の上書きルール:
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - `override` / `protected` による保護（OS 環境変数の保護など）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能。
    - J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level）など主要設定にアクセスするプロパティを実装。
    - 必須キー未設定時は明示的なエラー（ValueError）を返す。
    - env と log_level に対するバリデーションを実装。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols からニュースを集約して、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を算出・ai_scores テーブルへ書き込む機能を実装。
  - 処理の主な特徴:
    - JST の前日 15:00 〜 当日 08:30 を対象ウィンドウとして計算（内部は UTC naive で扱う）。
    - 1 銘柄あたり最大記事数・文字数（トリム）でトークン肥大化対策。
    - 最大バッチサイズ（20銘柄）でのチャンク処理、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列、code/score の存在と型チェック）。
    - スコアは ±1.0 にクリップ。
    - DB 書き込みは冪等（該当 date+code を DELETE → INSERT）で部分失敗時に既存スコアを保護（コード絞り込み）。
  - テスト容易性:
    - OpenAI 呼び出しを抽象化し、unittest.mock.patch で差し替え可能（_call_openai_api）。

- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して、日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みする機能を実装。
  - 処理の主な特徴:
    - prices_daily から過去 200 日の終値を用いて MA200 乖離を算出（ルックアヘッド防止のため target_date 未満のみ参照）。
    - raw_news をマクロキーワードでフィルタしてタイトルを取得し、LLM でマクロセンチメントを評価（記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0）。
    - OpenAI API 呼び出しは独立実装でモジュール結合を避ける。
    - API フェイル時は macro_sentiment を 0.0 にフォールバックして処理を続行（フェイルセーフ）。
    - レジームスコア合成後、閾値に基づきラベル付けし DB に BEGIN/DELETE/INSERT/COMMIT で保存。DB 書き込み失敗時は ROLLBACK を試行して例外を上位に伝播。

- 研究（Research）モジュール（kabusys.research）
  - factor_research、feature_exploration の主要関数を公開:
    - モメンタム／バリュー／ボラティリティ系ファクター計算: calc_momentum, calc_value, calc_volatility
    - 将来リターン計算: calc_forward_returns（任意ホライズン対応、入力検証あり）
    - IC（Spearman ランク相関）計算: calc_ic（結合、None/非有限値除外、最小サンプルチェック）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - ランク変換ユーティリティ: rank（同順位は平均ランク）
  - 設計上の注意:
    - DuckDB 接続を受け取り prices_daily / raw_financials のみ参照（外部 API/発注にアクセスしない）。
    - 結果は (date, code) をキーとする dict のリストで返却。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を扱う複数のユーティリティを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar が存在しない場合は曜日ベース（土日除外）のフォールバックを一貫して使用。
    - next/prev/get_trading_day は DB に登録されている日付を優先し、未登録日は曜日フォールバックで補完。
    - 安全ガード: 最大探索日数制限（_MAX_SEARCH_DAYS）により無限ループ防止、last_date に対する健全性チェック等。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックを含む）。
    - jquants_client との連携を想定（fetch/save 関数呼び出し）。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを提供し、ETL 実行結果（取得数、保存数、品質問題、エラー）を構造化。
    - 差分更新戦略、バックフィル、品質チェックフローを想定した設計。
    - DuckDB の挙動差（executemany に空リスト不可）を考慮して DB 操作を実装。

- 再エクスポート
  - kabusys.data.etl で ETLResult を公開再エクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / Design Decisions
- ルックアヘッドバイアス防止:
  - 各種処理（news window、regime scoring、factor 計算、forward returns 等）は内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を指定する設計としている。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）呼び出しの失敗は可能な限りロギングしてフォールバック（0.0 やスキップ）し、システム全体の連続実行を優先。
- テスト性:
  - OpenAI 呼び出しや自動 .env ロードの無効化フラグなど、ユニットテストで差し替えや隔離がしやすい設計を心がけている。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョンへの対応や、日付型の取り扱いを明示的に実装。

---

作成されたコードは初期の機能セット（データ取得/整備、研究用ファクター計算、AI ベースのニュース解析・市場レジーム判定）を含む基盤です。将来的なリリースでは以下を想定しています: 発注/実行ロジックの実装（execution モジュール）、運用監視（monitoring）、より詳細なドキュメントとテストカバレッジの拡充。
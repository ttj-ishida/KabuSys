# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルには公開された変更点の要約を載せています。将来のリリースでは Unreleased セクションを更新してください。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
初回リリース — KabuSys のコア機能を実装しました。日本株のデータ取得・ETL・研究用ファクター計算・ニュース NLP と市場レジーム判定を含む初期版です。

### Added
- パッケージのエントリポイント
  - kabusys パッケージを追加。バージョン "0.1.0" を定義し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local 自動ロード機能を実装（プロジェクトルート判定は .git または pyproject.toml を利用）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは以下をサポート：
    - export KEY=val 形式
    - シングル/ダブルクォート、バックスラッシュによるエスケープ
    - インラインコメントの取り扱い（クォートあり/なしの差分処理）
  - Settings クラスを追加し、環境変数の取得とバリデーションを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須取得メソッド）
    - OPENAI 用の設定参照、LINE API トークン、DB パス（DUCKDB_PATH/SQLITE_PATH）、監視用ファイルパス等の既定値
    - KABUSYS_ENV の値検証（development/paper_trading/live）
    - LOG_LEVEL の検証

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）の JSON Mode にバッチ送信し、ai_scores テーブルへスコアを書き込む処理を実装。
  - 特徴：
    - タイムウィンドウ：前日 15:00 JST ～ 当日 08:30 JST（UTC換算で前日 06:00 ～ 23:30）
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたり最大 10 記事・最大 3000 文字にトリム
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ（デフォルトリトライ回数）
    - レスポンスの厳密バリデーション（JSON 抽出・results 配列・コード照合・数値チェック）
    - スコアは ±1.0 にクリップ
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）により部分失敗時の保護

- マクロニュース + レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
  - 特徴：
    - 1321 の ma200_ratio 計算（target_date 未満のデータのみ使用しルックアヘッドを防止）
    - マクロキーワードに基づく raw_news タイトル抽出（最大 20 記事）
    - OpenAI（gpt-4o-mini）呼び出しによるマクロセンチメント評価（JSON 出力想定）
    - API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）
    - レジームスコアは clip(-1.0,1.0)、閾値によりラベル付与
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とエラーハンドリング（ROLLBACK）

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理ロジックを実装（market_calendar テーブル参照／フォールバックは曜日ベース）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティを提供
    - calendar_update_job: J-Quants API から差分取得・バックフィル・保存（健全性チェック、保存件数の返却）
  - pipeline / etl:
    - ETLResult データクラスを実装（ETL 実行結果の集約、品質問題・エラーの収集、辞書変換ユーティリティ）
    - ETL の設計（差分更新、backfill、品質チェックを行う方針）を反映
    - etl モジュールは pipeline.ETLResult を再エクスポート

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB クエリで計算する関数を実装
    - データ不足に対する安全処理（必要行数未満は None）
  - feature_exploration:
    - 将来リターン計算（horizons 指定可、デフォルト [1,5,21]）、IC（スピアマン ρ）、rank、factor_summary を実装
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 実装上の重要点
- ルックアヘッドバイアス対策:
  - 各 AI / リサーチ機能は内部で datetime.today()/date.today() を参照しない設計。関数呼び出し時に明示的な target_date を渡す必要あり。
  - DB クエリは target_date より前のデータだけを参照する等の防止策を実装。
- OpenAI の呼び出し:
  - gpt-4o-mini を想定し JSON Mode を使用。環境変数 OPENAI_API_KEY または各関数の api_key 引数で指定可能。
  - API レスポンスの堅牢なパース・バリデーションとリトライロジックを実装（429/ネットワーク/タイムアウト/5xx 対応）。
- DuckDB を主要なローカル DB として利用。SQL ウィンドウ関数を多用して効率的に集計を行う。
- DB 書き込みは可能な限り冪等性を担保（DELETE → INSERT、ON CONFLICT 相当の扱い）する実装方針。
- .env パーサーは現実的な .env ファイルのパターンに対応するよう実装（コメント処理・クォート・エスケープ等）。
- 部分失敗耐性:
  - ニューススコアリングや ETL は部分的に失敗しても他部分に影響を与えない（例: スコア取得に失敗した銘柄だけスキップして残りは DB 保持）。

### Required / Recommended 環境変数
- 必須（関数を利用する際に必要になることがある）:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabu API 用）
  - OPENAI_API_KEY（AI モジュールを利用する場合）
- 任意 / デフォルト設定あり:
  - KABUSYS_ENV（development|paper_trading|live、デフォルト: development）
  - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
  - DUCKDB_PATH / SQLITE_PATH（デフォルトパスが設定されています）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。

---

今後のリリースでは監視・実行（execution/monitoring）周りや戦略（strategy）実装、テストカバレッジの拡充、CLI / デプロイ関連のドキュメント追加などを予定しています。
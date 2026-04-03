CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
-------------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-04-03
-------------------

初回公開リリース。以下の主要機能と実装を含みます。

Added
- パッケージ初期化
  - kabusys パッケージの基本を実装。__version__ = "0.1.0"。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に設定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local ファイルからの自動読み込みを実装（プロジェクトルート判定: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - export KEY=val 形式やクォート、インラインコメントなどを考慮した堅牢な .env パーサ実装。
  - 環境変数保護（既存の OS 環境変数を上書きしない挙動）と override ロジック。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB /監視 / ログ等の設定をプロパティ経由で取得。必須キー未設定時は ValueError を送出。
  - KABUSYS_ENV / LOG_LEVEL の値検証（有効値の列挙）と is_live / is_paper / is_dev のユーティリティ。

- ニュースNLP（AI）モジュール (kabusys.ai.news_nlp)
  - raw_news / news_symbols を集約して銘柄ごとのニューステキストを生成し、OpenAI（gpt-4o-mini）の JSON モードでバッチセンチメント評価を行う機能を実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
  - バッチ処理（最大 20 銘柄 / チャンク）・記事数/文字数トリム（記事最大 10 件、文字数 3000 文字）・スコアの ±1.0 クリッピング。
  - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフによるリトライ。
  - OpenAI レスポンスの厳密なバリデーション（JSON パース、results リスト、code/score の型検査、未知コード無視）。
  - スコア取得結果を ai_scores テーブルへ冪等的に置換（DELETE → INSERT、部分失敗時に他コードを保護）。
  - テスト容易性のため _call_openai_api を patch 可能に実装。

- 市場レジーム判定モジュール (kabusys.ai.regime_detector)
  - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルに保存。
  - マクロニュース抽出（キーワードベース）・OpenAI による macro_sentiment の取得（gpt-4o-mini、JSON 出力想定）。
  - API 呼び出し、JSON パース、サーバーエラー等に対するリトライ制御とフェイルセーフ（失敗時 macro_sentiment=0.0）。
  - DuckDB を用いたルックアヘッドバイアス防止（date < target_date 条件）と冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK）。

- データプラットフォーム（data）モジュール
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー管理ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が存在しない場合は曜日（平日/週末）ベースのフォールバックを提供。
    - DB 登録値優先、未登録日は曜日フォールバックで一貫した振る舞い。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar への冪等保存、バックフィル・健全性チェック（未来日異常検出）を実装。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー集約など）。
    - 差分取得、backfill、保存は jquants_client（外部モジュール）経由で行う構成を想定。
    - 品質チェックの結果を収集し、呼び出し元が判断できるようにする設計。
    - テーブル存在チェックや最大日付取得などのユーティリティを実装。
  - etl モジュールで ETLResult を再公開。

- 研究（research）モジュール
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金 / 出来高比率）、バリュー（PER / ROE）を DuckDB クエリで算出。
    - データ不足時の None ハンドリング、結果を (date, code) をキーとした dict リストで返す設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）、IC 計算（スピアマンランク相関 calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージで一部ユーティリティ（zscore_normalize）を再エクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーを環境変数 OPENAI_API_KEY か関数引数で解決。未設定時は明示的に ValueError を発生させることで誤動作を防止。

Notes / Design decisions（設計上の注記）
- ルックアヘッドバイアス防止: すべての「当日」依存処理で datetime.today() / date.today() を直接参照せず、target_date を外部から受け取る設計を採用。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時は基本的に例外を上位へ投げず、スコアに中立値（0.0）を使用するなどして処理を継続する実装方針。
- テスト容易性: OpenAI 呼び出し箇所は内部の _call_openai_api を patch してモック化できるようにしており、ユニットテストの容易さを考慮。
- DuckDB 互換性: executemany の空リストバインド等 DuckDB の挙動を考慮した防御的実装を行っている。

Breaking Changes
- なし（初回リリース）

開発者向けメモ
- .env パーサは細かいケース（エスケープ、引用符、インラインコメント）に対応しているため、.env ファイル作成時は .env.example を参照すること。
- OpenAI のレスポンスは JSON モードを期待しているが、余計な前後テキストが混入するケースに備えた復元処理を含む。

ライセンス、貢献方法等
- （この CHANGELOG では省略。プロジェクトルートの README / CONTRIBUTING を参照してください。）
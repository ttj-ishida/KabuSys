CHANGELOG
=========
すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存の変更（互換性壊す可能性があるもの含む）
- Fixed: バグ修正
- Removed: 削除されたもの
- Security: セキュリティ関連

[Unreleased]
------------

- （現状なし）

[0.1.0] - 2026-04-03
-------------------
初回リリース。ライブラリ全体の基本機能と主要コンポーネントを実装。

Added
- パッケージのエントリポイント
  - kabusys.__init__ を追加。__version__ = "0.1.0"、主要サブパッケージとして data, strategy, execution, monitoring を公開。

- 環境変数 / 設定管理
  - kabusys.config: .env ファイルおよび環境変数から設定を読み込むユーティリティを実装。
    - プロジェクトルート検出（.git または pyproject.toml）に基づいた自動 .env 読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env パーサは export 句のサポート、シングル/ダブルクォート内のエスケープ解釈、インラインコメントの扱いを含む堅牢な実装。
    - Settings クラスでアプリケーション設定をプロパティとして公開（J-Quants トークン、kabu API、LINE トークン、DB パス、監視関連しきい値、環境判定等）。
    - 設定値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須項目チェック（_require）。

- AI（LLM）関連
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を集約し、銘柄ごとにまとめたニューステキストを OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントスコアを生成。
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30 を UTC に変換）を提供（calc_news_window）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄／コール）、1銘柄あたり記事数上限、文字数上限によるトリムを実装。
    - API 呼び出しでのリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）と堅牢なレスポンス検証（JSON 抽出、results 配列検証、コード一致、数値検証）。
    - ai_scores テーブルへの冪等的な書き込み（対象コードのみ DELETE → INSERT）を実装。
    - API キー解決（引数または OPENAI_API_KEY 環境変数）。未設定時は ValueError。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定。
    - prices_daily から ma200_ratio を算出し、raw_news からマクロ経済キーワード（複数）に合致するタイトルを抽出。
    - gpt-4o-mini を用いてマクロセンチメントを取得（最大記事数制限、リトライ処理、フェイルセーフで失敗時は 0.0 にフォールバック）。
    - レジームスコア合成・閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出しのプライベート関数は news_nlp と分離して実装（モジュール結合を避ける設計）。

- データプラットフォーム / ETL
  - kabusys.data.pipeline と kabusys.data.etl
    - ETLResult データクラスを追加（ETL 実行結果、品質チェック、エラー情報を格納）。
    - 差分更新／バックフィル／品質チェック方針の下で ETL を行うための基盤を実装（jquants_client と quality モジュールを想定して連携）。
    - DuckDB 接続を前提とした実装（テーブル存在チェック、最終日取得ユーティリティ等）。

  - kabusys.data.calendar_management
    - JPX マーケットカレンダー管理機能（market_calendar テーブルの参照/更新ロジック）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを提供。
    - calendar_update_job: J-Quants API からカレンダー差分を取得し冪等保存する夜間バッチ処理を実装（バックフィル、健全性チェック含む）。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末 = 非営業日）を使用する堅牢設計。

- リサーチ（ファクター算出・特徴量探索）
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB の SQL／ウィンドウ関数で計算する関数群を実装。
    - データ不足時の None ハンドリング、出力は (date, code) ベースの dict リスト。

  - kabusys.research.feature_exploration
    - 将来リターン計算（複数ホライズン、LEAD を用いた効率的取得）、Spearman ランク相関（IC）計算、ランク付けユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部依存を持たない純 Python 実装。入力データの検証・無効値除外を行う。

- モジュールエクスポートの整理
  - 各パッケージの __init__ で主要関数を再エクスポート（例: kabusys.ai.__init__ で score_news、kabusys.research.__init__ で複数の関数を公開、kabusys.data.etl が ETLResult を再エクスポート）。

Changed
- 設計方針の明示
  - 全 AI / リサーチ処理で datetime.today() / date.today() を直接参照せず、外部から target_date を与えることでルックアヘッドバイアスを防止する方針を採用。

Fixed
- （該当なし：初回リリース）

Removed
- （該当なし：初回リリース）

Security
- OpenAI API キー取り扱い
  - API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY から取得する実装。キー未設定時は明示的例外を投げることで誤操作を防止。

Notes / Known limitations
- jquants_client、quality、その他外部連携モジュールの実体はこの差分に含まれていません。ETL や calendar_update_job はこれらのクライアント実装が必要です。
- 実行環境は DuckDB を使用することを前提としています。DuckDB のバージョン差異に注意（コメント内に DuckDB 0.10 の互換性考慮あり）。
- OpenAI のレスポンス形式を JSON Mode（response_format={"type":"json_object"}）で期待するため、将来の SDK・モデル仕様変更が起きた場合は対応が必要です。
- ai モジュールは API コール失敗時にフォールバック（スコア 0.0 や対象外スキップ）する実装のため、部分失敗時も処理継続しますが、運用ポリシーに応じた監視/アラートを推奨します。

Contributing
- 変更は Keep a Changelog に従って記録してください。新機能／修正が行われる度にこの CHANGELOG を更新してください。
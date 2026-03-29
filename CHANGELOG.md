# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のガイドラインに従って記載しています。  
このファイルは、リポジトリ内のコードから推測される機能追加・仕様を元に作成した初期リリースの変更履歴です。

全般
- パッケージバージョン: 0.1.0
- パッケージ説明: KabuSys - 日本株自動売買システム（src/kabusys）

[Unreleased]
- （今後の変更をここに記載）

[0.1.0] - 2026-03-29
Added
- パッケージ基盤
  - 初期パッケージ構成を追加（src/kabusys）。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
  - __version__ を "0.1.0" として定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ の親ディレクトリから .git または pyproject.toml を探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - .env 読み込み時の上書き制御（override）・OS 環境変数保護（protected）をサポート。
  - Settings クラスを提供し、必要な環境変数を明示的に取得するプロパティを実装。
    - J-Quants / kabuステーション / Slack / データベースパス等のプロパティ。
    - KABUSYS_ENV の限定値検証（development / paper_trading / live）。
    - LOG_LEVEL の限定値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - duckdb/sqlite のデフォルトパスを設定（data/kabusys.duckdb, data/monitoring.db）。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとに記事を結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得。
    - JST 時間ウィンドウの厳密計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（UTC 変換済み）。
    - バッチサイズ、記事数・文字数トリム、JSON Mode を用いたレスポンス検証、スコアの ±1.0 クリップを実施。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフで再試行。
    - レスポンスの堅牢なパースとバリデーション（JSON 抽出、results 配列・型検査、未知コードの無視）。
    - 書き込みは部分置換方式（DELETE for each code → INSERT）で冪等性と部分失敗時の保護を実現（DuckDB executemany の互換性考慮）。
    - テスト容易性: _call_openai_api をモック可能に設計。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - prices_daily にはルックアヘッドを防ぐため target_date 未満のみを使用。
    - マクロ記事抽出はマクロキーワード集合によるタイトル検索、記事が無ければ LLM を呼ばず中立（0.0）を使用。
    - OpenAI 呼び出しは gpt-4o-mini / JSON mode を利用。API エラー時はフェイルセーフ（macro_sentiment=0.0）で継続。
    - DB 書き込みはトランザクションで冪等性を確保（BEGIN / DELETE / INSERT / COMMIT、エラー時は ROLLBACK）。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（calendar_management.py）
    - JPX カレンダー（market_calendar）を参照して営業日判定、次/前営業日の取得、期間内営業日リスト取得、SQ日判定などのユーティリティを実装。
    - DB にデータがない場合は曜日ベースのフォールバック（土日非営業日）。
    - next_trading_day / prev_trading_day の最大探索範囲を設定し無限ループを防止。
    - calendar_update_job: J-Quants クライアント経由で差分取得 → market_calendar へ冪等保存。バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（対象日、取得/保存件数、品質チェック結果、エラー一覧などを格納）。
    - 差分更新、バックフィル、データ保存（jquants_client 経由で冪等保存）、品質チェックの想定設計を実装。
    - 内部ユーティリティ: 테ーブル存在チェック、最大日付取得などを実装。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン）、200 日 MA 乖離、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）等のファクター計算を実装。
    - DuckDB の window 関数を活用し、結果を (date, code) ベースの辞書リストとして返す。データ不足は None を返す設計。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を実装。horizons の検証あり（1..252）。
    - IC（Information Coefficient、Spearman の ρ）をランク相関で計算する calc_ic を提供。必要件数未満は None を返す。
    - ランキング関数 rank（同順位の平均ランク、丸め処理で ties の漏れ防止）。
    - factor_summary: 複数カラムの基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。
  - data.stats からの zscore_normalize を re-export（research パッケージの __init__ で取り込み）。

Changed
- 設計方針の徹底
  - 重要モジュール（AI スコアリング、レジーム判定、ファクター計算）においてルックアヘッドバイアスを避けるため、datetime.today()/date.today() を内部ロジックで参照しない設計（外部から target_date を受け取る方式）。
  - OpenAI 呼び出しをモジュール内部で隠蔽しつつ、テストによる差し替えを可能にする設計。

Fixed
- N/A（初期リリース）

Security
- API キーの取り扱い
  - OpenAI の API キーは引数で注入可能。未提供時は環境変数 OPENAI_API_KEY を参照。未設定の場合は明示的に ValueError を発生させることで誤動作を抑止。

Deprecated
- N/A（初期リリース）

Removed
- N/A（初期リリース）

Notes / Implementation details（補足）
- DuckDB を主要な内部 DB として想定。各処理は DuckDB の SQL/ウィンドウ関数を活用することでパフォーマンスと可読性を両立。
- OpenAI とのやり取りは gpt-4o-mini + JSON Mode を前提にプロンプトとレスポンスの厳密性を担保。API のエラーや不正レスポンスに対するフォールバック・リトライロジックを多数実装。
- .env パーシングは多くの実運用ケース（export プレフィックス、引用符、エスケープ、インラインコメント）に対応するよう配慮。
- DB への書き込みは可能な限り冪等操作（DELETE→INSERT、ON CONFLICT 相当の考慮）で設計され、部分失敗時に既存データを不必要に上書きしない工夫をしている。

BREAKING CHANGES
- なし（初期リリース）

Acknowledgements
- 本 CHANGELOG はコードベースの内容から推測して作成したもので、実際のコミット履歴や変更ログと完全に一致しない可能性があります。必要があれば、実際のコミットやリリースノートを基に追記・修正を行います。
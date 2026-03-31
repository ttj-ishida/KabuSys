# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に従います。  
このプロジェクトのバージョンは src/kabusys/__init__.py の __version__ を基にしています。

フォーマットの説明や履歴ポリシーは KEEP A CHANGELOG を参照してください。

なお、以下の項目はリポジトリ内のコード（モジュール構成・ドキュメンテーション文字列・実装）から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-31

Added
- パッケージ初期リリース。
- コアパッケージ構成:
  - kabusys パッケージを公開（__all__ に data, strategy, execution, monitoring を含む）。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境設定 / ロード (.env サポート):
  - kabusys.config モジュールを追加。
  - プロジェクトルート探索: .git または pyproject.toml を起点にプロジェクトルートを特定する実装を提供（配布後も CWD に依存しない）。
  - .env / .env.local 自動ロード機能（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 解析の堅牢化:
    - export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしの行でのインラインコメント扱い（直前が空白・タブの場合に # をコメントとして扱う）を実装。
  - 環境保護機能: OS 環境変数を protected として .env の上書きから保護するオプションを実装。
  - Settings クラスを提供し、アプリケーション設定（J-Quants, kabu API, Slack, DB パス, 環境種別、ログレベル等）をプロパティ経由で取得可能。
  - 必須値取得時は _require により未設定で ValueError を送出（利用者フレンドリーなエラーメッセージ含む）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値以外は ValueError）。

- AI モジュール:
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）でバッチセンチメントスコアを取得して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（JST ベース → DB は UTC 想定）を実装（calc_news_window）。
    - バッチサイズ、記事数・文字数トリム、JSON Mode（厳密 JSON）を利用。
    - エラー耐性:
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
      - レスポンスパース失敗・バリデーション失敗はログ出力の上で該当チャンクをスキップし、処理を継続（フェイルセーフ）。
    - レスポンスの厳密バリデーション実装（results 配列、code と score、スコアの数値化・クリップ）。
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能に実装。
  - kabusys.ai.regime_detector:
    - ETF 1321（Nikkei225 連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp ベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等的に保存する機能を実装。
    - OpenAI 呼び出しは独立実装。API の失敗時には macro_sentiment=0.0 で継続する設計（フェイルセーフ）。
    - リトライ・エラー処理、JSON パースの安全処理を実装。
    - レジーム合成ロジック（スコアのクリップと閾値に基づくラベリング）を実装。
    - ルックアヘッドバイアス防止のため内部で datetime.today()/date.today() を直接参照しない設計。

- Data / ETL / カレンダー:
  - kabusys.data.pipeline:
    - ETL のインターフェースと ETLResult データクラスを実装。取得数・保存数・品質チェック結果・エラー概要を格納可能。
    - DuckDB を使った差分取得ロジックの補助ユーティリティ（テーブル存在チェック・最大日付取得など）。
    - ETL の設計方針（差分更新、backfill、品質チェックの扱い）をドキュメント文字列に明示。
  - kabusys.data.etl:
    - pipeline.ETLResult を再エクスポート。
  - kabusys.data.calendar_management:
    - JPX カレンダー（market_calendar）を管理する夜間バッチ（calendar_update_job）および営業日判定ユーティリティ群を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などの関数を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - カレンダーバックフィル・健全性チェック・J-Quants API からの差分取得と保存を実装（jq クライアント呼び出しを使用）。
    - 最大探索日数制限を導入して無限ループを防止。

- Research（因子・特徴量解析）:
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M）、200 日移動平均乖離、ATR（20 日）、流動性（20 日平均売買代金、出来高比）などのファクター計算を実装。
    - raw_financials を参照して PER / ROE を計算するバリュー系処理を実装（calc_value）。
    - DuckDB SQL + Python の組合せでレコードを返す形式を採用（(date, code) キーの dict リスト）。
    - データ不足時は None を返すなど堅牢に実装。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: スピアマンのランク相関）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
    - 入力検証（horizons の値検証等）あり。

- その他ユーティリティ・実装品質:
  - DuckDB を主要なオンディスク分析 DB として採用（クエリ実行は duckdb.DuckDBPyConnection を前提）。
  - ロギング（logger）を各モジュールに導入し、情報・警告・例外状況を出力。
  - API 呼び出しに対するリトライ・バックオフ戦略やレスポンスバリデーションなど、実運用を意識した堅牢性を重視。
  - ドキュメンテーション文字列（docstring）を多く含め、設計方針や処理フローを明示。

Security
- 環境変数の自動読み込みはプロジェクトルートを基に行い、OS 環境変数を protected として誤って上書きしない設計を採用。
- OpenAI API などの機密情報は環境変数（OPENAI_API_KEY 等）で注入する前提。AI モジュールの関数は api_key 引数で注入可能。

Notes / Known limitations
- OpenAI を用いる機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）の設定が必須。api_key を引き渡す形でも可。
- ai 関連は外部 API の挙動に依存するため、ネットワーク障害や API 仕様変更により結果が異なる可能性あり。実装はフェイルセーフ（失敗時スキップ・デフォルト値）を採用。
- 一部 DuckDB のバインド挙動（executemany に空リストが不可等）を考慮した実装を行っている（互換性対策）。
- news_nlp と regime_detector はそれぞれ独自の _call_openai_api を持ち、モジュール間で private 関数を共有しない設計（モジュール結合を低減）。

---

今後のリリースで想定される改善点（例）
- strategy / execution / monitoring モジュールの実装拡張（現状パッケージ公開名のみ）。
- テストスイートと CI での自動検証（OpenAI 呼び出しのモックを含む）。
- J-Quants / kabu API クライアントの実装と統合テストの追加。
- パフォーマンス最適化（大規模データ処理時のクエリ最適化、バッチ処理改善）。

（以上）
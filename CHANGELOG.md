CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

0.1.0 - 2026-03-29
-----------------

Added
- 初期リリース。以下の主要機能群を実装・公開しました。
  - パッケージ初期化
    - kabusys.__init__ にてバージョン `0.1.0` を定義。パッケージの公開 API に data / strategy / execution / monitoring を想定（現時点では一部モジュールは未実装または別ファイルで提供）。
  - 設定管理 (.env / 環境変数)
    - kabusys.config: .env / .env.local ファイルの自動読み込み機構を実装（プロジェクトルート判定は .git または pyproject.toml を探索）。
    - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
    - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）などの設定をプロパティ経由で取得可能。未設定時は明示的な例外を発生させる必須設定取得ヘルパ (_require) を用意。
    - デフォルトの DB パス: DuckDB = data/kabusys.duckdb、SQLite = data/monitoring.db。
  - AI（ニュース NLP / レジーム判定）
    - kabusys.ai.news_nlp:
      - raw_news と news_symbols を元に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini の JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を計算。
      - チャンク処理（デフォルト最大 20 銘柄/リクエスト）、1 銘柄あたり最大記事数／文字数制限、429/ネットワーク断/5xx への指数バックオフリトライ、レスポンスバリデーション、スコアのクリップ、DuckDB への冪等書き込み（DELETE→INSERT）を実装。
      - calc_news_window: JST ベースのニュース取得ウィンドウ計算を提供（テストやルックアヘッドバイアス対策として datetime.today() を参照しない設計）。
      - score_news(conn, target_date, api_key=None) を公開。OpenAI API キーは引数か環境変数 OPENAI_API_KEY で指定。
    - kabusys.ai.regime_detector:
      - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
      - マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）、リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）、計算結果を market_regime テーブルへ冪等書き込みする score_regime(conn, target_date, api_key=None) を実装。
      - 内部での OpenAI 呼び出しは独立実装とし、モジュール間のプライベート関数共有を避ける設計。
  - Data（ETL / カレンダー / パイプライン）
    - kabusys.data.pipeline:
      - ETLResult データクラスを実装。ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して返却・ロギング可能。
      - 差分更新・バックフィル・品質チェックを想定した設計（実際の jquants_client 呼び出し箇所を統合する想定）。
    - kabusys.data.etl:
      - pipeline.ETLResult を再エクスポート。
    - kabusys.data.calendar_management:
      - JPX カレンダー管理（market_calendar）に関するユーティリティ群を実装。
      - 営業日判定（is_trading_day）、翌/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 判定（is_sq_day）等を提供。
      - market_calendar が未取得のときは曜日ベース（土日非営業日）でフォールバックする一貫した挙動。
      - calendar_update_job: J-Quants からカレンダーデータを差分取得して保存する夜間ジョブ（バックフィル・健全性チェック付き）を実装。
    - データベース操作は DuckDB を前提に実装（型変換・空リスト executemany の回避などの互換性対策あり）。
  - Research（ファクター計算・特徴量探索）
    - kabusys.research パッケージを実装（calc_momentum, calc_value, calc_volatility, zscore_normalize の再エクスポート、calc_forward_returns, calc_ic, factor_summary, rank など）。
    - ファクター計算は prices_daily / raw_financials を参照し、モメンタム（1/3/6M 等）、MA200 乖離、ATR、平均売買代金、PER/ROE 等を計算。
    - 将来リターン（calc_forward_returns）は任意ホライズン対応（デフォルト [1,5,21]）、ホライズン引数のバリデーションを実装。
    - IC（スピアマンのランク相関）計算、ランク付けユーティリティ、統計サマリー集計を提供。
  - その他
    - メソッド・関数レベルでのログ出力（logger）を多く配置し、失敗時の情報を残す設計。
    - テスト容易性考慮: OpenAI 呼び出し関数の差し替えポイント（unittest.mock.patch を想定）を明示。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 特記事項なし。ただし OpenAI API キーや各種トークンは環境変数で管理することを想定。Settings の未設定は明示的にエラーにすることで誤設定を検出しやすくしています。

Notes / 使用上の注意
- OpenAI 連携
  - news_nlp / regime_detector の実行には OpenAI API キー（環境変数 OPENAI_API_KEY または api_key 引数）が必須。キー未設定時は ValueError を送出します。
  - API 呼び出しは gpt-4o-mini を前提とした JSON mode を利用します。OpenAI SDK のバージョン差異に伴う挙動変化を考慮しており、SDK 側の APIError.status_code の有無にも対応しています。
- 環境変数 / .env の自動ロード
  - プロジェクトルート検出はファイル __file__ を起点に上位ディレクトリを探索します。パッケージ配布後もカレントワーキングディレクトリに依存せず動作する設計です。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ルックアヘッドバイアス対策
  - AI モジュール・研究モジュール等は内部で datetime.today() や date.today() を直接参照せず、target_date を明示的に渡す設計です。バックテストや再現性確保の観点で意図的な設計です。
- DuckDB の互換性
  - DuckDB のバージョンに依存する SQL バインド（例えば executemany に空リストを渡せない等）に配慮した実装を行っています。

今後の予定
- strategy / execution / monitoring の具現化（売買戦略の実装・発注ロジック・監視周り）
- 追加の ETL 処理の具備（jquants_client の実体実装・品質チェックルールの拡充）
- テストカバレッジ拡充・CI パイプライン整備

Authors
- このリリースのコードはプロジェクト初期実装として作成されています。README やドキュメントを追って詳細な使用方法を追加予定です。
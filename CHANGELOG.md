# CHANGELOG

すべての変更は Keep a Changelog の原則に従って記載しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

全般:
- DuckDB をバックエンドにしたデータパイプライン / 分析 / ETL 基盤と、OpenAI（gpt-4o-mini）を利用したニュース NLP / 市場レジーム判定機能を中心に実装されています。
- 設定は .env / .env.local / OS 環境変数から読み込み、アプリケーション設定を Settings クラスで提供します。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能です。

Unreleased
---------
- いくつかの実装上の細部（例: pipeline._get_max_date の末尾に不完全な行が存在）が残っており、次リリースで修正予定です。
- ドキュメント・単体テストの追加、エラー時の更なる observability 向上、OpenAI クライアントの抽象化（DI の強化）を検討中。

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース相当の機能群を追加。
  - kabusys パッケージの基本エントリポイントを追加（__version__ = 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定・環境変数管理（kabusys.config）
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を基準）。
  - .env/.env.local ファイル自動読み込み（OS 環境変数を保護する protected 機構を導入）。
  - export KEY=val 形式、引用符あり/なしの行のパース、行内コメントの取り扱いなど堅牢な .env パーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / 環境種別・ログレベル等をプロパティで取得（必須項目は未設定時に ValueError を送出）。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）の JSON Mode を利用して銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1銘柄あたりの記事数・文字数トリム、429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳格なバリデーションとスコアのクリップ、取得済みコードのみを置換して ai_scores に冪等書き込み（DELETE→INSERT）する仕組みを実装。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_unittest.mock.patch で差し替え想定）。

  - regime_detector モジュール:
    - ETF 1321（Nikkei 225 連動型）の200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - OpenAI 呼び出しのリトライ / フェイルセーフ（API失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等的な書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス対策：date 比較は target_date 未満／以前などで外部時刻関数を参照しない設計。

- データ基盤（kabusys.data）
  - calendar_management:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - データ未取得時は曜日ベースのフォールバック（土日を非営業日扱い）。
    - calendar_update_job：J-Quants API から差分取得して market_calendar を冪等保存、バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを実装（ETL 実行結果の集約、品質問題・エラーの収集）。
    - pipeline モジュールに ETL の設計方針とユーティリティを追加（差分更新、品質チェック、保存は jquants_client に委譲）。
    - etl モジュールで pipeline.ETLResult を再エクスポート。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の SQL を主体に計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、営業日ベースの窓確保など現実的な処理を導入。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB SQL で構築。

Changed
- .env の読み込みロジックを安全かつ柔軟に改善（export 形式、引用符・エスケープ、インラインコメントの扱いを細かく実装）。
- OpenAI 呼び出しに対して JSON Mode を利用し、応答の厳格なパースと検証を行うようにした（news_nlp / regime_detector）。

Fixed
- -（初版のため既知の不具合修正履歴はなし。既知問題は下記参照）

Security
- 環境変数（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN 等）を Settings 経由で必須チェックし、未設定時に明示的なエラーを出すことで秘密情報の不整備を早期に検出。

Known issues / Notes
- pipeline._get_max_date の末尾に不完全な実装片（返却処理が途中で切れている）が存在します。ETL の一部ユーティリティ関数で修正が必要です（次リリースで修正予定）。
- 一部のモジュールで外部クライアント（J-Quants, OpenAI）のエラー時にログは出るがリトライ戦略や通知連携の追加要望あり（運用環境により閾値や通知対象をカスタマイズする予定）。
- ai モジュールは OpenAI の利用に依存するため API レートやコストに注意。news_nlp はバッチ化や最大記事長の制限等でトークン制御を行っていますが、運用時はさらに司令/料金管理が必要です。
- DuckDB バージョン依存の取り扱い（executemany の空リスト制約や配列バインドの挙動）に対処するための記載・ワークアラウンドを実装していますが、環境差異に注意。

開発者向けメモ
- テスト容易性のため、OpenAI API 呼び出し部（_call_openai_api）をモジュール内で分離しており、unittest.mock.patch により差し替え可能です。
- 自動 .env 読み込みはパッケージの設計上 CWD に依存しないため、配布後も適切に機能するようプロジェクトルート検出ロジックを実装しています。

---------- 
（この CHANGELOG はコードの静的解析・コメントから推測して作成しました。実際の変更履歴やリリースノートとは差異がある可能性があります。必要に応じて日付やバージョン、細部を調整してください。）
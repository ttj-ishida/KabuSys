# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成しています（推定に基づく説明・設計意図を含みます）。

## [0.1.0] - 2026-04-01

初回公開リリース。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを "0.1.0" に設定。
  - パブリックモジュールとして data / strategy / execution / monitoring を __all__ で公開。

- 設定管理 (kabusys.config)
  - .env / .env.local /環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 複雑な .env パース実装:
    - export KEY=val 形式対応、クォート文字のエスケープ処理、インラインコメント処理等に対応。
  - Settings クラスを導入し、アプリケーション設定をプロパティで提供（J-Quants トークン、kabu API、Slack、DB パス、監視閾値、環境文字列、ログレベル等）。
  - env と log_level に入力検証を実装（許容値を限定し不正値で ValueError を送出）。
  - 各種ファイルパスは Path 型で提供し expanduser を適用。

- AI モジュール (kabusys.ai)
  - news_nlp: raw_news を元に OpenAI（gpt-4o-mini + JSON Mode）で銘柄別センチメントを算出し ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 -> UTC での比較）を提供する calc_news_window。
    - バッチ処理（最大 20 銘柄／チャンク）、1 銘柄当たり記事数・文字数上限、レスポンス検証、スコアのクリップ処理を実装。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）は指数バックオフでリトライ。フェイルセーフとして失敗時は該当チャンクをスキップして継続。
    - レスポンスの JSON 抽出・バリデーション実装（余計な前後テキストの復元処理含む）。
    - DuckDB の executemany の互換性考慮（空リストバインド回避）。
  - regime_detector: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で market_regime を判定・保存。
    - ma200_ratio 計算（target_date より前のデータのみ使用してルックアヘッドを排除）。
    - マクロニュース抽出（キーワードベース、最大記事数制限）。
    - OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価。API失敗時は macro_sentiment=0.0 にフォールバック。
    - 最終的なスコアを閾値でラベル化（bull / neutral / bear）し、market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダーを扱うユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar 未取得時の曜日ベース・フォールバック、DB 登録値優先の一貫した判定ロジックを提供。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、save_market_calendar 呼び出し）。
  - pipeline / etl:
    - ETLResult データクラスを公開し、ETL の各種取得数・保存数・品質チェック結果・エラー情報を保持できるように実装。
    - pipeline モジュールの設計方針に基づく差分更新・バックフィル・品質チェックのインターフェースを準備（jquants_client, quality と連携する想定）。
  - その他ユーティリティ:
    - 複数の内部関数で DuckDB の日付・テーブル存在チェック、fetch/保存の互換性に配慮。

- 研究モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）等のファクター計算を実装。
    - DuckDB のウィンドウ関数を活用した SQL ベース実装で、target_date 基準の計算結果を (date, code) キーの辞書リストで返す。
    - データ不足時は None を返すなど欠損処理を明示。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の rho）計算（calc_ic）、ランク化 util（rank）、ファクター統計サマリ（factor_summary）を実装。
    - 入力バリデーション（horizons の上限 252 日など）や ties の平均ランク処理等の実務的配慮を実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーを引数で注入可能にしてテスト性・鍵管理の柔軟性を確保。環境変数 OPENAI_API_KEY もサポート。

### Notes / Implementation details / 制約・注意事項
- ルックアヘッドバイアス対策:
  - AI モジュール・研究モジュールともに datetime.today() / date.today() を内部で参照せず、必ず caller が渡す target_date を基準に処理する設計。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定（JSON Mode を使用）。API レスポンスのパース失敗や API 停止に対してはフェイルセーフ（0.0 やスキップ）で継続する戦略。
  - テスト容易性のため _call_openai_api をモジュール内で定義しており、ユニットテスト時にモック差し替えが可能。
- DuckDB 互換性:
  - executemany に空リストを渡せない DuckDB の振る舞いを考慮して空チェックを行っている（特に ai_scores 書き込み処理）。
- DB 書き込みの冪等性:
  - market_regime / ai_scores 等への書き込みは DELETE → INSERT の方式で冪等性を担保。トランザクション（BEGIN/COMMIT/ROLLBACK）を使用。
- 時刻・タイムゾーン:
  - news のウィンドウ計算は JST を起点に UTC naive datetime に変換して DB と比較する実装（タイムゾーン混入を避ける）。
- 環境変数:
  - 必須の環境変数は Settings 経由でアクセスすると ValueError が発生（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）。README/.env.example に従って設定する必要あり。
- 未実装・将来拡張想定:
  - monitoring / execution 等の公開モジュールは __all__ に含まれているが、今回提供された抜粋には詳細実装が含まれていない（将来のリリースで追加される想定）。

---

今後のリリースでは以下を想定しています（推定）:
- AI モデルやプロンプトの細かなチューニング、モデル指定の柔軟化。
- ETL の実行スケジューリング・監査ログ・リトライ耐性の強化。
- monitoring / execution の具体的な監視・発注ロジックの追加。
- テストカバレッジ向上（ユニット/統合テスト）と CI 設定の整備。

もしリリース日や追加で強調したい変更点（例: 外部 API バージョン、互換性ポリシー等）があれば教えてください。これらを反映した更新版の CHANGELOG を作成します。
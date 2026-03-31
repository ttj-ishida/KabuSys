# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般方針:
- 日付はリリース日を示します。
- 各項目はコードベース（src/kabusys 以下）の実装内容から推測して記載しています。
- 初回リリースとして 0.1.0 をまとめています。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-03-31
初回リリース。自動売買プラットフォーム（日本株）向けのコアライブラリ群を提供します。主な機能はデータ取得/ETL、マーケットカレンダー管理、リサーチ用ファクター計算、ニュースのNLU/センチメント評価（OpenAI 利用）、市場レジーム判定、設定管理などです。

### Added
- パッケージ基盤
  - パッケージのエントリポイントを定義（src/kabusys/__init__.py）。
  - バージョンは 0.1.0。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）をプロジェクトルート（.git または pyproject.toml を検出）から自動的に読み込む機能を実装。
  - .env のパースは以下に対応:
    - コメント行・空行の無視
    - export KEY=val 形式のサポート
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの場合のインラインコメント処理（# の直前が空白／タブのときのみ分離）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須環境変数取得ヘルパー `_require` を提供（未設定時に ValueError を発生）。
  - 各種設定プロパティを定義（J-Quants / kabu API / Slack / DB パス / 環境判定 / ログレベルなど）。KABUSYS_ENV と LOG_LEVEL の検証を実装。
  - デフォルトの DB パス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db。

- Data モジュール（src/kabusys/data）
  - calendar_management.py
    - JPX マーケットカレンダーの管理と営業日判定APIを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末を非営業日扱い）を実装。
    - DB がまばらな場合でも一貫性を保つロジック（DB 値優先、未登録日は曜日ベースで補完）。
    - calendar_update_job を実装し、J-Quants クライアントから差分取得→保存（バックフィルと健全性チェック含む）。
  - pipeline.py / etl.py
    - ETLResult dataclass を追加（ETL の集計情報、品質問題、エラーを保持）。
    - ETL パイプライン用ユーティリティ（DB の最大日付取得、テーブル存在チェック、トレーディング日調整など）。
    - ETL の設計方針に従い差分更新・バックフィル・品質チェックの枠組みを整備。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- AI（ニュース NLP / レジーム判定）（src/kabusys/ai）
  - news_nlp.py
    - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄ごとのセンチメントスコアを算出・ai_scores に保存する機能を実装。
    - タイムウィンドウ（JST: 前日15:00～当日08:30 を UTC に変換）計算を提供（calc_news_window）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1銘柄あたりの記事数上限・文字数トリムの実装。
    - リトライ戦略（429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ）を実装。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、"results" 構造検証、スコアの数値変換、既知コードのみ受け入れ、±1.0 クリップ）。
    - API 失敗時は当該チャンクをスキップするフェイルセーフ挙動。部分失敗でも既存データを保護するため、更新は該当コードのみ削除→挿入。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api）。
  - regime_detector.py
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とニュースマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能（score_regime）を実装。
    - prices_daily から MA200 乖離を計算（ルックアヘッド防止のため target_date 未満データを使用）。
    - raw_news からマクロキーワードでフィルタしたタイトルを取得し、OpenAI でマクロセンチメントを評価（記事が無い場合は LLM 呼び出しを行わない）。
    - LLM 呼び出しに対するリトライ/フォールバック: API 失敗やパース失敗時は macro_sentiment=0.0 として継続（例外を上げない）。最大3回リトライ。
    - DB へは冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。失敗時は ROLLBACK を試みて例外を伝播。
    - テストのため _call_openai_api をモック可能にしている。
  - ai パッケージは score_news と score_regime を公開。

- Research（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日ベースのラグや移動平均を計算。データ不足時は None を返す設計。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）を実装。
    - ランク相関（Spearman）に基づく IC 計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで動作。
  - research パッケージは主要な関数をエクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。

### Changed
- （初回リリースのため特になし）

### Fixed
- （初回リリースのため特になし）

### Security
- OpenAI API キー等の必須情報は環境変数経由で扱う設計。キー未設定時は明示的なエラー（ValueError）を投げるため、誤設定に気づきやすい。

### Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策:
  - AI スコアリング / レジーム判定 / ファクター計算などはすべて target_date を明示的に受け取り、内部で datetime.today() / date.today() を参照しない設計。
  - DB クエリは target_date 未満（あるいは target_date 到達基準）でデータ選択を行い、未来データの参照を防止。
- フェイルセーフ:
  - LLM 呼び出しの失敗は基本的に局所的に扱い（0.0 でフォールバック、またはチャンクスキップ）、システム全体を停止させない。
- DuckDB への依存:
  - 多くの処理は DuckDB へ SQL を投げる設計。compatibility を考慮した実装（executemany の空リスト回避等）あり。
- テスト容易性:
  - OpenAI 呼び出しの内部関数をモック可能に設計（unittest.mock.patch で差し替え）。

---

将来的なリリースでは、監視/実行（execution/monitoring）や発注ロジック、より詳細な品質チェック、外部サービス統合などが追記されることが想定されます。
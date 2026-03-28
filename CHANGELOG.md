Keep a Changelog に準拠した CHANGELOG.md（日本語）
すべての注目すべき変更を記録します。意味的バージョニングに従います。

Unreleased
----------

（空）

0.1.0 - 2026-03-28
-----------------

Added
- 初回リリース。日本株自動売買・データ基盤向けのコアライブラリを追加。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージトップでの __all__ により主要サブパッケージ（data, research, ai, execution, monitoring 等）の公開を想定。

- 設定管理
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - OS 環境変数保護（既存値を保護する protected 機構）と上書き制御（override オプション）。
  - _parse_env_line による多様な .env フォーマット（export プレフィックス、引用符内のエスケープ、コメント処理）対応。
  - 環境変数取得用 Settings クラスを提供（J-Quants、kabuステーション、Slack、DB パス、実行環境・ログレベル判定など）。値検証（許容値チェック）や is_live / is_paper / is_dev のユーティリティプロパティを備える。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- AI（自然言語処理）機能
  - news_nlp モジュール
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - バッチ処理（1APIコールあたり最大20銘柄）、記事数・文字数トリム、JSON Mode を利用したレスポンス検証、スコアの ±1.0 クリップ。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実行し、致命的でない失敗はスキップして処理継続するフェイルセーフ設計。
    - calc_news_window による JST ベースのニュース集計ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）。
    - レスポンスパースで余分な前後テキストが混入した場合の復元ロジックを実装。
  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロキーワードフィルタによる raw_news 抽出、OpenAI 呼び出しのリトライ・フェイルセーフ、スコア合成とクリッピング、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）をサポート。
    - lookahead バイアス防止のため datetime.today()/date.today() に依存しない設計。

- データプラットフォーム機能（DuckDB ベース）
  - data.pipeline / ETLResult
    - ETL の実行結果を表す dataclass（ETLResult）を追加。品質チェック結果、取得/保存件数、エラー一覧などを保持し、to_dict でシリアライズ可能。
    - 差分更新・バックフィル・品質チェック設計方針を反映。
  - data.calendar_management
    - JPX 市場カレンダー管理（market_calendar テーブル）の夜間更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し冪等保存。
    - 営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供し、DB データ優先だが未登録日は曜日ベースでフォールバックする一貫した挙動を実現。
    - 最大探索範囲やバックフィル、健全性チェック（未来日付の異常検出）を実装。

- リサーチ（ファクター計算・特徴量解析）
  - research.factor_research
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、流動性指標（20 日平均売買代金、出来高比）などのファクター計算関数（calc_momentum, calc_volatility, calc_value）を提供。DuckDB の SQL とウィンドウ関数で実装。
    - raw_financials からの EPS/ROE 取得により PER/ROE を算出。データ不足時は None を返す方針。
  - research.feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証付き）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）と rank/ factor_summary などの統計ユーティリティを提供。
    - pandas など外部依存を避け標準ライブラリと DuckDB のみで実装。

- テストしやすさ・堅牢性
  - OpenAI API 呼び出しのラッパー関数を各モジュールで独立実装しており、ユニットテスト時に patch による差し替えが容易。
  - DuckDB を前提とした SQL 実行で、空集合や未作成テーブル、データ不足に対する安全なハンドリングを備える。
  - 全体的にルックアヘッドバイアス防止設計（グローバル日時参照回避）を徹底。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- OpenAI API キー等の取り扱いは引数注入または環境変数参照により行い、自動的にログ等へ露出しない実装方針。

Migration notes / 注意事項
- 環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（または各関数の api_key 引数）などが必須/想定される。Settings クラスの _require により未設定時は ValueError を発生させる。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後や実行コンテキストに応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。
- OpenAI のモデルとして gpt-4o-mini を使用。レスポンスは JSON モードを期待する（厳密な JSON 出力が前提）。
- DuckDB のバージョン差分（executemany の空リスト扱いなど）に配慮した実装をしているが、実行環境の DuckDB バージョンにより振る舞いが異なる場合があり得るので注意。

Acknowledgments
- 本リリースは DuckDB、OpenAI API を主要な依存先とし、J-Quants を通じたデータ取得を想定した構成です。
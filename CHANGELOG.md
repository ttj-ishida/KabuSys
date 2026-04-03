# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初期公開バージョンを以下に記載します。

全般注意:
- 日付は本 CHANGELOG 作成日（2026-04-03）を使用しています。
- コードから推定した設計方針、依存性、動作上の注意点を補足として記載しています。

## [0.1.0] - 2026-04-03

### Added
- 初期リリース。日本株自動売買プラットフォームのコアライブラリを提供。
  - パッケージ公開名: kabusys（src/kabusys/__init__.py）
  - バージョン: 0.1.0

- 環境設定管理（src/kabusys/config.py）
  - .env ファイル（.env / .env.local）および OS 環境変数の読み込み機能を実装。プロジェクトルートを .git または pyproject.toml から探索して自動読み込みを行う。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装（クォート、エスケープ、inline コメント、export 形式対応）。
  - Settings クラスを公開し、主要設定値をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（検証）
    - ヘルパープロパティ: is_live / is_paper / is_dev

- AI モジュール（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントスコアを算出。
    - バッチ処理（最大 20 銘柄／回）、1 銘柄あたり記事上限・文字数トリム対応。
    - リトライポリシー（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造検証、未知コード無視、スコアクリップ）。
    - ai_scores テーブルへの冪等書き込み（該当 code の DELETE → INSERT）。
    - 公開 API: score_news(conn, target_date, api_key=None)
    - 補助: calc_news_window 関数（JST に基づくウィンドウ計算）

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - OpenAI 呼び出しをラップした独自実装（news_nlp との結合を避ける設計）。
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- Data モジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）の管理機能。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にデータがない場合は曜日ベース（平日）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得し market_calendar に冪等保存（fetch/save は jquants_client を利用）。
    - 安全対策: 最大探索日数 / バックフィル / 健全性チェックを実装。

  - ETL パイプライン（src/kabusys/data/pipeline.py、src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（fetch/save件数、品質問題、エラーの集約）。
    - 差分更新・バックフィル・品質チェックのためのユーティリティを実装（jquants_client / quality と連携）。
    - DuckDB を前提にしたテーブル存在チェック等のユーティリティ実装。
    - etl.py では ETLResult を公開インターフェースとして再エクスポート。

  - jquants_client（暗黙的依存）を利用する設計で、fetch/save 関数によりデータの取得・保存を行う想定。

- Research モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比）、
      Value（PER、ROE）を DuckDB 上の SQL と Python で計算。
    - 関数: calc_momentum, calc_volatility, calc_value（すべて prices_daily か raw_financials のみ参照）。
    - 設計方針として本番取引系 API へのアクセスは行わない（分析専用）。

  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換 util（rank）、統計サマリー（factor_summary）。
    - pandas 等外部ライブラリに依存しない実装。

- 公開エクスポート
  - パッケージの __all__ に data, strategy, execution, monitoring を定義（将来のモジュール拡張を想定）。
  - research.__init__ で主要関数を再エクスポート。

### Changed
- N/A（初期リリースのため変更点なし）

### Fixed
- N/A（初期リリースのため修正点なし）

### Security
- AI 機能は OpenAI API キー（OPENAI_API_KEY または関数引数）を必要とする。API キー未設定時は ValueError を送出。
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テストの容易化・秘密情報の漏洩防止に貢献）。

### Notes / Implementation details（重要な設計・運用注記）
- DuckDB 依存:
  - executemany に空リストを渡せない（DuckDB 0.10 の既知制約）ことを考慮して、空チェックを入れている。
- ルックアヘッドバイアス対策:
  - AI・研究関連の各関数は datetime.today() / date.today() を参照せず、呼び出し側が target_date を渡す設計。
  - DB クエリは target_date 未満（または排他）でデータ選択を行う等、未来情報の漏洩を防ぐ実装が意図されている。
- 冪等性:
  - ETL / calendar / ai スコア書き込み処理は冪等化（DELETE → INSERT、ON CONFLICT 更新など）を意識した実装。
- フェイルセーフ:
  - OpenAI 等外部 API 呼び出しでエラー発生時は部分的にスキップして継続する方針（例: macro_sentiment=0.0、スコア取得失敗は該当銘柄のみ除外）。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api 等）は unittest.mock.patch で差し替えやすい位置に実装。
- 環境変数（主なキー、参考）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
  - OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - KABUSYS_ENV（development / paper_trading / live）, LOG_LEVEL
- 外部依存:
  - openai（OpenAI SDK）、duckdb、J-Quants クライアント（jquants_client 想定）、kabu API（kabu_standalone 想定）等。

---

今後のリリースで期待される改善点（例）
- strategy / execution / monitoring の具体的実装（現在はパッケージエクスポートのみ）。
- ai のモデル選択・温度パラメータ・プロンプト改善のチューニング。
- ETL のスケジューリング、ジョブ状態の監視ダッシュボード。
- テストカバレッジ拡充（特に外部 API 呼び出しのモック・統合テスト）。

もし特定のファイルや機能について詳しい変更ログ（関数レベルの更新差分）を出力したい場合は、どのファイルを重点にするか指示ください。
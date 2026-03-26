CHANGELOG
=========
すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-03-26
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基盤モジュール群を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py: __version__ = "0.1.0"、主要サブパッケージを公開 (data, strategy, execution, monitoring)。
  - 設定・環境管理
    - src/kabusys/config.py
      - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env/.env.local を自動読み込み。
      - export プレフィックスやクォート・エスケープ・行内コメントに対応した堅牢な .env パーサを実装。
      - OS 環境変数の保護（protected set）や .env.local による上書き、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
      - 必須 env チェック（_require）、環境値検証（KABUSYS_ENV, LOG_LEVEL）を提供。
  - データプラットフォーム（DuckDB ベース）
    - src/kabusys/data/pipeline.py
      - ETLResult データクラスを含む ETL パイプライン基盤（差分取得、保存、品質チェック方針）。
      - DuckDB 上での最終取得日判定、範囲調整、backfill 処理などのユーティリティを実装。
    - src/kabusys/data/etl.py
      - pipeline.ETLResult を再エクスポート（公開インターフェース）。
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理（market_calendar）を実装。
      - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
      - calendar_update_job: J-Quants API から差分フェッチして market_calendar を冪等保存（バックフィル、健全性チェック含む）。
      - DB がまばらな場合の曜日ベースフォールバックを実装（カレンダー未登録日は土日判定で補完）。
  - 研究・ファクター計算
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB SQL + Python で計算する関数群を実装:
        - calc_momentum, calc_volatility, calc_value
      - 設計上、prices_daily / raw_financials のみ参照し外部 API/発注を行わない。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算: calc_forward_returns（任意ホライズン対応、入力検証あり）。
      - IC（Spearman ランク相関）計算: calc_ic。
      - ランク付けユーティリティ: rank（同順位は平均ランク）。
      - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - src/kabusys/research/__init__.py
      - 主要関数を公開。data.stats.zscore_normalize を再エクスポート。
  - AI（OpenAI を利用したニュースNLP・レジーム判定）
    - src/kabusys/ai/news_nlp.py
      - score_news: raw_news と news_symbols から記事を集約して銘柄別にニュースセンチメントを取得し、ai_scores テーブルへ書き込む。
      - ニュース収集ウィンドウ算出（JST ベース → UTC 変換）: calc_news_window。
      - バッチ処理（最大 20 銘柄 / リクエスト）、トリム（記事数・文字数制限）、JSON Mode での厳密レスポンス検証、応答バリデーション、±1.0 クリップを実装。
      - レート制限・ネットワーク・5xx に対する指数バックオフリトライを実装し、API 失敗時はフェイルセーフでスキップ（例外を波及させない設計）。
      - 部分成功時に既存スコアを保護するため、DELETE→INSERT の対象 code を絞って冪等的に書き換える。
    - src/kabusys/ai/regime_detector.py
      - score_regime: ETF 1321（Nikkei 225 連動 ETF）の 200 日 MA 乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・保存。
      - マクロキーワードによるタイトル抽出、gpt-4o-mini を用いた JSON レスポンスパース、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）を実装。
      - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT による冪等設計。失敗時は ROLLBACK を試行し例外を伝播。
  - 例外処理・堅牢性
    - OpenAI 呼び出しに対して RateLimitError / APIConnectionError / APITimeoutError / APIError のハンドリングとリトライを標準化。
    - JSON パース失敗時の復元ロジック（最外側の {} を抜き出す等）を実装し、LLM の非理想出力に耐性を持たせる。
    - DuckDB の executemany における空リスト制約に対応（空時は実行をスキップ）。
  - 内部ユーティリティ
    - 複数モジュールでテスト時に置換可能な _call_openai_api の抽象化を採用（unittest.mock.patch で差し替え可能）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 設計方針の強調
- ルックアヘッドバイアス防止: 日付算出で datetime.today()/date.today() を直接参照する処理を避け、target_date を明示的に受け渡す設計を採用。
- 冪等性: ETL・カレンダー更新・レジーム/AI スコア書き込み等は冪等操作（DELETE→INSERT、ON CONFLICT 相当）を基本とする。
- フェイルセーフ: 外部 API が失敗しても処理全体を停止させず、該当箇所のみフォールバック（既定値利用・スキップ）する方針。
- テスト容易性: OpenAI 呼び出しや .env 自動読み込みの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）、関数の分離によりユニットテストの差し替えが容易。

Security
- OpenAI API キーや各種トークンは環境変数経由で取得。必須変数が未設定の場合は ValueError を発生させ安全に検出できるようにしている。

---

今後の予定（例）
- strategy / execution / monitoring パッケージの実装（発注ロジック、監視・アラート機能）。
- パフォーマンス改善（大規模データ処理の最適化、並列化）。
- テストカバレッジの拡充と CI の整備。

もし特定ファイルや機能についてより詳細な CHANGELOG 項目（導入理由や既知の制約、後方互換性情報など）を追加したい場合は、対象箇所を指定してください。
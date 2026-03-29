# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-29

初回リリース。

### Added
- パッケージ初期化
  - kabusys パッケージを公開。バージョンを src/kabusys/__init__.py の `__version__ = "0.1.0"` で管理。
  - __all__ に data, strategy, execution, monitoring を公開モジュール候補として定義。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。`.env.local` は `.env` を上書き。
  - OS 側の既存環境変数を保護するための protected 処理を実装。
  - 自動読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト時に利用可能）。
  - .env のパースロジックを独自実装:
    - コメント、`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント扱いの挙動などに対応。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に:
    - 必須の環境変数取得は `_require()` を用い未設定時に ValueError を発生。
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティを提供（デフォルト値も設定）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG, INFO, ...）の検証を実施。
    - is_live / is_paper / is_dev のヘルパープロパティを提供。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルから対象ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）記事を集約し、銘柄ごとに OpenAI（gpt-4o-mini、JSON mode）へバッチ評価して ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、記事数制限、文字数トリム、JSON レスポンスのバリデーション、スコアの ±1.0 クリップを実装。
    - 429（レート制限）、ネットワーク断、タイムアウト、5xx に対する指数バックオフ（リトライ）を実装。その他のエラーはスキップして継続するフェイルセーフ設計。
    - テスト容易性のため OpenAI 呼び出し（_call_openai_api）の差し替え（unittest.mock.patch）を想定。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返却。
    - calc_news_window(target_date) を公開し、ニュース集計ウィンドウを計算可能。

  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する機能を実装。
    - マクロニュース抽出のためのキーワードリストを内蔵。最大取得記事数やモデル（gpt-4o-mini）、リトライポリシーを定義。
    - OpenAI API の呼出し失敗時は macro_sentiment = 0.0 で継続するフェイルセーフを採用。
    - DuckDB の prices_daily/raw_news/market_regime を参照し、計算結果を冪等に market_regime テーブルへ書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能。

- データプラットフォーム関連（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供し、
      - DB 登録がある場合は DB 値を優先、未登録日は曜日（平日）でフォールバックする一貫したロジックを実装。
      - 最大探索日数の上限を設け無限ループを回避。
    - calendar_update_job を実装し、jquants_client 経由で差分取得 → 保存（保存処理は jquants_client に委譲）を行う。バックフィル、健全性チェックを実装。
    - market_calendar が未取得の場合のフォールバック動作を明確化（曜日ベース）。

  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質チェック結果、エラー一覧など）を表現。
    - 差分更新、バックフィル、品質チェックの考え方に基づく設計（詳細は doc コメント）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比）、バリュー（PER, ROE）を計算する関数を実装。
    - 入力は DuckDB の prices_daily / raw_financials。データ不足時は None を返す設計。
    - calc_momentum, calc_volatility, calc_value を提供。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク付け（rank）、統計サマリー（factor_summary）を実装。
    - pandas など外部依存を使わず標準ライブラリと DuckDB のみで処理。
  - research パッケージの __init__.py で主要関数を再エクスポート（zscore_normalize は kabusys.data.stats からインポート）。

### Changed
- （初版のため変更履歴はなし）

### Fixed
- （初版のため修正履歴はなし）

### Notes / Implementation details
- DuckDB を中心とした設計で、関数は DuckDB 接続を受け取り SQL と Python を組み合わせて処理する方針。これにより外部 API 依存を排し、分析・テストが容易。
- 日時の扱いは全て明示的に行い、datetime.today() や date.today() に依存しない実装（ルックアヘッドバイアス防止）。news/score/regime 判定等は target_date を明示的に受け取る。
- OpenAI 呼び出しは JSON mode を活用し、レスポンスの堅牢なバリデーションとフォールバック（失敗時のスコア 0.0、あるいは処理のスキップ）を行うことで、API 変動に対する耐性を持たせている。
- テスト容易性を考慮し、AI モジュール内の API 呼び出し関数は差し替え可能（patch 対応）に設計。

### Security
- OpenAI API キー等の機密情報は環境変数で扱う前提。Settings は必須キー未設定時に ValueError を出すことで誤設定を早期発見できるようにしている。

---

（補足）今後のリリースでは、strategy / execution / monitoring の具体実装や、jquants_client の具体的な保存ロジック、テストカバレッジの追加、ドキュメントの整備などを予定しています。
# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" の慣例に従っています。  
各リリースには互換性のある変更性（Added, Changed, Fixed, Removed, Security, Deprecated）を明示します。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-03-28
初回公開リリース。日本株の自動売買システム用ユーティリティ群を提供する最小限の実装を含みます。

### Added
- パッケージの公開
  - pakage: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理
  - .env ファイルおよび環境変数から設定値を読み込む settings API を追加（src/kabusys/config.py）。
  - 自動 .env ロード機能（プロジェクトルート検出 .git / pyproject.toml ベース）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ実装（export 対応、クォート／エスケープ、インラインコメント処理、保護キー処理）。
  - Settings クラスで主要設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV / LOG_LEVEL 検証（development / paper_trading / live 等）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール（OpenAI を利用した自動センチメント評価）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）により銘柄単位のセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数・文字数上限、JSON mode（厳密 JSON）を採用。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行。
    - レスポンスの堅牢なバリデーションと数値のクリップ（±1.0）。
    - ai_scores テーブルへの冪等書き込み（DELETE → INSERT、部分失敗時の保護）。
    - テスト容易性のため _call_openai_api を差し替え可能に実装。
    - calc_news_window 関数でニュース集計ウィンドウ（JST基準）を提供。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF (1321) の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull / neutral / bear）。
    - prices_daily / raw_news / market_regime テーブルを利用し、計算結果を market_regime に冪等書き込み。
    - LLM 呼び出しに対する再試行・フォールバック（API失敗時 macro_sentiment=0.0）。
    - OpenAI の呼び出しはモジュール内で独立実装（news_nlp と意図的に分離し、モジュール結合を避ける）。
    - ルックアヘッドバイアス防止を設計方針に明示（date 比較は target_date 未満／排他等）。

- データプラットフォーム関連（DuckDB を利用）
  - ETL パイプライン用の ETLResult データクラスを追加（src/kabusys/data/pipeline.py）。
    - ETL の取得・保存件数、品質チェック結果、エラー概要などを保持。
    - to_dict により品質問題を (check_name, severity, message) 形式で出力可能。
  - ETL ヘルパー（差分更新・バックフィル・品質チェック設計）を実装（pipeline モジュールに詳細ロジック）。
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar を使った営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - カレンダー未取得時の曜日ベースフォールバック実装。
    - 夜間バッチ calendar_update_job による J-Quants からの差分取得と保存（バックフィル、健全性チェック）。
    - DuckDB の日付型変換ユーティリティ、テーブル存在チェック等を提供。
  - ETL API の公開出口: kabusys.data.etl は pipeline.ETLResult を再エクスポート。

- リサーチ（研究）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR・相対 ATR・20 日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（未実装の指標は注記）。
    - DuckDB SQL を用いた実装で、外部 API にアクセスしない安全設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 複数ホライズンの将来リターン（LEAD を用いた効率的取得）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。
    - rank: 同順位の平均ランクを扱うランク化ユーティリティ（小数丸めで ties を安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
  - research パッケージの __all__ で主要関数を公開（zscore_normalize など外部 utils と連携）。

- パッケージ構成・エクスポート
  - kabusys パッケージは data, strategy, execution, monitoring を __all__ に含む（初期化）。strategy / execution / monitoring の具体実装は将来追加予定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー未設定時は明示的に ValueError を投げ、無設定で API 呼び出しが行われないように安全策を実装（news_nlp / regime_detector）。

### Notes / 設計上のポイント
- ルックアヘッドバイアス防止: datetime.today()/date.today() を解析処理の基準日として直接参照しない設計（target_date を明示的に渡す）。
- DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT 使用の想定、トランザクション管理）。
- OpenAI 呼び出しは JSON mode を使い厳密な構造を期待するが、レスポンスパース失敗に対する復元ロジックも備える（外側の {} 抽出など）。
- テスト容易性: OpenAI 呼び出し関数は差し替え可能にしてユニットテストでモックできるように実装。
- DuckDB をデータ格納・解析の中心に採用。

---

参考: 各モジュールの詳細な API と挙動はソースコードの docstring を参照してください。今後、機能追加・改善（発注・監視ロジック・ストラテジ実装・エンドツーエンドテストサポート等）を予定しています。
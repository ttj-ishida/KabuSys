# Keep a Changelog
すべての注記はセマンティックバージョニングに準拠します。  
このファイルは主にユーザ向けの変更点サマリ（機能追加・変更・修正）を示します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回公開リリース。

### Added
- パッケージ初期構成を導入
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境 / 設定管理
  - Settings クラスを提供して環境変数からアプリ設定を取得可能に（src/kabusys/config.py）。
  - .env 自動読み込み機能を実装:
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサーは export KEY=val フォーマット、クォートやインラインコメント、エスケープに対応。
    - override と protected による上書き保護のサポート。
  - 必須設定取得用の _require 関数と各種プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を参照。
    - DB パス設定（DUCKDB_PATH, SQLITE_PATH）、実行環境 (KABUSYS_ENV) とログレベル検証 (LOG_LEVEL) を実装。
    - is_live/is_paper/is_dev ヘルパー。

- AI（自然言語処理）モジュール
  - ニュース NLU スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとのニュースを結合し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメント（ai_score）を計算。
    - チャンク単位（最大 20 コード）での API コール、最大記事数・最大文字数でのトリム、JSON Mode 利用。
    - レスポンスの厳密な検証（JSON 抽出、results 配列、code と score の型チェック、スコアの有限性、±1.0 クリップ）。
    - リトライ/バックオフ戦略（429・ネットワーク断・タイムアウト・5xx を対象）とフェイルセーフ（失敗時はスキップして継続）。
    - calc_news_window(target_date) により JST ベースのニュースウィンドウ算出（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - テスト容易性のため _call_openai_api を独立実装し patch で差し替え可能。
    - ai_scores テーブルへの冪等性を考慮した DELETE→INSERT の置換実装。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（Nikkei 連動 ETF）の 200 日移動平均乖離とマクロニュースの LLM センチメントを組み合わせて日次レジーム（bull/neutral/bear）を判定。
    - MA200 乖離計算（_calc_ma200_ratio）、マクロキーワードでのニュース抽出（_fetch_macro_news）、LLM スコアリング（_score_macro）を実装。
    - スコア合成は重み付け（MA 70% / マクロ 30%）・スケーリング・クリッピングを適用。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装し、失敗時はロールバックを試行。
    - API 呼び出しの分離によりテスト容易性とモジュール結合の低減を実現。

- データプラットフォーム周辺 (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを扱うユーティリティ群を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供（DB の有無に応じて曜日ベースのフォールバック）。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・健全性チェックを行い、冪等に保存。
    - 最大探索日数等の安全ガードを用意。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスによる ETL 実行結果の集約（品質チェック結果・エラー情報含む）。
    - 差分取得、backfill、品質チェック連携（quality モジュール）、jquants_client 経由の保存を想定した設計。
    - _get_max_date 等の DB ヘルパーを実装。

- リサーチ / ファクター解析 (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、バリュー（PER、ROE）等の計算関数を追加。
    - DuckDB に対する SQL + Python 実装で、prices_daily / raw_financials を参照。
    - データ不足時は None を返す等の堅牢性を確保。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン calc_forward_returns、IC（calc_ic）、rank、統計サマリー factor_summary を実装。
    - pandas 等に依存せず、標準ライブラリのみで実装。
  - re-export: 主要関数をパッケージ初期化で公開（src/kabusys/research/__init__.py）。

- パッケージエクスポート整理
  - ai、research、data など主要モジュールで __all__ を整理して公開 API を明確化。

### Changed
- （初回リリースのため該当なし）

### Fixed
- フェイルセーフ / ロバストネス強化
  - OpenAI API 呼び出しでのリトライ/バックオフロジックを実装し、429/タイムアウト/ネットワーク断/5xx で安全にフォールバックするようにした（news_nlp, regime_detector）。
  - JSON パース失敗時に備え、文字列から最外の JSON オブジェクトを抽出して復元するロジックを追加（news_nlp）。
  - DuckDB の executemany に空リストを渡せない制約への対応として、空チェックを行う処理を導入（news_nlp）。
  - market_regime / ai_scores への書き込みでトランザクションとロールバック処理を確実に実行。

### Security
- （該当なし）

Notes / 設計方針（抜粋）
- LLMや日次集計処理では datetime.today()/date.today() の直接参照を避け、target_date を引数で与える設計によりルックアヘッドバイアスを排除。
- 外部 API 呼び出しは明示的に分離（_call_openai_api をモック可能）してテスト容易性を確保。
- DB 書き込みは冪等化（DELETE→INSERT / ON CONFLICT での上書き想定）およびトランザクション制御で安全に実行。

以上が本リリース（0.1.0）の主要追加・設計上のハイライトです。今後の変更はここに追記します。
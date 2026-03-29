CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ 日本語訳に準拠

未リリース
--------

（現在のところ未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買向け基盤ライブラリを追加。
  - パッケージ情報
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - __all__ として data, strategy, execution, monitoring を公開。

- 環境設定 / 起動処理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォートのバックスラッシュエスケープ処理対応。
    - インラインコメント処理（クォートあり / なしの扱いを区別）。
  - ファイル読み込み時の上書き制御（override）と保護キー(protected)をサポート。
  - Settings クラスを提供し、環境変数から以下を安全に取得:
    - J-Quants / kabu ステーション用設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL）
    - Slack 設定（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - DB パス既定値（DUCKDB_PATH, SQLITE_PATH）
    - 実行環境判定（KABUSYS_ENV: development/paper_trading/live）およびログレベル検証
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール（src/kabusys/ai）
  - ニュース NLV スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを統合評価。
    - タイムウィンドウ計算（JST 基準）: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC に変換して DB と比較）。
    - 1 チャンク最大 20 銘柄で OpenAI (gpt-4o-mini) の JSON モードへ送信。
    - 再試行ポリシー: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - レスポンス検証とスコアクリップ（±1.0）。
    - 書き込みはトランザクション（DELETE → INSERT）で行い、DuckDB executemany の制約に配慮。
    - API キー注入対応（api_key 引数 or 環境変数 OPENAI_API_KEY）。
    - テスト容易性: OpenAI 呼び出し箇所は差し替え可能（ユニットテストで patch 可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成。
    - マクロ記事抽出はキーワードベースで raw_news から取得（最大 20 件）。
    - OpenAI による macro_sentiment を取得し、ブレンドして regime_score を計算。
    - 判定ラベル: bull / neutral / bear（閾値あり）。
    - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API エラーはフォールバック（macro_sentiment=0.0）して処理継続。API キー注入対応。

- データ処理（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を利用した営業日判定ロジックを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得 → 冪等保存（ON CONFLICT DO UPDATE）を実装。バックフィル・健全性チェックあり。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL の差分取得・保存・品質チェックのための基盤を実装。
    - ETLResult データクラスを公開（ETL 成果・品質問題・エラー情報を格納）。
    - jquants_client と quality モジュールを組み合わせた差分 ETL の設計方針を反映。
    - _get_max_date 等ユーティリティを提供。
  - data パッケージ API を整理して公開（etl で ETLResult を再エクスポート）。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M）、200 日 MA 乖離、Volatility（20 日 ATR）、Liquidity 指標、Value（PER/ROE）を DuckDB クエリで計算。
    - データ不足時は None を返す設計、結果は (date, code) をキーとする dict のリスト。
    - DuckDB のウィンドウ関数を活用して効率的に算出。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、必要十分なデータ件数チェック）。
    - ランク変換 rank（同順位は平均ランクを採用し丸めで ties を安定化）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median 計算）。
  - research パッケージ __init__ で主要関数を再公開。

Changed
- 設計方針の明示的適用:
  - すべての AI / 研究モジュールは datetime.today()/date.today() を直接参照せず、外部から target_date を与えてルックアヘッドバイアスを排除。
  - OpenAI 呼び出しの失敗時はフェイルセーフで処理を継続（部分失敗が全体を止めない設計）。

Fixed
- （初版につき既存バグ修正履歴はなし。実装上の頑健性向上措置を多数適用: リトライ、トランザクション保護、入力検証、空リスト処理回避など）

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で required として参照されるため、実行時に未設定だと ValueError が発生します。
  - OpenAI を使う機能（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY が必要。
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - いずれも展開時に expanduser() が適用されます。
- 自動 .env ロード:
  - プロジェクトルートが .git または pyproject.toml によって特定される場合、起動時に .env → .env.local の順で読み込み（.env.local が上書き）。
  - OS 環境変数は保護され、override による上書きを防止。
- テストのしやすさ:
  - OpenAI 呼び出し箇所は内部 _call_openai_api を patch してモック可能。
  - 環境読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

既知の制約
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンがあるため、空パラメータのチェックを実装している。
- OpenAI レスポンスは JSON mode を使うが、稀に余計な前後テキストが混入する可能性があり、復元ロジック（最外側の {} を抽出）を実装している。完全な堅牢性は OpenAI 側の応答次第。

今後の予定（想定）
- strategy / execution / monitoring 周りの高レベル機能実装（現時点では基盤モジュールを中心に提供）。
- 追加の品質チェックルールや jquants_client 連携の強化。
- 単体テストと CI 設定の充実（OpenAI 呼び出しモックのテストケース整備）。

--- 

注: 上記は現行コードベースの実装内容から推測して作成した CHANGELOG です。リリース日時や文章は実際のリリース手順に合わせて調整してください。
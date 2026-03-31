# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトのセマンティックバージョニングは https://semver.org/ に準拠します。

## [Unreleased]

（該当なし）

## [0.1.0] - 2026-03-31

初回公開リリース。以下の主要機能・実装を含みます。

### Added
- パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - __all__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込み可能。
  - プロジェクトルートの自動検出（.git または pyproject.toml を探索）に基づく .env / .env.local 自動ロードを実装。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理対応。
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合に # をコメントとみなす）。
    - 無効行のスキップ、読み込み失敗時に warnings を出力。
  - 自動ロード時の優先順位: OS環境変数 > .env.local > .env（.env.local は override=True）。
  - Settings クラスを提供し、以下のプロパティでアプリ設定を取得可能（必須キーは未設定時に ValueError を発生）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live, is_paper, is_dev のブール判定ユーティリティ

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols をもとに銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - 処理仕様:
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で扱う）。
      - バッチサイズ: 最大 20 銘柄/コール。
      - 1 銘柄あたり最大記事数: 10 件（最新順）。
      - 1 銘柄テキストは最大 3000 文字にトリム。
      - レスポンスは JSON Mode を期待し、レスポンスのバリデーションを実施（results 配列、code/score 検証）。
      - スコアは ±1.0 にクリップ。
      - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（最大設定あり）。
      - 部分成功保護: ai_scores への書き込みはスコア取得済みコードのみを DELETE → INSERT（executemany）で置換。DuckDB の executemany 空リスト制約を考慮してガード。
    - 公開関数:
      - calc_news_window(target_date) → (window_start, window_end)
      - score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、news_nlp によるマクロセンチメント（重み30%）を合成して市場レジームを日次判定（'bull' / 'neutral' / 'bear'）。
    - 処理仕様:
      - ma200_ratio は target_date より前のデータのみで計算（ルックアヘッド防止）。
      - マクロ記事はマクロキーワードでフィルタ（デフォルトキーワードリストあり）、最大 20 件取得。
      - OpenAI（gpt-4o-mini）に JSON モードで問い合わせ、macro_sentiment を取得。API失敗時は macro_sentiment=0.0 のフェイルセーフで継続。
      - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
      - 書き込みは market_regime テーブルへ冪等に（BEGIN / DELETE / INSERT / COMMIT）行う。失敗時は ROLLBACK。
    - 公開関数:
      - score_regime(conn, target_date, api_key=None) → 1（成功時）
    - OpenAI 呼び出しはモジュール内実装で、news_nlp と内部関数を共有しない（モジュール結合を避ける設計）。

- Research（因子・特徴量探索）モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum, Value, Volatility, Liquidity などの定量ファクターを DuckDB の prices_daily / raw_financials を参照して計算する関数を実装。
    - 代表的なメソッド:
      - calc_momentum(conn, target_date): mom_1m, mom_3m, mom_6m, ma200_dev（200日未満は None）
      - calc_volatility(conn, target_date): atr_20（20日ATR平均）、atr_pct、avg_turnover、volume_ratio（20日窓）
      - calc_value(conn, target_date): per, roe（raw_financials の直近レポートを参照）
    - 設計指針: DB（prices_daily / raw_financials）のみを参照、外部 API にはアクセスしない。結果は list[dict]（date, code, ...）で返却。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - calc_forward_returns は任意ホライズン（デフォルト [1,5,21]）を受け取り、一度のクエリでまとめて取得する最適化を実施。
    - calc_ic は Spearman（ランクの Pearson）を自己実装し、欠損や同順位（ties）を適切に処理。
    - factor_summary は count/mean/std/min/max/median を返すユーティリティ。

- Data（データ基盤）モジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX マーケットカレンダーを管理するロジックを提供。
    - 提供関数:
      - is_trading_day(conn, d), is_sq_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(conn, start, end)
      - calendar_update_job(conn, lookahead_days=90): J-Quants API から差分取得し market_calendar を冪等更新。バックフィル（直近 7 日）と健全性チェック（最大未来日数制限）を実施。
    - 設計方針:
      - market_calendar データがない／部分的な場合は曜日ベースでフォールバック（週末は非営業日）。
      - DB 登録値が優先され、未登録日は曜日ベースで補完。next/prev_trading_day は _MAX_SEARCH_DAYS（60日）で探索上限を設ける。
  - ETL パイプライン（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを公開（src/kabusys/data/etl.py で再エクスポート）。
    - ETL の設計:
      - 差分取得（最終取得日からの未取得分）、backfill（デフォルト 3 日）をサポート。
      - 保存は jquants_client 経由で冪等に保存（ON CONFLICT DO UPDATE）する想定。
      - 品質チェック（quality モジュール）を呼び出して品質問題を収集し、呼び出し元が判断できるようにする（Fail-Fast にはしない）。
    - ETLResult は処理の統計（fetch/save/counted entities）、quality_issues、errors を保持し、has_errors / has_quality_errors / to_dict を提供。

- 公開 API エントリポイント・再エクスポート
  - kabusys.ai.__init__ にて score_news を公開。
  - kabusys.research.__init__ で主要関数（calc_momentum 等）と zscore_normalize（data.stats 由来）を公開。
  - kabusys.data.etl は ETLResult を再エクスポート。

### Changed
- （初期リリースのため変更履歴なし）

### Fixed
- （初期リリースのため修正履歴なし）

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError を発生させ明示的にエラーにすることで誤動作を防止。

---

注記:
- 多くの処理は「ルックアヘッドバイアスを防ぐ」設計指針に従い、内部で datetime.today() / date.today() を直接参照せず、target_date ベースでの計算を行います。
- OpenAI 呼び出しや外部 API 呼び出しはネットワーク障害や 5xx に対してリトライロジック・フェイルセーフ（失敗時はスコア 0.0 やスキップ）を備えています。
- DuckDB のバージョン差異（executemany の空リスト制約等）を考慮した実装が各所にあります。
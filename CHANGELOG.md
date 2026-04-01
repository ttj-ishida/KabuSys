# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-01

### Added
- 初回リリースとして以下の主要機能を実装・公開。
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 に設定 (src/kabusys/__init__.py)。
  - パブリック API として "data", "strategy", "execution", "monitoring" をエクスポート。

- 設定 / 環境変数管理
  - .env ファイルおよび環境変数から設定を読み込む設定モジュールを追加 (src/kabusys/config.py)。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）と .env.local による上書きサポート。
  - _parse_env_line による堅牢な .env パース実装（export 形式、クォート / バックスラッシュエスケープ、インラインコメント処理など）。
  - Settings クラスを公開（必須環境変数取得メソッド _require、各種プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, Slack 設定、DB パス、監視閾値、環境/ログレベル検証等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値は "development", "paper_trading", "live" および標準ログレベル）。

- AI（OpenAI）連携: ニュース NLP と市場レジーム判定
  - ニュースセンチメント集計モジュール (score_news) を追加 (src/kabusys/ai/news_nlp.py)。
    - 指定タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事集約、銘柄ごとのテキスト結合とトリミング、バッチ送信（最大20銘柄）。
    - OpenAI（gpt-4o-mini）への JSON Mode 呼び出しとレスポンス検証（results 配列のバリデーション、スコアの ±1.0 クリップ）。
    - レート制限・ネットワーク障害・5xx を対象とした指数バックオフリトライ（最大回数・安全なフォールバック）。
    - DuckDB への冪等書き込み（DELETE → INSERT、トランザクション、ROLLBACK 保護）。
    - テスト用に _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定モジュール (score_regime) を追加 (src/kabusys/ai/regime_detector.py)。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算におけるルックアヘッドバイアス回避（target_date 未満データのみを使用）。
    - マクロキーワードに基づく raw_news フィルタ、OpenAI 呼び出し（JSON パース・リトライ・フェイルセーフ）および結果のクリップとテーブル書き込み。
    - 失敗時マクロセンチメントを 0.0 として継続するフェイルセーフ設計。

- データ関連（DuckDB ベース）
  - ETL パイプラインの結果型 ETLResult を公開 (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)。
    - ETL 実行結果を保持するデータクラス（取得／保存件数、品質問題、エラー一覧、シリアライズ）。
  - カレンダー管理モジュールを追加 (src/kabusys/data/calendar_management.py)。
    - market_calendar テーブルを使用した営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、最大探索日数上限による安全対策。
    - J-Quants クライアント経由での夜間バッチ更新 job（calendar_update_job）とバックフィル、健全性チェック実装。

- Research（因子・特徴量探索）
  - ファクター計算モジュール (src/kabusys/research/factor_research.py) を追加。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR、20 日平均売買代金、出来高比率等。
    - calc_value: raw_financials からの EPS/ROE を用いた PER / ROE 計算（未実装項目の注記あり）。
    - DuckDB ベースでの窓関数利用実装、営業日/スキャン範囲のバッファ等。
  - 特徴量探索モジュール (src/kabusys/research/feature_exploration.py) を追加。
    - calc_forward_returns: 指定ホライズンでの将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマン順位相関（IC）計算（3 銘柄未満は None）。
    - rank: 同順位は平均ランクを返すランク関数（丸めで ties の誤検出を防止）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。

- 一般的な設計上の特徴（複数モジュール）
  - DuckDB を第一選択のストレージとして利用、SQL＋Python で計算。
  - ルックアヘッドバイアス回避: datetime.today()/date.today() をスコープ内で直接参照しない実装方針（関数に target_date を明示的に渡す）。
  - API 呼び出しの堅牢化: リトライ、指数バックオフ、5xx の扱い分離、タイムアウト設定。
  - データ不足や API エラー時は例外を投げずにフェイルセーフ（デフォルト値やスキップ）する設計を優先。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を用いて冪等性と一貫性を確保。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- .env ロード時に現在の OS 環境変数を保護する protected キーセットを導入（.env.local/.env による誤上書きを防止）。
- OpenAI API キーは引数で注入可能、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を明示的に発生させることで誤動作を防止。

### Notes / Migration
- 公開 API の主要要素:
  - 設定: kabusys.config.settings（Settings インスタンス）
  - AI: kabusys.ai.score_news, kabusys.ai.score_regime
  - データ: kabusys.data.ETLResult（再エクスポート）
  - Research: kabusys.research.calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（zscore は kabusys.data.stats から）
  - カレンダー: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job

- 動作環境・前提:
  - DuckDB を用いたテーブル構造（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が前提。
  - OpenAI の JSON Mode（chat.completions.create、response_format={"type":"json_object"}）を利用するため、SDK バージョン差異に注意。テスト用に _call_openai_api をモック可能。
  - .env パーサは一般的なケースをカバーするが極端に複雑な .env 構文（複数行クォート等）は想定外の挙動となる可能性あり。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装と発注ロジックの追加
- モデル評価用のユーティリティや CI 用のデータフィクスチャ整備
- ドキュメント（Usage / Deployment / DB Schema）とサンプル ETL 実行手順の追加

（以上）
# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
- 現在のブランチに未リリースの変更はありません。

## [0.1.0] - 2026-03-28
初回公開リリース。

### Added
- パッケージ初期化
  - kabusys パッケージの基本構成を追加。公開 API: data, strategy, execution, monitoring（src/kabusys/__init__.py）。
  - バージョン定義 __version__ = "0.1.0" を追加。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 行パーサーを実装（コメント・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープに対応）。
  - Settings クラスを実装し、以下の設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development | paper_trading | live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - 環境変数未設定時は明確な ValueError を送出。

- ニュース NLP（OpenAI 統合）（src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py）
  - raw_news / news_symbols を読み、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini, JSON Mode）へ送信しセンチメントを算出。
  - バッチ処理（デフォルト 20 銘柄/リクエスト）、記事数・文字数制限、リトライ（429・ネットワーク・タイムアウト・5xx へ指数バックオフ）を実装。
  - レスポンス検証ロジックを実装（JSON 抽出、results 配列の検証、未知コードの無視、数値変換、±1.0 クリップ）。
  - ai_scores テーブルへの冪等的な書き込み（該当コードのみ DELETE → INSERT）。
  - calc_news_window 関数でニュース取得ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算。
  - テスト向けに _call_openai_api をパッチ可能にして API 呼び出しを差し替え可能。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
  - ルックアヘッドバイアスを避ける設計（target_date 未満のみ使用、datetime.today() を参照しない）。
  - OpenAI 呼び出しは独立実装でテスト時に差し替え可能。API エラー時は macro_sentiment=0.0 としてフェイルセーフで継続。
  - 結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- データ基盤（src/kabusys/data/*）
  - ETL パイプラインの結果を表す ETLResult データクラスを追加（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py で公開）。
    - ETL の取得・保存件数、品質問題リスト、エラーメッセージなどを保持。has_errors / has_quality_errors / to_dict を提供。
  - JPX（市場）カレンダー管理モジュールを実装（src/kabusys/data/calendar_management.py）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 値優先の一貫したロジック、探索最大日数の防止を実装。
    - calendar_update_job により J-Quants API から差分取得して冪等保存（バックフィル・健全性チェック含む）。
  - ETL パイプラインの基本ユーティリティ（差分取得、最大日付取得、テーブル存在チェック）を実装。

- リサーチ機能（src/kabusys/research/*）
  - Factor 計算モジュールを実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA）を算出。
    - calc_value: per / roe を raw_financials と prices_daily を使って算出。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を算出。
  - Feature 探索モジュールを実装:
    - calc_forward_returns: 任意ホライズンの将来リターン（LEAD を使用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクで取り扱うランク変換実装。
  - zscore_normalize は kabusys.data.stats から再公開（研究 API の一部として）。

### Changed
- 設計方針の明確化
  - ほとんどのモジュールで「ルックアヘッドバイアス回避」のために datetime.today()/date.today() を直接参照しない実装方針を採用（target_date を明示的に受け取る設計）。
  - OpenAI 呼び出し周りは冪等性・堅牢性を重視し、エラー時のフォールバックやリトライ戦略を統一。

### Fixed
- DuckDB 互換性対応
  - executemany に空リストを渡せない DuckDB（0.10 系）への対応（空の場合は実行をスキップ）を実装して部分失敗時の既存データ保護を実現。

### Security
- 環境変数の必須チェックを厳格化。必須値が未設定の場合は ValueError を返すことで安全な起動失敗を実現。
- .env 読み込み時に OS 環境変数を保護（protected set）する仕組みを導入。

### Notes / Usage & Migration
- 必要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（または各関数の api_key 引数）
  - オプション: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_DISABLE_AUTO_ENV_LOAD
- OpenAI API
  - モデル: gpt-4o-mini を使用。JSON Mode を期待するプロンプト設計になっているため、API 応答は厳密な JSON を返すことを前提とする（ただし実運用では前後ノイズ除去処理を行う）。
  - テスト時は内部の _call_openai_api を patch することで外部 API 呼び出しを差し替え可能。
- データベース（DuckDB）
  - 期待されるテーブル: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等。
  - ETLResult や pipeline のユーティリティは ETL 実行フローでの品質チェックとエラー集約を容易にする。
- ルックアヘッドバイアス回避
  - 全てのデータ処理関数は target_date を受け取り、内部クエリは target_date より前のデータに制限するなどルックアヘッド防止を心がけた設計になっています。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充（現在は API の公開面を準備済み）
- テストカバレッジ拡大、API 呼び出しの堅牢化、性能改善（大量銘柄のバッチ処理最適化）

(本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートはプロジェクトの意思決定に基づいて調整してください。)
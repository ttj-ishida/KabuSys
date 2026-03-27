# Changelog

すべての注目すべき変更履歴をこのファイルに記録します。  
このプロジェクトは Keep a Changelog 準拠でバージョン管理を行っています。  

- 表記: 日付は YYYY-MM-DD 形式
- 影響範囲: public API や挙動に影響する点を中心に記載

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-27

初回公開リリース。以下の主要機能・モジュールを実装しています。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - __all__ に data, strategy, execution, monitoring をエクスポート（パッケージ公開インターフェース）
  - バージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）
  - .env パーサー（引用符・エスケープ・export プレフィックス・コメント処理をサポート）
  - 読み込み順序: OS 環境 > .env.local（override=True）> .env（override=False）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）
  - Settings クラスを公開（以下の主要プロパティを提供）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev の補助プロパティ

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出
    - チャンク処理（最大 20 銘柄/コール）、1 銘柄あたり記事数と文字数上限、JSON Mode を利用した厳密なレスポンス期待
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装
    - レスポンスバリデーション（results 配列・code/score の型検査・既知コードフィルタ・有限数値チェック）
    - DuckDB へは部分置換（DELETE / INSERT）で冪等/部分失敗耐性を確保
    - ルックアヘッドバイアスを避ける設計（datetime.today() を内部参照しない）
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定
    - マクロ記事はキーワードベースで抽出（複数キーワードリストを定義）
    - OpenAI 呼び出しは JSON レスポンスを期待、API エラー時は macro_sentiment = 0.0（フェイルセーフ）
    - DuckDB へは冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行い、書き込み失敗時は ROLLBACK を試行
    - API キーは引数または環境変数 OPENAI_API_KEY で注入

- 研究（research）モジュール
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を DuckDB の prices_daily から計算
    - calc_volatility: 20日 ATR、ATR/株価比、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials（report_date <= target_date）と当日の株価を組み合わせて PER, ROE を算出
    - 各関数はデータ不足時に None を返す設計
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（例: [1,5,21]）に対する将来リターンを算出（LEAD を利用）
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（ランクは平均ランク処理、重複値対応）
    - rank: 値リストを平均ランクに変換（round(..., 12) による誤差吸収）
    - factor_summary: count/mean/std/min/max/median を算出
  - research.__init__ で主要関数を再エクスポート（public API として利用可能）

- データプラットフォーム（data）モジュール
  - calendar_management
    - market_calendar テーブルを用いた営業日判定 API を提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB に値がない場合は曜日ベースのフォールバック（週末は非営業日）
    - calendar_update_job: J-Quants API（jquants_client）から差分取得・バックフィルして market_calendar を更新（健全性チェックあり）
    - 最大探索日数やバッファ等の安全設計（_MAX_SEARCH_DAYS, _BACKFILL_DAYS 等）
  - pipeline（ETL）
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラーログを保持）
    - 差分更新、バックフィル、品質チェック（kabusys.data.quality を想定）による ETL の設計方針を実装
    - _get_max_date / _table_exists 等のユーティリティ実装
  - etl.py は pipeline.ETLResult を再エクスポート

### Changed
- （該当なし：初回リリース）

### Fixed / Robustness improvements
- DuckDB 互換性や部分失敗を考慮した実装
  - executemany に空リストを渡さないようチェックを追加（DuckDB 0.10 の制約対策）
  - ai_scores / market_regime への書き込みは対象 code を限定して DELETE → INSERT を実行し、部分失敗時に既存レコードを保護
  - トランザクション処理時に例外が発生した際、ROLLBACK を試行し、ROLLBACK 自体の失敗は警告ログで報告
- LLM レスポンスのパースに対する回復処理
  - JSON モードでも前後に余計なテキストが混入する可能性を考慮して最外側の {} を抽出してパースを試みる実装
  - レスポンスに不整合がある場合は空スコア／macro_sentiment=0.0 にフォールバックし、例外を上位へ投げない（ロバストネス確保）

### Security
- （該当なし：初回リリース）

### Notes / Migration / Usage
- 必須環境変数（例）
  - OPENAI_API_KEY（AI モジュールを利用する場合）
  - JQUANTS_REFRESH_TOKEN（J-Quants 関連）
  - KABU_API_PASSWORD（kabu ステーション接続）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知を行う場合）
- データベーススキーマ（期待するテーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime などが各モジュールで参照されます。ETL での初回ロードやスキーマ準備が必要です。
- 設計上の重要点
  - ルックアヘッドバイアス回避のため、いずれの処理も内部で datetime.today() / date.today() を参照しない（全て target_date を明示的に指定する設計）
  - OpenAI 呼び出しは JSON Mode を期待するが、失敗時はフェイルセーフ（スコア 0.0 / スキップ）で継続するようになっています
  - 自動 .env 読み込みはプロジェクトルートに依存（.git / pyproject.toml を起点）。意図的に無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

---

今後のリリースでは、strategy / execution / monitoring の具現化、テストカバレッジの追加、外部 API クライアント（J-Quants/kabu ステーション）の具体実装や実運用用の監視・ロギング強化を予定しています。
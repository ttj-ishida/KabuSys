# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠して作成しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

未リリースの変更は "Unreleased" に記載します。各リリースには主な公開 API、構成、既知の制約や設計方針の要点を記載しています。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-31
初回リリース — 日本株自動売買・データ基盤のプロトタイプ実装

### Added
- パッケージ基盤
  - kabusys パッケージの初期実装を追加。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数/.env の自動読み込み機能を実装（src/kabusys/config.py）。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env のパースは export 形式、クォート、行末コメント等に対応。
    - 必須設定取得ヘルパー _require と Settings クラスを提供。
    - 主要な設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
      - SQLITE_PATH (デフォルト data/monitoring.db)
      - PID_FILE_PATH, CPU/MEMORY/DISK 閾値
      - KABUSYS_ENV (development / paper_trading / live)、LOG_LEVEL

- AI モジュール (OpenAI ベース)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄毎のセンチメントを生成。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）。
    - 再試行ロジック（429/ネットワーク/タイムアウト/5xx に対して指数バックオフ）。
    - レスポンスの厳密バリデーション（JSON 抽出・results 配列・code/score 検証）。
    - 結果は ai_scores テーブルへ冪等書き込み（該当コードのみ DELETE → INSERT）。
    - テスト容易性のため _call_openai_api をモック可能に実装。
    - 公開関数: score_news(conn, target_date, api_key=None)、calc_news_window(target_date)。
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離 (70%) とマクロニュース LLM センチメント (30%) を合成して日次レジーム判定（bull/neutral/bear）。
    - マクロキーワードで raw_news をフィルタリングし、OpenAI で macro_sentiment を算出（最大 20 記事）。
    - 計算は look-ahead 回避（target_date 未満のデータのみ使用）。
    - API エラーはフェイルセーフとして macro_sentiment=0.0 にフォールバック。
    - DB への書き込みは冪等に実施（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性のため _call_openai_api をモック可能に実装。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

- データモジュール
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを導入して ETL 実行結果を集約（対象日・取得/保存件数・品質問題・エラー等）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（J-Quants クライアント呼び出しを想定）。
    - ETLResult.to_dict により品質問題を辞書化して出力可能。
    - ETLResult を re-export（src/kabusys/data/etl.py）。

  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX 市場カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアントから取得し保存）。
    - 営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーがない場合は曜日ベースでフォールバック（土日非営業日）。
    - 最大探索日数・バックフィル・健全性チェック等を実装。
    - J-Quants クライアント呼び出しは kabusys.data.jquants_client 経由を想定。

- リサーチモジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離等を計算。
    - calc_volatility: 20日ATR、ATR比、平均売買代金、出来高比等を計算。
    - calc_value: PER・ROE を raw_financials と prices_daily から計算。
    - 全関数は DuckDB の prices_daily / raw_financials を参照し、外部 API にはアクセスしない。
    - 結果は (date, code) キーを持つ辞書リストで返す。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズンの将来リターン計算（horizons デフォルト [1,5,21]）。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を計算。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ。
    - factor_summary: カラム単位の count/mean/std/min/max/median を算出。
    - pandas 等に依存せず標準ライブラリで実装。

- データユーティリティ
  - calendar/ETL/pipeline などで DuckDB を主な DB として利用する設計を採用。
  - 各モジュールは DuckDBPyConnection を明示的に受け取り、テスト容易性を向上。

### Fixed
- 初回リリースのため特定の「修正」はありません（設計・実装上の注意点をドキュメントに反映）。

### Known limitations / Notes
- OpenAI 呼び出しは gpt-4o-mini を前提としており、API キー (OPENAI_API_KEY) の設定が必須。キー未設定時は ValueError を送出する設計。
- DuckDB 0.10 系に対する互換性配慮（executemany に空リストを渡さない等）を実装。
- 日時の取り扱いはすべて timezone-naive の date / datetime を想定（UTC/ JST の変換ルールはモジュール内で明示的に扱う）。
- 一部処理（AI 呼び出し・外部 API）では失敗時にフェイルセーフ（スコア 0 やスキップ）で継続する設計。重要な障害はログに記録されるが、部分失敗を許容する挙動になっている。
- market_calendar テーブルが欠落しているケースでは曜日フォールバックを使用するため、厳密な祝日判定が行われない可能性がある。カレンダーの定期取得（calendar_update_job）を推奨。

### Security
- .env の自動読み込みを行うが、既存 OS 環境変数は保護（上書きされない）されるロジックを実装。
- 自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を提供しており、CI/テスト環境での注入を制御可能。

### Public API（主要関数 / クラス）
- settings: Settings インスタンス（kabusys.config）
- score_news(conn, target_date, api_key=None) — ニュース NLP スコア生成（kabusys.ai.news_nlp）
- score_regime(conn, target_date, api_key=None) — 市場レジーム判定（kabusys.ai.regime_detector）
- calc_news_window(target_date) — ニュースの収集ウィンドウ（kabusys.ai.news_nlp）
- ETLResult（kabusys.data.pipeline）
- calendar_update_job(conn, lookahead_days=...)（kabusys.data.calendar_management）
- is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
- calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
- calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）

---

今後の予定（例）
- AI レスポンスのさらなる堅牢化（多様な出力形式への対応）。
- 単体テスト、統合テストの整備（外部 API 呼び出しのモックを含む）。
- ドキュメント（API リファレンス、運用手順）の充実。

--- 

（注）本 CHANGELOG は提供されたコード内容から実装・設計意図を推測して作成しています。実際のリリースノート作成時は開発履歴・コミットログ等と突き合わせて調整してください。
# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベースから推測した初期リリースの変更履歴を日本語で記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - public モジュール群を __all__ で公開: data, strategy, execution, monitoring

- 環境設定
  - 環境変数 / .env 読み込みユーティリティを実装（src/kabusys/config.py）。
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val やクォート・エスケープ、コメントの取り扱いに対応する独自パーサを実装。
    - Settings クラスを提供し、以下の設定プロパティを公開:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN) — 必須
      - kabu_api_password (KABU_API_PASSWORD) — 必須
      - kabu_api_base_url (KABU_API_BASE_URL, デフォルト http://localhost:18080/kabusapi)
      - slack_bot_token (SLACK_BOT_TOKEN) — 必須
      - slack_channel_id (SLACK_CHANNEL_ID) — 必須
      - duckdb_path (DUCKDB_PATH, デフォルト data/kabusys.duckdb)
      - sqlite_path (SQLITE_PATH, デフォルト data/monitoring.db)
      - env (KABUSYS_ENV: development|paper_trading|live, 検証あり)
      - log_level (LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL, 検証あり)
      - is_live / is_paper / is_dev ブール属性

- AI（自然言語処理）機能
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを算出。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）・トークン肥大化対策（記事数・文字数トリム）を実装。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実施。
    - レスポンスの厳密なバリデーション・クリップ（±1.0）を行い、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - 主要公開 API: score_news(conn, target_date, api_key=None)
    - 時間ウィンドウ計算ユーティリティ: calc_news_window(target_date)
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - OpenAI を用いたマクロセンチメント評価（gpt-4o-mini、JSON Mode）。API エラー時はフォールバック macro_sentiment=0.0。
    - DuckDB の prices_daily / raw_news / market_regime を利用し、冪等的に market_regime テーブルへ書き込み。
    - 主要公開 API: score_regime(conn, target_date, api_key=None)
  - 共通設計方針:
    - LLM 呼び出しはテストで差し替え可能（モジュール内 private 関数を patch 可能）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない実装。

- データプラットフォーム機能（DuckDB 前提）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants クライアント経由で差分取得・冪等保存）。
    - 営業日判定ユーティリティを実装:
      - is_trading_day(conn, d)
      - is_sq_day(conn, d)
      - next_trading_day(conn, d)
      - prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
    - market_calendar テーブルが未取得の場合は曜日ベース（土日非営業）でフォールバック。
    - 最大探索日数やバックフィル、健全性チェック等の保護ロジックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装して ETL 結果（取得数・保存数・品質問題・エラー等）を集約し公開（etl.py から ETLResult を再エクスポート）。
    - 差分更新、バックフィル、安全な保存（idempotent）、品質チェックの仕組みを想定した設計。
    - 内部ユーティリティ: テーブル存在チェック、テーブル最大日付取得など。

- リサーチ（ファクター計算・特徴量探索）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ / 流動性（20 日 ATR、atr_pct、avg_turnover、volume_ratio）
    - バリュー（PER、ROE。raw_financials の最新レコードを使用）
    - すべて DuckDB の prices_daily / raw_financials のみ参照し外部 API へアクセスしない設計。
    - 主要公開関数:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)
    - IC（Spearman ランク相関）計算: calc_ic(factor_records, forward_records, factor_col, return_col)
    - ランクユーティリティ: rank(values)
    - 統計サマリー: factor_summary(records, columns)
    - 外部ライブラリに依存しない、標準ライブラリベースの実装。
  - 研究用ユーティリティをパッケージで公開（src/kabusys/research/__init__.py）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Design highlights
- LLM 呼び出しは OpenAI SDK を使用（OpenAI(api_key=...) → client.chat.completions.create）。JSON Mode を期待するレスポンス処理が組み込まれている。
- LLM 呼び出し・API エラーに対する堅牢性（リトライ、バックオフ、非致命的フォールバック）を重視。
- DB 書き込みは冪等性と部分失敗時の保護（コード絞り込み DELETE → INSERT、トランザクション BEGIN/COMMIT/ROLLBACK）を考慮。
- ルックアヘッドバイアスの防止を明確に設計方針として採用（日時参照は外部入力として受ける）。
- DuckDB を想定した SQL（WINDOW 関数等）を多用しており、テーブルスキーマ（prices_daily, raw_news, ai_scores, news_symbols, raw_financials, market_calendar, market_regime 等）との整合性が前提。

### Required environment variables（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- OPENAI_API_KEY（AI 機能利用時に必須）
- KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH 等は任意（デフォルトあり）

### Known limitations / TODO（コードから推測）
- strategy / execution / monitoring の実体はこのスナップショットに含まれていない（__all__ にて公開される想定）。
- 一部モジュールの __init__ が未実装（例: src/kabusys/data/__init__.py は空）ため、追加のエクスポート整理が今後必要。
- モデルやプロンプトのチューニング、レスポンスバリデーションのさらなる強化（LLM の多様な出力への耐性向上）は今後の改善点。
- 単体テストや統合テストに関する記載はコード中には見当たらないため、テストカバレッジの整備が推奨される。

---

（以上）
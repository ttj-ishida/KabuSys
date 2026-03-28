Keep a Changelog に準拠した形式で、コードベースから推測した変更履歴（日本語）を作成しました。

CHANGELOG.md
=============
すべての重要なリリース変更を時系列で記載します。
フォーマットは Keep a Changelog に準拠しています。

フォーマット説明:  
- 可能な限り高レベルの設計方針とパブリック API を中心に記載しています。  
- 日付は本コードのスナップショット日（生成日）を使用しています。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境/設定管理
  - kabusys.config.Settings クラスを導入し、アプリケーション設定を環境変数から取得する公開インターフェースを提供。
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準に探索）。
  - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォート（エスケープ考慮）、行末コメント処理等に対応。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。既存の OS 環境変数は保護（protected）される挙動。
  - Settings が提供する主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev ブールヘルパー
- AI（自然言語処理）機能
  - kabusys.ai.news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI の gpt-4o-mini を用いて銘柄ごとのセンチメント（ai_score）を算出。
    - チャンク処理（最大 20 銘柄/リクエスト）、1 銘柄あたり最大記事数・文字数制限（肥大化対策）を実装。
    - リトライ・バックオフ: 429（レート制限）、ネットワーク断、タイムアウト、5xx を対象に指数バックオフで再試行。
    - レスポンスの堅牢なバリデーション（JSON パース回復処理、results 配列/型チェック、未知コードの無視、スコアのクリップ）。
    - 結果は ai_scores テーブルへ冪等的に保存（既存行を DELETE → INSERT で置換、部分失敗による既存データ保護）。
    - タイムウィンドウ定義: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
  - kabusys.ai.regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp ベースのマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロ記事は指定のキーワードリストでフィルタし、最大 20 件まで LLM 評価に渡す。
    - OpenAI 呼び出しは専用のクライアントラッパーを用いる（テスト用に差し替え可能）。API 失敗時は macro_sentiment=0.0 とするフォールバックを備える。
    - 判定結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
- データプラットフォーム関連
  - kabusys.data.calendar_management
    - 市場カレンダー管理（market_calendar）機能と営業日判定ロジックを実装。
    - 提供関数: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - カレンダーが未取得の場合は曜日ベース（平日＝営業日）でフォールバックする一貫性のある設計。
    - calendar_update_job: J-Quants API からの差分取得→market_calendar への冪等更新（バックフィル・健全性チェックを含む）。
    - 最大探索範囲(_MAX_SEARCH_DAYS) やバックフィル期間(_BACKFILL_DAYS) 等を設定可能。
  - kabusys.data.pipeline / ETLResult
    - ETL パイプラインの結果を表す ETLResult dataclass を公開（取得数・保存数・品質問題・エラー一覧などを含む）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
    - ETL の設計方針として差分更新、後出し修正吸収用バックフィル、品質チェックの集約を採用。
  - kabusys.data.etl は pipeline.ETLResult を再エクスポート。
- リサーチ / ファクター分析
  - kabusys.research パッケージに以下を実装・公開:
    - factor_research: calc_momentum, calc_volatility, calc_value
      - モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金/出来高変化率）、バリュー（PER, ROE）を DuckDB 上で SQL / Python により算出。
      - データ不足時は None を返す等、安全に動作する設計。
    - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
      - 将来リターン計算（horizons の検証・複数ホライズンの一括取得）、Spearman（ランク）による IC 計算、統計サマリー、ランク付けユーティリティを提供。
    - zscore_normalize は kabusys.data.stats から再エクスポート（data.stats モジュール想定）。
- 設計原則（全体）
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を内部判定に直接参照しない（関数引数で基準日を指定）。
  - DuckDB を中心としたローカル分析基盤を想定（prices_daily, raw_news, raw_financials, ai_scores, market_regime, market_calendar 等のテーブルを前提）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT や ON CONFLICT 相当の保存パターン）。
  - OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を利用し、レスポンスの堅牢な復元ロジックを実装。
  - エラー/例外時のフォールバックを各所に導入し（API 失敗時 0.0 やスキップ）、全体の堅牢性を確保。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で供給。未設定時は ValueError で明示的に失敗するため、誤った運用の早期検出に寄与。

Notes / Limitations / Migration
- OpenAI 利用
  - score_news / score_regime ともに OpenAI API キーが必須。テストでは内部 _call_openai_api を unittest.mock.patch で差し替えが可能な設計。
  - レスポンスが予期せぬ形式だった場合、該当チャンクはスキップされる（例外は上位へ伝播しない）。
- DB 前提
  - 各処理は DuckDB 内の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を前提とする。初期セットアップでスキーマとデータを用意する必要がある。
- 環境設定
  - .env 自動ロードはプロジェクトルートを基準に行うため、配布後も CWD に依存せず動作する設計。ただしルート検出に失敗すると自動ロードはスキップされる。
- 既知の未実装（将来的な拡張示唆）
  - Strategy/Execution/Monitoring の具体的な実装は本スナップショットに含まれていない（パッケージ __all__ で名前が公開されているが実装が省略されている可能性あり）。

貢献・報告
- バグ報告、機能要望、改善提案はリポジトリの Issue を使用して報告してください。特に OpenAI 呼び出しの安定性や DuckDB バインドの互換性（executemany の空リスト制約など）に関するフィードバックを歓迎します。

-- end of CHANGELOG.md --
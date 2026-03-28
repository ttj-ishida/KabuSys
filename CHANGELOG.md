# Changelog

すべての重要な変更をここに記録します。形式は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠します。

現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-28

初回公開リリース（ベース実装）。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys、__version__ = 0.1.0）。
  - モジュール公開: data, research, ai, execution, strategy, monitoring（__all__ に含める構成を準備）。
- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルートを .git / pyproject.toml から自動検出。
  - .env パーサ実装（クォート対応、export KEY= 値形式、インラインコメントの扱い、無効行スキップ）。
  - 自動ロードの制御: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境 (development/paper_trading/live) / ログレベル等の取得 API を公開。
  - 必須変数取得時に未設定であれば ValueError を投げる `_require` を実装。
  - デフォルト DB パス: DUCKDB_PATH=`data/kabusys.duckdb`, SQLITE_PATH=`data/monitoring.db`。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）に投げ、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書込む処理を実装。
    - バッチ処理（最大 20 銘柄/chunk）、記事トリミング、チャンク毎のリトライ（429/ネットワーク/5xx に対する指数バックオフ）。
    - レスポンス検証ロジック（JSON 抽出、results 配列検査、コード・スコアの正当性検証、±1.0 でクリップ）。
    - calc_news_window(target_date) ユーティリティ（JST 時刻ウィンドウを UTC naive datetime に変換）。
    - score_news(conn, target_date, api_key=None) を公開（書き込み件数を返す）。
    - ユニットテスト用の差し替えフック: _call_openai_api を patch 可能。
  - レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルに日次判定を書き込む機能を実装。
    - OpenAI 呼び出しのリトライ / フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - score_regime(conn, target_date, api_key=None) を公開（成功で 1 を返す）。
    - LLM 呼び出しは news_nlp と独立実装（モジュール結合を避ける設計）。
- データ処理（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装（取得数・保存数・品質問題リスト・エラー一覧・ユーティリティ to_dict 等）。
    - 差分取得・バックフィル・品質チェックを想定したユーティリティ（テーブル存在確認・最大日付取得など）。
  - calendar_management
    - JPX カレンダー管理（market_calendar）を扱うユーティリティを追加。
    - 営業日判定ロジック: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - calendar_update_job(conn, lookahead_days) により J-Quants から差分取得して保存する夜間バッチを想定。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日と扱う）。
  - etl re-export
    - kabusys.data.ETLResult を kabusys.data.etl 経由で再エクスポート。
- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、バリュー（PER/ROE）等のファクター計算関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB を用いた SQL ベースの計算、結果を dict リストで返す設計。
  - feature_exploration
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman ランク相関）。
    - ランク変換ユーティリティ: rank(values)（同順位は平均ランク）。
    - 統計サマリ: factor_summary(records, columns)（count/mean/std/min/max/median）。
  - research パッケージの __all__ で主要関数を公開。
- テスト/運用を意識した設計上の追加
  - ルックアヘッドバイアス防止のため、どの関数も datetime.today()/date.today() を直接参照せず target_date を受け取る設計。
  - DuckDB に対する書込みは冪等（DELETE→INSERT 等）／トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - OpenAI 呼び出しの失敗時はフェイルセーフなデフォールト値を使用して処理継続する実装。

### 変更 (Changed)
- （初版）パッケージ補完のため複数モジュールを実装。既存の外部仕様（DB スキーマや jquants_client の契約）を前提に設計。

### 修正 (Fixed)
- .env パーサの堅牢化:
  - クォート内のエスケープ処理と対応する閉じクォート探索を実装。
  - コメント判定の取り扱いを改善（クォート外でのみ # をコメントと扱う等）。
- OpenAI レスポンス処理の堅牢化:
  - JSON mode でも前後に余計なテキストが混ざるケースに備え最外の {} を抽出してパース。
  - レスポンスのバリデーション失敗、パースエラー、API エラーに対するログ出力とフォールバックを追加。
- DuckDB executemany の空リスト制約に対するガード（空リスト時は実行しない）。

### 互換性に関する注意 (Compatibility)
- 初回リリースのため破壊的変更はありませんが、内部で想定する DB スキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials, news_symbols, market_regime 等）に依存します。既存データベースを使用する場合はスキーマ互換性に注意してください。
- OpenAI SDK（openai.OpenAI）を利用するため、実行環境に適切な SDK バージョンとネットワークアクセスが必要です。

### セキュリティ (Security)
- OpenAI API キー（OPENAI_API_KEY）や J-Quants / kabu API のトークンは環境変数経由で管理してください。Settings は必須項目未設定時に例外を投げます。
- .env 自動ロードはデフォルトで有効ですが、テスト・特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

開発者向けメモ（利用方法の抜粋）
- AI スコアリングを実行する:
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)
  - api_key を None にすると環境変数 OPENAI_API_KEY を参照します。存在しない場合は ValueError。
- ETL 実行結果のログや監査には ETLResult.to_dict() を利用できます。
- テスト時には kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch して外部 API 呼び出しをモックしてください。

今後の予定（例）
- execution / strategy / monitoring 各モジュールの実装拡充（自動注文ロジック・監視アラート等）。
- jquants_client の抽象化・バージョン管理対応。
- 追加の品質チェックルールとデータ補正ロジック。

（終）
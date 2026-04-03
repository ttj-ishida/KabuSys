Changelog
=========

すべての重要な変更はこのファイルに記録します。形式は「Keep a Changelog」に準拠します。

0.1.0 - 2026-04-03
------------------

Added
- 初回リリース: KabuSys — 日本株自動売買／データ分析用ライブラリ（バージョン 0.1.0）。
- パッケージ公開情報
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - パブリックサブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ に準拠）

- 環境設定管理 (kabusys.config)
  - .env/.env.local 自動読み込み（優先順: OS 環境変数 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用）。
  - 高度な .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート対応（バックスラッシュエスケープを処理）
    - クォート無し行でのインラインコメント処理（直前が空白/タブの場合のみ）
    - ファイル読み込み失敗時に警告を出力
  - 環境変数上書き挙動:
    - .env は既存変数を上書きしない
    - .env.local は上書き（ただし OS 環境変数は保護）
  - Settings クラス（settings でインスタンス公開）:
    - J-Quants, kabuステーション, LINE, データベースパス (duckdb/sqlite), 監視設定（PID/KILL flag/閾値）等のプロパティ提供
    - KABUSYS_ENV の検証（development, paper_trading, live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - 必須環境変数未設定時は ValueError を発生（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須として取得メソッドあり）

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - target_date に対するニュース収集ウィンドウ計算（JST ベース、DB 比較は UTC naive datetime を使用）
      - ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC では前日 06:00 ～ 23:30）
    - raw_news / news_symbols を集約して銘柄ごとに記事を結合（最大 _MAX_ARTICLES_PER_STOCK 件、_MAX_CHARS_PER_STOCK 文字でトリム）
    - OpenAI（gpt-4o-mini）へのバッチ送信（1 API コールあたり最大 20 銘柄）
    - JSON Mode を期待し、応答は厳密な JSON: {"results": [{"code":"XXXX","score":0.0}, ...]} を想定
    - リトライ戦略:
      - レート制限(429)、接続断、タイムアウト、5xx を指数バックオフでリトライ（最大試行回数設定）
      - 失敗時は該当チャンクをスキップし、フェイルセーフで処理継続
    - レスポンスのバリデーションとスコアの ±1.0 クリップ
    - 書き込み: ai_scores テーブルへ冪等的に置換（対象コードだけ DELETE → INSERT、部分失敗時に既存スコア保護）
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - 日次で市場レジーム（'bull' / 'neutral' / 'bear'）を判定し market_regime テーブルへ冪等書き込み
    - 指標:
      - ETF 1321 の 200 日移動平均乖離（ma200_ratio）に重み 70%
      - マクロ経済ニュースの LLM センチメントに重み 30%
      - 合成式: regime_score = clip(0.7 * (ma200_ratio - 1) * 10 + 0.3 * macro_sentiment, -1, 1)
      - 閾値: regime_score >= 0.2 → "bull", <= -0.2 → "bear"、それ以外は "neutral"
    - マクロ記事抽出: raw_news のタイトルをマクロキーワード一覧でフィルタ（最大 20 件）
    - OpenAI 呼び出し（gpt-4o-mini）で JSON {"macro_sentiment": <score>} を期待
    - API 失敗時のフェイルセーフ: macro_sentiment = 0.0（警告ログ出力）
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作、失敗時は ROLLBACK を試行して例外を再送出
    - 公開関数: score_regime(conn, target_date, api_key=None) → 1（成功）

- リサーチモジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: mom_1m, mom_3m, mom_6m（営業日ベース）、ma200_dev（200日 MA 乖離）
    - Volatility/Liquidity: atr_20（20日 ATR）、atr_pct、avg_turnover（20日平均売買代金）、volume_ratio
    - Value: per（price / EPS）、roe（raw_financials から最新レコード）
    - DuckDB 内部クエリ中心で実装（prices_daily / raw_financials を参照）
    - 欠損/データ不足時は None を返却
    - 公開 API: calc_momentum, calc_volatility, calc_value（それぞれ conn, target_date を受ける）
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=[1,5,21] デフォルト)
      - LEAD を使った単一クエリで複数ホライズンを同時計算、horizons の検証あり
    - IC（Information Coefficient）: calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンのランク相関を自前実装（同順位は平均ランク）
      - 有効レコードが 3 件未満の場合は None
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）
    - ユーティリティ: rank(values)（同順位平均ランク処理）
    - 外部依存を避け、標準ライブラリのみで実装

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
    - market_calendar テーブルがある場合は DB 値優先、無ければ曜日（平日）ベースのフォールバック
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を実装して無限ループ防止
    - calendar_update_job(conn, lookahead_days=90):
      - J-Quants API から差分取得（jquants_client 経由）、バックフィル (_BACKFILL_DAYS) と健全性チェックを実施
      - 取得 → 保存（jq.save_market_calendar）を行い、取得件数・保存件数を返す
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスで ETL 実行結果を集約（取得数、保存数、品質問題、エラーの概略）
    - to_dict() で品質問題を serializable な dict に変換
    - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した設計
    - jquants_client / quality モジュールを利用して idempotent な保存と品質検査を行う
    - kabusys.data.etl は ETLResult を再エクスポート

Design / Safety / Implementation Notes
- ルックアヘッドバイアス防止:
  - AI モジュールやリサーチ関数は datetime.today()/date.today() を内部で参照しない（必ず target_date 引数を利用）
  - DB クエリでは date < target_date の排他条件や LEAD/LAG を適切に使用
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants 等）の失敗時は処理を完全停止せず、可能な限り部分的に継続（例: macro_sentiment=0.0、API チャンク失敗はスキップ）
  - DB 書き込みは冪等化を意識（DELETE → INSERT の形や executemany の空パラメータ回避）
- テスト性:
  - OpenAI 呼び出し箇所は内部関数を差し替え可能にしてユニットテストを容易化
- 依存:
  - DuckDB を前提とする SQL 実行（DuckDBPyConnection 型注釈）
  - OpenAI Python SDK を利用（OpenAI クライアント）
- ロギング:
  - 各モジュールで詳細ログ（INFO/DEBUG/WARNING）を出力し、失敗時は警告/例外ログを残す

BREAKING CHANGES
- 初回リリースのため該当なし。

Known issues / Limitations
- OpenAI の応答フォーマットに依存（JSON mode を前提）。LLM の出力が期待形式から外れた場合はスコア取得に失敗する可能性があり、その場合は該当チャンク/記事がスキップされる。
- DuckDB の executemany に空リストを渡すとエラーになる（回避策をコード内で適用済み）。
- 一部設計は J-Quants / kabu ステーションや LINE API の設定が前提（環境変数設定必須箇所あり）。詳細は settings のプロパティと .env.example を参照のこと。

その他
- 今後の予定（例）:
  - AI モデルやプロンプトのチューニング、エラー回復性の改善
  - 追加のファクター/スクリーニング機能、ETL の並列化オプション
  - モニタリング/アラート機能の拡張

--- 

（注）本 CHANGELOG は与えられたコードベースを解析して推測に基づき作成しています。実際のリリースノートとして採用する際は、実装・ドキュメントの差分や運用上の注意事項を含めて適宜追記してください。
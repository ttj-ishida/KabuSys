Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-29
-----------------

Added
- パッケージ初期リリース (kabusys v0.1.0)。
  - src/kabusys/__init__.py にて __version__="0.1.0" を公開し、サブパッケージを __all__ でエクスポート。
- 環境設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動ロード（プロジェクトルート(.git または pyproject.toml) に基づく）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの取り扱い等）。
  - override / protected をサポートして OS 環境変数を保護しつつ .env.local による上書きを可能に。
  - Settings クラスを提供し、以下をプロパティとして取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）とログレベル検証
    - is_live / is_paper / is_dev のユーティリティ
  - 未設定の必須環境変数取得時には明確な ValueError を送出。
- AI 関連（src/kabusys/ai/）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメント (ai_scores テーブル) を書き込む機能。
    - 設計上の特徴: タイムウィンドウ計算（JST基準→UTC比較）、1チャンク最大銘柄数、記事数および文字数上限（トークン肥大化対策）、バリデーション、スコア ±1.0 でクリップ、部分成功時の安全な置換（DELETE→INSERT の戦略）、API の 429/ネットワーク/5xx に対する指数バックオフリトライ。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替えられる設計。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書込み銘柄数を返す。
  - レジーム検出（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（'bull'/'neutral'/'bear'）を判定、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はニュース NLP のウィンドウ計算関数 calc_news_window を利用。
    - OpenAI 呼び出しは独立実装、API 失敗時は macro_sentiment=0.0 のフォールバック、リトライ・バックオフ実装あり。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 1 を返す（成功時）。
- データ処理・ETL（src/kabusys/data/）
  - ETL パイプライン型 (ETLResult) を src/kabusys/data/pipeline.py に実装し、src/kabusys/data/etl.py で再エクスポート。
    - ETLResult は品質チェック結果、取得/保存件数、エラーリスト等を含むデータクラス。to_dict() により品質問題はシリアライズ可能。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを提供。
    - calendar_update_job により J-Quants API から差分取得して冪等保存（jq.fetch_market_calendar / jq.save_market_calendar を呼ぶ想定）。
    - DB 登録がない場合は曜日ベースでフォールバック（週末を非営業日扱い）。DB とフォールバックの一貫性を維持する実装。
    - 最大探索幅やバックフィル、健全性チェックなどの安全機構を実装。
- リサーチ（src/kabusys/research/）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR、相対 ATR）、Liquidity（20日平均売買代金・出来高比）、Value（PER、ROE）を DuckDB 上で計算する関数群を実装。
    - 関数: calc_momentum(conn, target_date), calc_volatility(conn, target_date), calc_value(conn, target_date) — いずれも (date, code) キーの dict リストを返す。
    - データ不足時の扱い（None）やログ出力を明示。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンのランク相関を算出、データ不足で None を返す。
    - ランク化ユーティリティ: rank(values)（同順位は平均ランク）、factor_summary(records, columns)（count/mean/std/min/max/median を算出）。
  - research パッケージの __init__ で便利な関数を再エクスポート（zscore_normalize のインポート経路含む）。
- DuckDB を想定した SQL + Python 実装により、外部発注 API 等には一切アクセスしない安全な設計を採用。
- ロギングとエラーハンドリングを各モジュールで整備（WARN/INFO/DEBUG レベルのメッセージ、トランザクションでの ROLLBACK 処理、API エラーのフェイルセーフ）。

Changed
- 新規リリースのため該当なし。

Fixed
- リリース時点での初期実装のため該当なし。

Security
- リリース時点で特別なセキュリティ修正なし。
- 注意事項: OpenAI API キーや各種トークンは環境変数で管理する想定。Settings._require は未設定時に例外を投げるので、運用時は secrets 管理を推奨。

Notes / 開発者向けメモ
- 多くの処理は DuckDB 接続を引数に取る設計（副作用のあるグローバル DB 接続を持たない）。単体テストしやすい。
- AI 関連関数は api_key を引数で注入可能（テストや CI での差し替えが容易）。
- LLM 呼び出し部分はテストでモック可能なように内部関数を分離してある（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- ルックアヘッドバイアス防止のため、内部ロジックは date.today()/datetime.today() を直接参照しない設計（target_date を明示的に渡す）。
- DB 書き込みは冪等性を意識して DELETE→INSERT や ON CONFLICT 相当の戦略を採用。トランザクションを利用し、失敗時には ROLLBACK を試行。

Breaking Changes
- 初期リリースのため該当なし。

今後の予定（検討中）
- PBR・配当利回り等バリューファクターの追加。
- ai_scores / market_regime / prices_daily などテーブルスキーマのドキュメント化。
- 追加の品質チェックルールやモニタリング機能の拡充。
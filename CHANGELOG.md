Keep a Changelog
すべての重要な変更はこのファイルに記録します。

フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。
http://keepachangelog.com/ja

[Unreleased]
- （現時点、未リリースの変更はありません）

[0.1.0] - 2026-04-03
Added
- 基本パッケージ初期実装を追加。
  - パッケージ名: kabusys、バージョン 0.1.0。
  - 主要サブパッケージ: data, research, ai, monitoring, execution, strategy（__all__ による公開）。
- 環境設定管理モジュールを追加 (kabusys.config)。
  - .env / .env.local の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサの堅牢化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの扱い（クォート有無に応じた処理）。
    - 読み込み失敗時は警告を出力。
  - 既存 OS 環境変数を保護する protected キーセット対応。
  - Settings クラスを提供し、必須値取得（_require）・既定値・型変換・バリデーションを行う。
    - 例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI 連携用キー, DB パス（DUCKDB_PATH, SQLITE_PATH）等。
    - 環境 (development/paper_trading/live) と log_level のバリデーション。
- AI モジュールを追加 (kabusys.ai)。
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へ JSON mode でバッチ送信してセンチメントスコアを生成。
    - 時間ウィンドウ計算（JST基準）を提供する calc_news_window。
    - API リトライ（429/ネットワーク/タイムアウト/5xx）：指数バックオフ、上限回数指定。
    - レスポンス検証とスコアクリッピング（±1.0）。
    - 書き込みは部分失敗に強い方式（対象コードのみ DELETE → INSERT）。
    - public API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照、OpenAI を用いたマクロセンチメント評価（gpt-4o-mini）。
    - ルックアヘッドバイアス対策: 対象日のデータは排他条件（date < target_date 等）で取得。
    - API 障害時はフェイルセーフで macro_sentiment=0.0 にフォールバック。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
    - public API: score_regime(conn, target_date, api_key=None) — 成功時は 1 を返す。
- データモジュールを追加 (kabusys.data)。
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar を参照して is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB データ優先、未登録日は曜日ベースのフォールバック（土日を非営業日扱い）。
    - 最大探索幅や健全性チェック、バックフィルポリシーを実装（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。
    - 夜間バッチ更新ジョブ calendar_update_job(conn, lookahead_days) を追加（J-Quants から差分取得 → 保存）。
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分取得・保存・品質チェックの枠組みを想定したユーティリティ（品質チェック結果を収集し上位で判断可能）。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを実装。
- 研究・ファクター分析モジュールを追加 (kabusys.research)。
  - ファクター計算 (research.factor_research)
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）。
    - ボラティリティ/流動性: atr_20、atr_pct、avg_turnover、volume_ratio。
    - バリュー: PER、ROE（raw_financials から最終レコードを取得）。
    - DuckDB 上で SQL を活用した計算、結果は (date, code) を含む dict のリストで返す。
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)（デフォルト horizons=[1,5,21]）。
    - Information Coefficient 計算 calc_ic（Spearman の rank 相関を実装）。
    - ランク付けユーティリティ rank、および factor_summary（基本統計量）。
- パッケージ設計上の方針（ドキュメントコメントとして明記）。
  - ルックアヘッドバイアス防止（datetime.today() や date.today() を内部ロジックで直接参照しない設計）。
  - API 呼び出しはリトライ・フェイルセーフ化してロバストネスを確保。
  - DB 書き込みは冪等性を重視（削除→挿入など）。
  - DuckDB を主要なローカル分析 DB として想定（SQL + Python の組合せ）。
  - 外部サービスキー（OpenAI 等）は引数注入可能でテストを容易にする。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。ただし注意事項あり:
  - OpenAI API キーや各種トークンは環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）で設定すること。
  - .env ファイルをリポジトリに含めない、共有しない運用を推奨。

注意事項 / マイグレーション
- 初期公開版です。使用するには以下の環境変数等の設定が必要（少なくとも一部は必須）。
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings により必須取得）
  - OPENAI_API_KEY（AI モジュールを利用する場合）
- デフォルトのデータベースやファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
  - PID / KILL フラグのデフォルトパスも Settings により定義
- OpenAI 呼び出しのテスト時は各モジュールの内部 _call_openai_api をパッチして疑似応答を返す設計になっています（unittest.mock.patch を想定）。

連絡先 / 貢献
- バグ報告や提案は issue を通じて受け付けてください。今後、安定化・テスト追加・ドキュメント整備を進める予定です。
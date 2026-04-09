CHANGELOG
=========
すべての注記は Keep a Changelog の慣例に準拠しています。  
リリース日はリポジトリ内の __version__ に基づく初期公開（本日）として記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ構成を公開（kabusys, kabusys.ai, kabusys.data, kabusys.research など）。
- 環境設定・管理（kabusys.config）
  - .env / .env.local の自動読み込み（優先度: OS 環境変数 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ考慮、インラインコメント扱いのルール。
  - Settings クラスを提供（settings インスタンスで利用可能）:
    - J-Quants / kabuステーション / LINE / DB パス等の設定プロパティを収録。
    - デフォルト値（例: KABUSYS_API_BASE_URL、データベースパス等）と入力検証を実装。
    - PAPER_FILL_MODE（instant/partial/never/reject）の検証。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証。
    - 各種監視設定（PID ファイル、kill フラグ、閾値など）をプロパティ化。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄単位のセンチメント（ai_score）を算出。
  - タイムウィンドウ計算（JST 前日 15:00 〜 当日 08:30 を UTC に変換）と記事トリム（記事数・文字数制限）を実装。
  - バッチ処理（最大 20 銘柄/コール）、再試行（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップを実装。
  - DuckDB の executemany 空リスト制約を考慮した書き込み（DELETE → INSERT の冪等更新）。
  - テストしやすさのため _call_openai_api をパッチ可能に実装。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ書き込み。
  - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（JSON mode）、リトライ/フェイルセーフ戦略（API 失敗時は macro_sentiment=0.0）を実装。
  - ルックアヘッドバイアス対策（target_date 未満のデータのみ使用、datetime.today() 非参照）。
- Research ユーティリティ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_value: raw_financials から PER/ROE を計算（EPS が 0/欠損のときは None）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - 計算は DuckDB 上の SQL ウィンドウ関数を主体に実装（外部 API へアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン後の将来リターン（デフォルト 1/5/21 営業日）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank / factor_summary: ランク化・統計サマリーを標準ライブラリのみで実装。
- Data モジュール（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar）用ユーティリティ。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar が未取得の場合は曜日ベース（週末休）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して冪等保存（バックフィル・健全性チェックを実装）。
  - pipeline / etl:
    - ETLResult データクラス（ETL の集計結果・品質問題・エラーを格納）。
    - ETL 処理設計方針に基づく差分更新・品質チェック統合（jquants_client / quality との連携を想定）。
  - etl モジュールは ETLResult を再エクスポート。
- DuckDB を主要なローカル DB として利用する前提で実装（duckdb.Python API を使用）。

Changed
- 初期リリースのため変更履歴なし。

Fixed
- 初期リリースのため修正履歴なし。

Security
- AI 機能（score_news / score_regime）を利用する場合は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を返す旨を明記。

Notes / Migration / 期待される環境
- 必要な DB テーブル（例: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）が存在することが前提です。ETL モジュールは jquants_client と quality モジュールに依存します（実装は別途）。
- Settings のデフォルト DB パス:
  - duckdb: data/kabusys.duckdb
  - sqlite (monitoring): data/monitoring.db
  - paper_trading sqlite: data/paper_trading.db
- テスト容易性:
  - OpenAI 呼び出し部分は内部関数をパッチしてモック可能。
  - 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

今後の TODO（未実装・検討項目）
- PBR・配当利回りなどのバリュー指標の追加（calc_value の拡張）。
- monitoring / execution 等の実行系モジュールの追加（今回のリリースでは存在しない / 別途実装予定）。
- より詳細な品質チェックルールの実装と ETL ワークフローの稼働監視機能。

（以上）
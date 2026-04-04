CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-04
-----------------

Added
- 初回公開リリース。KabuSys：日本株自動売買／データ基盤向けユーティリティ群を提供。
- パッケージ構成（主なモジュール）
  - kabusys.config
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応する堅牢な実装。
    - 必須設定取得用 _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI 関連、DB パス、監視設定等）。
    - 環境（development / paper_trading / live）やログレベルの値検証を実装。
  - kabusys.data
    - ETL 用 pipeline モジュールと ETLResult データクラスを公開。
    - calendar_management: JPX カレンダー管理（market_calendar テーブル操作、営業時間判定、next/prev_trading_day, get_trading_days, is_sq_day、calendar_update_job）を実装。DB にデータがない場合は曜日ベースのフォールバックを行う設計。
    - ETL パイプライン設計（差分更新、バックフィル、品質チェック連携）に対応する基盤ロジックを実装。
    - DuckDB を前提とした互換性重視の実装（executemany の空リスト回避などの注意あり）。
  - kabusys.ai
    - news_nlp モジュール：raw_news / news_symbols を用いたニュースの銘柄別センチメントスコアリング機能を実装。
      - gpt-4o-mini（OpenAI JSON Mode）を用いたバッチスコアリング（最大 20 銘柄 / チャンク）。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window。
      - レスポンスの厳密なバリデーション、JSON 抽出ロジック、スコア ±1 でクリップ。
      - レート制限・ネットワーク断・タイムアウト・5xx に対するエクスポネンシャルバックオフによるリトライ実装。失敗時は該当チャンクをスキップ（フェイルセーフ）。
      - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。api_key は引数または環境変数 OPENAI_API_KEY。
    - regime_detector モジュール：市場レジーム判定（bull / neutral / bear）。
      - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジームスコアを算出。
      - OpenAI 呼び出しは専用実装を使用、失敗時のフォールバック（macro_sentiment=0.0）あり。
      - 冪等性を担保した market_regime テーブルへの書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK の取り扱い）。
      - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時は 1 を返す。api_key は引数または環境変数 OPENAI_API_KEY。
  - kabusys.research
    - factor_research モジュール：StrategyModel に基づく定量ファクター群（Momentum, Value, Volatility, Liquidity 等）の計算を実装。
      - calc_momentum, calc_volatility, calc_value を提供。いずれも DuckDB 接続と target_date を受け取る。
      - 計算は prices_daily / raw_financials テーブルのみ参照（外部 API に依存しない）。
      - 欠損やデータ不足に配慮した None の扱い。
    - feature_exploration モジュール：将来リターン計算、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク変換ユーティリティを実装。
      - calc_forward_returns(conn, target_date, horizons=None)
      - calc_ic(factor_records, forward_records, factor_col, return_col)
      - factor_summary(records, columns), rank(values)
    - research パッケージは zscore_normalize（data.stats から再エクスポート）などを公開。
- 共通設計上の方針・品質面の実装
  - 全モジュールでルックアヘッドバイアスを防ぐ設計（datetime.today()/date.today() を直接参照しない、DB クエリに date < target_date 等の排他条件を適用）。
  - OpenAI 呼び出し、外部 API 呼び出しに対する堅牢なエラーハンドリング（再試行・バックオフ・ログ）とフェイルセーフフォールバック。
  - DB 書き込みは冪等性を重視（既存レコード削除→挿入等）、部分失敗時に既存データを不必要に消さない工夫あり。
  - DuckDB を前提とした SQL 実装や互換性考慮（ROW_NUMBER, LEAD/LAG, window 関数利用）。  

Security
- OpenAI API キーや各種シークレット（J-Quants トークン、kabu API パスワード等）は環境変数で管理することを想定。Settings からの取得時に未設定であれば ValueError を送出して注意喚起。

Notes / Usage reminders
- OpenAI API を利用する機能（news_nlp, regime_detector）は api_key 引数または環境変数 OPENAI_API_KEY を必要とします。未設定時は例外が発生します。
- DuckDB 接続を受け取る関数が多く、事前にスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を準備する必要があります。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。パッケージ配布後も CWD に依存せず機能するよう設計されていますが、必要に応じて自動ロードを無効化できます。

今後の予定（想定）
- API クライアント（jquants_client 等）の公開/改善、監視・実行・発注モジュールの実装・統合。
- テスト・ドキュメントの充実、型注釈や型チェックの強化、パフォーマンス最適化。
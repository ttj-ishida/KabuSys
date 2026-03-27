Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。

[未リリース]: https://example.com/compare/v0.1.0...HEAD

0.1.0 - 2026-03-27
-----------------

Added
- 初回リリース。パッケージ名: kabusys, バージョン: 0.1.0。
- パッケージ公開インターフェースを定義（kabusys.__init__）。__all__ に data / strategy / execution / monitoring を公開。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数を読み込む自動ローダーを実装。プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env パーサーはコメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 環境変数の必須チェック用 _require と Settings クラスを提供。J-Quants / kabu ステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを定義。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols テーブルを元に、指定タイムウィンドウ（JST 前日 15:00 〜 当日 08:30）内のニュースを銘柄ごとに集約。
    - OpenAI (gpt-4o-mini) を JSON Mode で呼び出し、銘柄ごとのセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - バッチ処理（最大 20 銘柄 / コール）、1銘柄あたり記事数・文字数のトリム制御、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、code/score の型チェック、未知コードの無視、スコアクリップ）。
    - API 失敗時は例外を投げず該当チャンクをスキップ（フェイルセーフ）。テスト用に _call_openai_api をパッチ可能に実装。
    - 日時の参照で datetime.today()/date.today() を使用しない（ルックアヘッドバイアスの防止）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を計算（target_date 未満のデータのみ使用、データ不足時は中立値 1.0 を採用）。
    - raw_news からマクロ経済キーワードでフィルタしたタイトルを取得し、OpenAI に投げて macro_sentiment を算出。API エラー時は macro_sentiment=0.0 として継続。
    - レジームスコアを合成して market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。失敗時は ROLLBACK を行い例外を伝播。
    - OpenAI 呼出しは独立実装（news_nlp と内部関数を共有しない）でモジュール結合を低減。

- データ関連 (kabusys.data)
  - ETL パイプライン基盤 (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを実装し、ETL の取得数／保存数／品質問題／エラー一覧を保持。辞書変換メソッド to_dict を提供。
    - 差分更新、バックフィル、品質チェックの設計方針に基づくユーティリティを準備（詳細実装の拡張に対応）。
    - data.etl で ETLResult を再エクスポート。

  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ユーティリティを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 最大探索日数制限で無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル期間・健全性チェック・エラー処理を実装。
    - market_calendar が未取得の場合のフォールバック（曜日ベース）を用意。

  - DuckDB 互換性のための細かな配慮
    - executemany に空リストを渡さないガード（DuckDB 0.10 互換性）。
    - 日付型変換ユーティリティ（_to_date）やテーブル存在チェックを実装。

- リサーチ / ファクター分析 (kabusys.research)
  - factor_research
    - Momentum: calc_momentum を実装（1M/3M/6M リターン、200日 MA 乖離）。
    - Volatility: calc_volatility を実装（20日 ATR, ATR 比率, 20日平均売買代金, 出来高比率）。
    - Value: calc_value を実装（PER, ROE。raw_financials から最新財務データを取得）。
    - DuckDB ベースの SQL+Python 実装。データ不足時は None を返す設計。
  - feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得（LEAD を使用）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None。
    - rank: 平均ランク付け（同順位は平均ランク）を実装。丸めによる ties 検出対策あり。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。
  - 研究用ユーティリティを kabusys.research.__init__ でエクスポート。

Other
- ロギングとウォーニングを多用し、フェイルセーフな挙動とデバッグ容易性を提供。
- 各モジュールで DuckDB 接続を引数に取る設計。直接外部発注 API へアクセスしない方針（データ処理／研究コードの安全化）。
- テスト容易性のため、OpenAI 呼び出し部分をモック差し替え可能に実装。

Fixed
- （初版のため該当なし）

Changed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- （初版のため該当なし）

注記
- OpenAI 関連機能は API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出するため運用時の鍵管理が必要です。
- 一部設計は将来的に拡張を想定（例: PBR/配当利回り、strategy / execution / monitoring 層の実装）。
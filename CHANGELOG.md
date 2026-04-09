CHANGELOG
=========

このファイルは Keep a Changelog の形式に従って作成されています。
リリース日付はソースコードのスナップショット取得日 (2026-04-09) を使用しています。

Unreleased
----------

なし

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初期リリース "kabusys"（__version__ = 0.1.0）。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を含む（__all__）。
- 環境設定管理モジュール (kabusys.config)
  - .env/.env.local を自動読み込み（OS 環境変数を優先、.env.local は上書き）する仕組みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を探索）により CWD に依存しない読み込み。
  - .env パースの強化:
    - export KEY=... 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、
    - 無効行やコメント行を無視。
  - 読み込み時の上書き制御（override/protected）と読み込み失敗時の警告発行。
  - Settings クラスを提供し、J-Quants / kabuステーション API、LINE、データベースパス、Paper Trading 設定、
    監視閾値、環境 / ログレベル判定（validation 含む）などのプロパティを環境変数から取得。
  - 必須キー未設定時に ValueError を投げる _require ユーティリティ。
- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を集約し、銘柄毎にニュースを結合して OpenAI (gpt-4o-mini) にバッチ送信。
    - JSON Mode 応答のバリデーション、スコアの ±1.0 クリップ、部分成功時の差分書き込み（DELETE → INSERT）による冪等性。
    - バックオフ付きリトライ（429 / ネットワーク断 / タイムアウト / 5xx）、フェイルセーフで API 失敗時はスキップ継続。
    - calc_news_window による JST/UTC を考慮したニュース収集ウィンドウ計算。
    - テスト容易性のため OpenAI 呼び出し (_call_openai_api) を差し替え可能に設計。
  - regime_detector.score_regime:
    - ETF 1321（TOPIX 日経225） の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定。
    - OpenAI 呼び出しに対するリトライ / フォールバック（API 失敗時 macro_sentiment=0.0）。
    - DuckDB を用いた冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と例外時の ROLLBACK 保護。
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（不足時は None）。
    - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（EPS 不在時は None）。
    - DuckDB を用いた SQL 主導の実装、外部 API へのアクセスなし。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD）を一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
    - rank / factor_summary: ランク変換（同順位の平均ランク処理）および基本統計量集計ユーティリティ。
  - kabusys.data.stats の zscore_normalize を re-export。
- Data モジュール (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - カレンダーデータ未取得時の曜日ベースフォールバック（主に土日判定）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存、バックフィル・健全性チェックを実装。
  - ETL / pipeline:
    - ETLResult データクラスを提供（ETL 実行結果の構造化、品質チェック結果・エラー一覧などを保持）。
    - pipeline モジュールを通じて差分取得、idempotent 保存、品質チェック（quality モジュール連携）を想定した設計。
  - etl サブモジュールで ETLResult を再エクスポート。
- 全体設計上の注意点（ドキュメント化）
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照する実装を避け、target_date を明示的に受け取る関数設計。
  - DuckDB に対する実用上の互換性処理（executemany に空リストを渡さないガード等）。
  - ロギングと警告を多用して運用観点の情報を提供。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 実装上の設計判断（要点）
- OpenAI 呼び出しは JSON Mode（厳密な JSON レスポンス指定）を期待するが、万一のパースエラーや余計な前後テキスト混入に対して復元ロジックを実装。
- API 呼び出しの失敗は基本的にフェイルセーフ（デフォルト値へフォールバック or 該当処理をスキップ）とし、処理全体の停止を避ける設計。
- DB 書き込みは冪等性を重視（既存レコードの DELETE → INSERT、トランザクション保護、ROLLBACK の試行）。
- テスト容易性のため、外部 API 呼び出し箇所は差し替え可能（unittest.mock.patch を想定）。

Breaking Changes
- なし

今後の予定（想定）
- strategy / execution / monitoring の実装拡張（パッケージ __all__ で宣言済み）。
- 単体テスト・統合テストの追加、ドキュメント整備、CI ワークフローの構築。
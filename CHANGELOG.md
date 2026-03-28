CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このファイルは "Keep a Changelog" の形式に準拠しています。
配布パッケージのバージョンはパッケージ内の __version__（0.1.0）に合わせています。

[Unreleased]
-------------

（現時点のコードベースが最初の公開バージョン相当のため、Unreleased に特別な変更はありません）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ構成
  - 初期リリースとして kabusys パッケージを追加。
  - サブパッケージ/モジュールを公開: data, research, ai, config, execution, monitoring（__all__ にて公開）。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルと OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から探索することで CWD に依存しない読み込みを実現。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途）。
  - .env のパースは以下に対応:
    - 空行・コメント行、export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い（非クォート時は '#' の直前が空白/タブのときのみコメントとして扱う）。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - 必須キー未設定時は例外を投げる _require を実装。
    - J-Quants / kabu / Slack / DB パスなどのプロパティを提供（デフォルト値や検証を含む）。
    - KABUSYS_ENV の許容値チェック（development / paper_trading / live）や LOG_LEVEL 検証実装。
    - duckdb/sqlite パスのデフォルトを設定（data/kabusys.duckdb 等）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI (gpt-4o-mini) を用いた銘柄別センチメント評価を行い、ai_scores テーブルへ書き込む。
    - ニュース時間ウィンドウ（JST基準の前日15:00〜当日08:30）を計算する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数・文字数制限）、JSON Mode による応答バリデーションを実装。
    - API エラー（429/接続断/タイムアウト/5xx）に対する指数バックオフリトライ、応答パース失敗時はスキップしてフェイルセーフで継続。
    - レスポンス検証（results 配列の有無、code の照合、数値変換、有限値チェック）、スコアは ±1 にクリップ。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて 'bull'/'neutral'/'bear' を判定し market_regime テーブルへ冪等書き込みする。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース抽出はタイトルベースでキーワードフィルタを適用（デフォルトキーワード群あり）。
    - OpenAI 呼び出しは JSON レスポンスを期待し、API の過負荷やサーバーエラーに対してリトライとフォールバック（macro_sentiment=0.0）を実装。
    - 設計上、news_nlp の内部関数とは共有せず独立した実装でモジュール結合を抑制。

- 研究用（research）モジュール（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。
    - モメンタム: 1M/3M/6M リターン、200日MA乖離（データ不足時は None）。
    - ボラティリティ/流動性: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率（NULL伝播制御を考慮）。
    - バリュー: raw_financials から最新財務を参照して PER, ROE を算出（EPS が 0/欠損であれば None）。
    - 全関数は prices_daily / raw_financials のみ参照し、本番発注 API へアクセスしない安全設計。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank を実装。
    - 将来リターンを一度のクエリで取得する最適化、horizon のバリデーション。
    - IC（Spearman の ρ）をランク化して計算、十分なサンプルがない場合は None を返す。
    - 統計サマリー（count, mean, std, min, max, median）を提供。依存ライブラリなし（標準ライブラリのみ）。
  - data.stats の zscore_normalize を再エクスポート。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未取得の場合は曜日ベース（土日休）でフォールバック。
    - DB 登録値優先、未登録日は曜日フォールバックにより next/prev/trading_days の一貫性を確保。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等的に保存（バックフィルと健全性チェックあり）。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラーの保持、ヘルパー to_dict）。
    - 差分更新・バックフィルロジック、品質チェックの収集（quality モジュール呼び出し）を設計方針として明記。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
  - jquants_client などの外部クライアント連携を想定した設計（fetch/save 関数を利用）。

- 汎用・運用面
  - DuckDB を主要なデータストアとして想定（DuckDB 接続オブジェクトを各関数で受け取る）。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT のような冪等性を意識したトランザクション処理を採用、エラー時は ROLLBACK を試行し失敗ログを残す。
  - ロギングを広範に追加し、重要な分岐や警告を出力。
  - ドキュメント的な docstring を各モジュールに充実させ、設計方針（ルックアヘッドバイアス防止、フェイルセーフ、テスト容易性等）を明記。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 環境変数による API キー管理（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）を想定。必須項目は Settings で明確化し、未設定時は ValueError を投げる。

Known limitations / Notes
- ai モジュールは OpenAI (gpt-4o-mini) の JSON Mode を利用する前提で実装。実運用時は API レートやコスト管理が必要。
- news_nlp と regime_detector はそれぞれ独立して OpenAI 呼び出し実装を持つ（意図的な分離）。
- calc_value は現時点で PBR・配当利回りは未実装。
- DuckDB の executemany に関する互換性（空リスト不可など）を考慮した実装となっている。
- ETL / calendar_update_job は外部 J-Quants クライアントの実装（fetch/save）が存在することを前提とする。
- 日時の扱いはすべて timezone-naive（date / datetime）で統一し、JST/UTC 変換はドキュメントに従っている。ルックアヘッドバイアス回避のため datetime.today() 等を直接参照しない設計。

参照 API（主な公開関数）
- kabusys.config.settings（Settings インスタンス）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
- kabusys.data.pipeline.ETLResult
- kabusys.data.etl.ETLResult（再エクスポート）

今後の予定（memo）
- PBR / 配当利回り等のバリューファクター追加。
- AI モデルの切替やプロンプト改善、スコアのキャリブレーション。
- ETL の並列化・パフォーマンス最適化、品質チェックの強化。
- 単体テスト・統合テストの追加（現在はテストフックを散在させているが網羅は未実装）。
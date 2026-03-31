CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。
日付は本リリース作成日です。

Unreleased
----------

- なし

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初回リリースを追加。
  - パッケージメタ情報: kabusys v0.1.0（src/kabusys/__init__.py）。
  - 主要モジュール群を提供: data, research, ai, monitoring, strategy, execution（__all__ エクスポート）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを導入。
  - export KEY=val、クォート（シングル/ダブル）、バックスラッシュエスケープ、コメント処理等を考慮した .env パーサを実装。
  - OS 環境変数を保護する protected 機構（.env.local での上書き制御含む）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須設定を取得する Settings クラスを実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - デフォルト値とバリデーションを提供: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）、DuckDB/SQLite のデフォルトパス。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチ評価して銘柄別センチメント（ai_scores）を生成。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換を行い DB と比較）。
  - バッチ処理（最大 20 銘柄/回）、1銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。
  - OpenAI レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、code/score 型チェック、スコアの ±1.0 クリップ）。
  - 部分成功を考慮した冪等的 DB 書き込み（対象 code の DELETE → INSERT。DuckDB executemany 空リスト回避の配慮）。
  - テストフック: _call_openai_api を unittest.mock.patch で差し替え可能。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
  - MA200 計算は target_date 未満のデータのみ使用（ルックアヘッドバイアス防止）。
  - マクロニュースは news_nlp.calc_news_window と同様のウィンドウで抽出し、OpenAI を呼び出して macro_sentiment を評価。API 失敗時は macro_sentiment=0.0 にフォールバック。
  - レジームスコア合成・閾値判定、および冪等的な DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）。

- データプラットフォーム: カレンダー管理（src/kabusys/data/calendar_management.py）
  - market_calendar を用いた営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
  - DB にデータがない/未登録日は曜日ベースのフォールバック（土日非営業）を行う一貫した挙動。
  - next/prev の最大探索日数制限（_MAX_SEARCH_DAYS）による無限ループ防止。
  - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants API から差分取得、バックフィル、健全性チェック、保存（jquants_client 経由）を行う。

- ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
  - ETLResult データクラスを追加（取得・保存件数、品質問題、エラーの集約、to_dict メソッド）。
  - テーブル存在チェック、最大日付取得などのユーティリティ関数。
  - デフォルトの差分更新方針、バックフィル設定、品質チェックの設計方針を実装（quality モジュールと連携する想定）。
  - etl モジュールで ETLResult を再エクスポート。

- 研究用モジュール（src/kabusys/research/）
  - factor_research.py:
    - モメンタム（1M/3M/6M）、ma200_dev、ATR（20日）、相対ATR、平均売買代金、出来高比率、PER/ROE（raw_financials 結合）などのファクター計算を実装。
    - DuckDB 統合 SQL を多用し高速計算を想定。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない純標準ライブラリ実装（DuckDB のみ依存）。

- パッケージエクスポート整理
  - ai.__init__ で score_news を公開。
  - research.__init__ で主要関数を公開。
  - data.etl が ETLResult を公開。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API キー / 各種トークン等は環境変数から取得する設計。Settings.require により未設定時は ValueError を発生させることで誤動作を防止。
- .env 自動ロード時に OS の既存環境変数を保護する実装（protected set）。

注意・移行ガイド
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能使用時）
- .env 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。
- DuckDB / SQLite のデフォルトパスは settings.duckdb_path / settings.sqlite_path で指定可能。必要に応じて環境変数で上書きしてください。
- OpenAI 周りはテストフック（_call_openai_api の差し替え）を用意しているため、ユニットテストでモック可能です。
- DuckDB の executemany の挙動やリストバインドはバージョン差分で振る舞いが異なるため、空リストを渡さない等の互換性対策を実装しています。

既知の制約
- news_nlp / regime_detector は OpenAI の JSON mode に依存。API のレスポンス形式や SDK の変更（status_code 等）には注意して運用してください（コード中で互換性を配慮した実装あり）。
- 一部関数は DuckDB の日付値や行番号処理に依存しており、他 DB への移植時に SQL の調整が必要になる可能性があります。

ライセンス・貢献
- 本リリースは初期実装のため、今後の拡張で API 安全性・エラー可観測性・性能改善を予定しています。貢献・バグ報告はリポジトリの Issues / PR を通じて行ってください。
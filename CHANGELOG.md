# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトの初版リリース情報を以下に示します。

最新: Unreleased
===============

[Unreleased]
------------

- なし

v0.1.0 - 2026-03-31
===================

Added
-----

- パッケージ初期構成
  - パッケージ名: `kabusys`
  - エントリポイント: `src/kabusys/__init__.py`（__version__ = "0.1.0"、公開サブパッケージ: data, strategy, execution, monitoring）

- 環境変数／設定管理
  - `kabusys.config.Settings`
    - `.env` / `.env.local` の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
    - 環境変数ロードの上書き挙動（override / protected）をサポート
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化（テスト向け）
    - `.env` 行の高度なパース機能（export プレフィックス、クォート文字のエスケープ処理、インラインコメントの扱い）
    - 必須 env の取得 `_require`（未設定時は ValueError）
    - 標準的な設定プロパティを提供:
      - J-Quants / kabu ステーション / Slack / DB パス（DuckDB, SQLite）/ 環境種別（development/paper_trading/live）/ ログレベル 等
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証を実装

- AI（自然言語処理）モジュール
  - `kabusys.ai.news_nlp`
    - `score_news(conn, target_date, api_key=None)` を実装
      - ニュースのタイムウィンドウ計算（JST基準 → UTC変換）
      - `raw_news` と `news_symbols` から銘柄ごとに記事を集約（最大記事数／文字数でトリム）
      - OpenAI（gpt-4o-mini）へチャンク（最大20銘柄）で送信し JSON Mode で結果を取得
      - レスポンスのバリデーション、スコアクリップ（±1.0）
      - 成功した銘柄のみ `ai_scores` テーブルへ置換的に書き込み（DELETE → INSERT）
      - ネットワーク断・429・タイムアウト・5xx に対する指数バックオフリトライ、失敗時は部分的にスキップして継続
    - `calc_news_window(target_date)` を提供（前日15:00 JST ～ 当日08:30 JST を対象）
    - 内部で OpenAI 呼び出しを行う `_call_openai_api` はテストで差し替え可能（patch 用）

  - `kabusys.ai.regime_detector`
    - `score_regime(conn, target_date, api_key=None)` を実装
      - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定
      - `prices_daily` からの MA200 比率計算（ルックアヘッド回避のため target_date 未満のデータのみ使用）
      - マクロキーワードによる `raw_news` 抽出と LLM 評価（最大記事数上限）
      - OpenAI 呼び出しのリトライ・フェイルセーフ（API失敗時は macro_sentiment=0.0）
      - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）
    - レジーム合成の閾値・スケーリング等を定数化

- Data（データ基盤）モジュール
  - `kabusys.data.calendar_management`
    - JPX カレンダー管理ロジック（`market_calendar` テーブルと連携）
    - 営業日判定 API:
      - `is_trading_day(conn, d)`
      - `is_sq_day(conn, d)`
      - `next_trading_day(conn, d)`
      - `prev_trading_day(conn, d)`
      - `get_trading_days(conn, start, end)`
    - DB 登録データを優先し、未登録日は曜日ベース（週末除外）でフォールバックする一貫した挙動
    - 最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止
    - 夜間バッチ: `calendar_update_job(conn, lookahead_days=90)` を実装（J-Quants クライアント経由で取得 → 保存、バックフィル、健全性チェック）

  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL のためのユーティリティ実装（差分更新、バックフィル、品質チェックを想定）
    - `ETLResult` dataclass を実装し `kabusys.data.etl` で再エクスポート
      - ETL 実行結果（取得件数・保存件数・品質問題・エラーメッセージ等）を構造化
      - `has_errors`, `has_quality_errors`, `to_dict()` を提供
    - DuckDB に関するヘルパー (`_table_exists`, `_get_max_date`) を追加

  - その他
    - DuckDB の制約（executemany に空リストを渡せないなど）に配慮した実装

- Research（研究／リサーチ）モジュール
  - `kabusys.research.factor_research`
    - ファクター計算: `calc_momentum`, `calc_volatility`, `calc_value`
      - Momentum: 1M/3M/6M リターン、ma200_dev（200日MA乖離）
      - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
      - Value: PER（EPSが0/欠損時は None）および ROE（raw_financials から取得）
    - DuckDB を用いた SQL ベースの実装。外部API呼び出し無し。結果は (date, code) キーの dict リストで返却

  - `kabusys.research.feature_exploration`
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト [1,5,21]）
    - IC 計算（Spearman のランク相関）: `calc_ic(factor_records, forward_records, factor_col, return_col)`
    - 統計サマリー: `factor_summary(records, columns)`
    - ランク変換: `rank(values)`（同順位は平均ランク、丸めで ties 検出漏れ対策）
    - 外部ライブラリ依存を避け、標準ライブラリのみで実装

Changed
-------

- 初版のため該当なし

Fixed
-----

- 初版のため該当なし

Security
--------

- OpenAI API キーは明示的に引数で渡すか環境変数 `OPENAI_API_KEY` を利用する設計。
- AI 関連関数は API キー未設定時に ValueError を送出し誤用を防止。
- `.env` ファイルの読み取りは UTF-8 指定、読み込み失敗時は警告ログを出力して継続。

Notes / Implementation details
------------------------------

- ルックアヘッドバイアス対策:
  - AI モジュールおよび研究モジュールはいずれも内部で現在時刻を参照しない設計（呼び出し側が target_date を指定）
  - DB クエリは target_date 未満や半開区間等を用いて未来データ参照を回避

- フォールトトレランス:
  - OpenAI 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx に対する再試行ロジックを実装。上限到達時はフェイルセーフ値（例: macro_sentiment=0.0）を採用して処理を継続
  - DB 書き込みは明示的なトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK 失敗時は警告出力

- テスト性:
  - OpenAI 呼び出し用の内部関数（`_call_openai_api`）はモジュール単位で差し替え可能に実装（unittest.mock.patch を想定）
  - `.env` 自動ロードの無効化フラグあり（テストで環境を固定可能）

- 既知の前提:
  - DuckDB の使用を前提（SQL の日付型が date/ISO 文字列で返る等）
  - `jquants_client`（外部モジュール）に依存する部分がある（カレンダーやデータ取得）

---

今後の予定（例）
- strategy / execution / monitoring の具体的な実装追加
- 単体テスト・統合テストの充実
- ドキュメント（API リファレンス、運用手順）の整備

もし特定の変更点（より詳細な関数単位の記述や差分の想定）を追加で反映したい場合は、対象機能を指定していただければ追記します。
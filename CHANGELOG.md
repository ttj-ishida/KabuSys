Keep a Changelog 準拠 — CHANGELOG.md
=================================

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン
----------------

- 0.1.0 — 2026-03-29

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py: __version__ = "0.1.0"、公開サブパッケージ data, strategy, execution, monitoring を定義。
- 環境設定・読み込み:
  - src/kabusys/config.py:
    - .env/.env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
    - .env のパースを堅牢化（export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメント処理）。
    - _load_env_file で既存 OS 環境変数保護（protected set）や override の挙動を実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベース / システム設定等の取得プロパティを定義（必須値は未設定時に ValueError を送出）。
    - デフォルト値: KABUSYS_ENV="development"、KABUSYS_ENV の有効値検証、LOG_LEVEL の検証、デフォルト DB パス（duckdb/sqlite）など。
- AI（NLP）モジュール:
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事に対する銘柄別センチメント解析機能 score_news を実装。
    - JST ベースのニュース収集ウィンドウ計算 calc_news_window（前日 15:00 JST〜当日 08:30 JST を UTC に変換して使用）。
    - raw_news + news_symbols から銘柄ごとに記事を集約し、1銘柄あたり最大記事数・文字数でトリム。
    - バッチ処理（1 API コール当たり最大 _BATCH_SIZE=20 銘柄）。
    - OpenAI（gpt-4o-mini）への JSON Mode 呼び出し、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の検証、未知コード無視、スコアを ±1.0 にクリップ）。
    - DuckDB への冪等書込み（対象コードのみ DELETE → INSERT、executemany の空リスト制約に対応）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に実装。
  - src/kabusys/ai/regime_detector.py:
    - 市場レジーム判定 score_regime を実装（'bull' / 'neutral' / 'bear'）。
    - ETF 1321（日経225 連動）200日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成。
    - マクロニュースは news_nlp.calc_news_window で得たウィンドウから抽出、LLM は gpt-4o-mini を使用。
    - API 呼び出しはリトライ（429/接続/タイムアウト/5xx）を実装、全失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - レジームスコアをクリップし閾値に基づきラベル付与。結果は market_regime テーブルへ冪等書込み（BEGIN/DELETE/INSERT/COMMIT）。
    - モジュール結合を避けるため、OpenAI 呼び出しロジックは news_nlp と別実装（ただしテストで差し替え可能）。
- データ管理（Data platform）:
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先し、未登録日は曜日ベースフォールバック（土日非営業）で一貫性を保つ設計。
    - calendar_update_job により J-Quants API から差分取得し冪等保存（バックフィル、健全性チェック、lookahead）。
    - 探索範囲上限と不整合保護（_MAX_SEARCH_DAYS、_SANITY_MAX_FUTURE_DAYS、_BACKFILL_DAYS）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py:
    - ETL パイプラインの基盤機能を追加。
    - ETLResult データクラスを定義（取得件数、保存件数、品質チェック結果、エラー一覧、シリアライズ用 to_dict）。
    - 差分取得のためのテーブル最終日取得ユーティリティ（_get_max_date）やテーブル存在チェックを実装。
    - J-Quants クライアント（jquants_client）および品質チェック（quality）との連携を想定した設計。
- リサーチ（ファクター・探索）:
  - src/kabusys/research/factor_research.py:
    - ファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）。
      - calc_volatility: atr_20（20日 ATR）/ atr_pct / avg_turnover / volume_ratio。
      - calc_value: per / roe（raw_financials の最新報告より）。
    - DuckDB に対する SQL ベース実装、外部 API への依存なし。
    - 不足データ（例：必要行数未満）は None を返す設計。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: スピアマンランク相関（IC）計算、十分なサンプルがない場合は None。
    - rank, factor_summary: ランク変換（同順位は平均ランク）、カラム別統計サマリー（count/mean/std/min/max/median）。
    - 実装は標準ライブラリのみ、DuckDB 接続を前提とする。
- 実装上の配慮・設計方針（全体）:
  - ルックアヘッドバイアスを防ぐために datetime.today() / date.today() の直接参照を避け、すべての関数は target_date を受け取って決定。
  - API 呼び出し失敗時はフェイルセーフ（スコアは 0.0、該当銘柄はスキップ）で継続する設計。
  - DuckDB のバージョン差異（executemany の空リスト不許可等）に対する互換性処理を行っている。
  - ロギングと警告を広範に追加し、異常ケースを可視化。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

注記・使用例
- 環境変数取得の例:
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token
- News / Regime スコアリング:
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)
  - どちらも api_key が None の場合は環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出する。
- DuckDB 接続（DuckDBPyConnection）を呼び出し側で準備して渡すこと。

今後の TODO（想定）
- strategy / execution / monitoring の具体実装（現在はパッケージ公開のみ）。
- jquants_client, quality の詳細実装・テストカバレッジ強化。
- CI 環境向けの統合テスト（OpenAI 呼び出しのモック置換の標準化）。
- ドキュメント（API リファレンス・設計ドキュメント）とサンプルワークフローの追加。

履歴
- このファイルは初期リリース時点の機能をまとめたものです。今後のバージョン更新では追加・修正・互換性情報をここに追記します。
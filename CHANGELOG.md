CHANGELOG
=========
すべての公開変更は "Keep a Changelog" の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージメタ:
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - エントリポイント: src/kabusys/__init__.py

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env および .env.local）をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは以下をサポート:
    - コメント行、空行、export KEY=val 形式
    - シングル/ダブルクォート内のエスケープ処理
    - クォート無しの行で '#'(直前が空白/タブ) をインラインコメントとして扱う
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス / ログレベル / 実行環境（development/paper_trading/live）などのプロパティを安全に取得
    - 必須キー未設定時は ValueError を送出する _require 実装
    - env / log_level の検証（無効値は ValueError）

- AI (自然言語処理) モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して、銘柄ごとに OpenAI (gpt-4o-mini, JSON Mode) へバッチ送信してセンチメントを算出
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換してDB照合）
    - バッチサイズ、記事トリム（最大記事数・最大文字数）や JSON レスポンスのバリデーション実装
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、その他はスキップ
    - API レスポンスパース失敗や異常時は該当銘柄をスキップ（フェイルセーフ）
    - DuckDB 互換性的配慮: executemany に空リストを与えないガード
    - public API: score_news(conn, target_date, api_key=None) — 書き込み件数を返す。api_key は引数注入可能（テスト容易性）
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して 'bull'/'neutral'/'bear' を日次判定
    - prices_daily と raw_news を参照し、計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）
    - LLM 呼び出しは失敗時に macro_sentiment=0.0 とするフェイルセーフ
    - public API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。api_key 引数で OpenAI キーを注入可能
    - OpenAI との通信は retry/backoff・5xx 判定・JSON パースの耐障害性を考慮

- データ関連モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを使った営業日判定ユーティリティ群:
      - is_trading_day(conn, d)、next_trading_day、prev_trading_day、get_trading_days、is_sq_day
    - DB にデータがない／未登録日の場合は曜日ベースでフォールバック（土日を非営業日と扱う）
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル、健全性チェックを実装
    - calendar_update_job(conn, lookahead_days=90) を提供し、J-Quants クライアント経由で差分取得→保存する夜間処理を実装（fetch/save の例外を安全に扱う）
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult dataclass を公開（ETL 実行結果の構造化）
    - 差分取得・保存・品質チェックフローに基づく ETL のためのユーティリティ（詳細実装は pipeline 内）
    - DuckDB のテーブル存在チェック、最大日付取得などのヘルパーを実装
    - 実装方針: idempotent 保存（ON CONFLICT DO UPDATE 想定）、バックフィル、品質チェックの収集（Fail-Fast ではない）
  - jquants_client と quality モジュールを呼び出す設計（外部 API・品質チェックを分離）

- リサーチ / ファクター分析 (kabusys.research)
  - 研究向けユーティリティ群を提供:
    - factor_research: calc_momentum, calc_value, calc_volatility
      - Momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）
      - Value: PER（EPS が 0/NULL の場合は None）、ROE（raw_financials を参照）
      - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
      - DuckDB SQL を活用し営業日・ウィンドウ処理を行う（ルックアヘッドバイアス回避）
    - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
      - 将来リターン（任意ホライズン）を一度の SQL で取得する効率化
      - Spearman 型のランク相関（IC）計算、同順位は平均ランクで処理
      - 基本統計量（count/mean/std/min/max/median）算出ユーティリティ
    - zscore_normalize を data.stats から再エクスポート
  - 全て DuckDB 接続を受け取り DB のみ参照（発注API等にアクセスしない）

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Deprecated
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- OpenAI API キーの取り扱い:
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY のいずれかを要求。未設定時は ValueError を送出して安全に停止。
  - .env 自動ロード処理は既存 OS 環境変数を保護する（protected set を使用して上書き回避）

Notes / マイグレーション（利用者向け重要点）
- .env 自動読み込み
  - 自動的にプロジェクトルートを探索して .env, .env.local をロードします。テスト・CI 等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。
- OpenAI クライアント
  - デフォルトモデルは gpt-4o-mini。レスポンスは JSON Mode（response_format={"type":"json_object"}）を想定しています。
  - テスト時はモジュール内の _call_openai_api をパッチして API 呼び出しを差し替え可能です。
- DuckDB 互換性
  - executemany に空リストを渡すとエラーとなる DuckDB の挙動に対応するため、空リストチェックを挟んでいます。
- ルックアヘッドバイアス対策
  - 全ての時刻計算において date.today()/datetime.today() を直接参照しない設計（関数呼び出し側から target_date を渡す形）を採用しています。
- フェイルセーフ設計
  - AI の呼び出し失敗やパース失敗は基本的に例外を投げずフェイルセーフ（該当スコアを 0.0 にフォールバック、あるいは当該銘柄をスキップ）しています。ただし DB 書き込み失敗時は上位へ伝播（ロールバック処理あり）。

今後の予定（示唆）
- ai モジュールの追加テストカバレッジ強化、OpenAI 冗長化戦略、モデル切替オプションの拡充
- ETL パイプラインのジョブ化・スケジューリングサポート、品質チェックのルール拡張
- research モジュールの追加ファクター・パフォーマンス計測機能の拡張

----
この CHANGELOG は、提供されたソースコードの実装内容から推測して作成した初期リリース記録です。実際のリリースノートやバージョン管理履歴に合わせて更新してください。
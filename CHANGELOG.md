Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは、語意的バージョニングに従います。

[0.1.0] - 2026-03-31
--------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムのコアモジュール群を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py にてバージョンを 0.1.0 として公開。
    - パッケージの公開 API: data, research, ai 等（__all__ の一部は将来的な拡張を想定）。
  - 設定・環境読み込み
    - src/kabusys/config.py
      - .env および .env.local の自動読み込み実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - .env パーサ: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの取り扱いなどを考慮。
      - 環境変数の保護機構（OS 環境変数を protected として .env.local が上書きしても保護できる）。
      - Settings クラスを提供（必須値は取得時に ValueError を送出）。J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / 環境・ログレベル検証などのプロパティを用意。
      - ログレベル・環境値のバリデーション（許容値チェック）。
  - AI: ニュース NLP と市場レジーム判定
    - src/kabusys/ai/news_nlp.py
      - raw_news, news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を使ってバッチでセンチメントスコアを取得。
      - タイムウィンドウ（JST 前日15:00〜当日08:30）計算ユーティリティ calc_news_window を実装。
      - バッチ処理（最大 20 銘柄 / チャンク）、文字数・記事数トリム、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）とフォールバック動作。
      - レスポンスバリデーション（JSON 抽出、results キー、code/score 型検査、スコアクリップ ±1.0）。
      - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存スコアを残す設計）。
      - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api をモック可能）。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
      - MA 計算は target_date 未満のデータのみを利用してルックアヘッドバイアスを防止。
      - マクロキーワードで raw_news をフィルタ、OpenAI（gpt-4o-mini） でマクロセンチメントを評価（記事なし時は LLM 呼び出しを行わず、API 失敗時は macro_sentiment=0.0 としてフェイルセーフ）。
      - レジーム値の合成ルール・閾値設定・DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
      - API 呼び出しのリトライとエラー分類（RateLimit/APIConnection/APITimeout/APIError の扱い）を実装。
  - データ基盤（Data platform）
    - src/kabusys/data/calendar_management.py
      - JPX マーケットカレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ群を実装。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
      - DB にカレンダーがない/未登録の場合は曜日ベースのフォールバック（週末は非営業日）を使用。
      - calendar_update_job: J-Quants クライアント経由で差分取得 → 冪等保存（保存は jquants_client モジュールへ委譲）、バックフィルと健全性チェックを実装。
    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
      - ETL パイプラインの骨格: 差分取得、保存、品質チェックフローに対応。
      - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの収集、辞書化ユーティリティを含む）。
      - pipeline 内部ユーティリティ（テーブル存在確認、最大日付取得など）を実装。設計上、backfill・品質チェックは処理継続を前提に問題を収集する。
    - jquants_client など外部クライアントは data.jquants_client 経由で利用する想定（本差分はクライアント実装に依存）。
  - 研究（Research）ユーティリティ
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金等）、バリュー（PER/ROE）等の計算を実装。
      - DuckDB 上で SQL を用いて効率的に計算し、(date, code) ベースの辞書リストを返す設計。
      - データ不足時の扱いや NULL 管理を明示。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換（rank）、ファクター統計サマリ（factor_summary）を実装。
      - pandas 等に依存せず、標準ライブラリ + DuckDB で完結する実装。
    - src/kabusys/research/__init__.py
      - 主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize の再エクスポートなど）。
  - その他
    - DuckDB を主要なローカルストレージとして利用する実装前提。
    - 多くのモジュールで「datetime.today()/date.today() を直接参照せず target_date を受け取る」設計によりルックアヘッドバイアスを防止。
    - OpenAI 呼び出し部分は各モジュール内で独立実装し、モジュール間でプライベート関数を共有しない設計（テストと疎結合のため）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーが未設定の場合は明示的に ValueError を送出して失敗させる箇所あり（news_nlp.score_news, regime_detector.score_regime）。
- 環境変数の自動読み込みは明示的に無効化できるフラグを用意（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Caveats
- OpenAI API の利用には環境変数 OPENAI_API_KEY（または api_key 引数）が必須。API エラー時はフェイルセーフ（ニューススコア・マクロスコアを 0 にフォールバックする等）を多く採用しているため、部分的失敗が全体を致命化しにくい設計になっている。
- DuckDB バインディングや executemany の空リスト制約などの実装上の互換性注意点（コード内に注釈あり）。
- jquants_client や kabu ステーション連携など、外部クライアントの実装は別途提供される前提。
- 単体テスト容易性のため、OpenAI 呼び出し箇所は patch/モック可能に設計。

Contributors
- 初期実装（単独またはチームによる）を反映。

今後
- strategy / execution / monitoring などの実行系モジュールの実装拡張。  
- テストカバレッジの拡充、CI / デプロイ関連のドキュメント整備。
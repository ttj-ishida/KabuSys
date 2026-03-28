Keep a Changelog 準拠 — 変更履歴

すべての注目すべき変更はここに記録します。フォーマットは「Keep a Changelog」に従っています。

Unreleased
----------
（現在なし）

[0.1.0] - 2026-03-28
--------------------
Added
- 初回リリース。KabuSys パッケージの基本機能を実装。
  - パッケージ初期化:
    - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。パッケージ API として data, strategy, execution, monitoring をエクスポート。

  - 設定管理:
    - src/kabusys/config.py
      - .env ファイル（.env, .env.local）と OS 環境変数を統合して設定を読み込む自動ロード機能を実装。
      - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
      - export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメント等の .env パースに対応する堅牢なパーサを実装。
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - 環境値保護（protected）を用いた .env 上書きロジック。
      - 必須設定取得用 _require と Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス等の設定をプロパティで取得可能。
      - KABUSYS_ENV, LOG_LEVEL のバリデーション、is_live / is_paper / is_dev 等のユーティリティを実装。

  - AI（NLP）:
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（ai_score）を算出し ai_scores テーブルへ書き込む処理を実装。
      - 前日 15:00 JST ～ 当日 08:30 JST の時間ウィンドウ算出（calc_news_window）。
      - 1銘柄あたり記事数・文字数のトリミング（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - バッチ処理（_BATCH_SIZE=20）・JSON Mode を用いた API 呼び出し、429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライ。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造、未知コード除外、数値判定、スコア ±1.0 でクリップ）。
      - DuckDB 互換性考慮（executemany に空リストを渡さない等）、部分失敗時に既存スコアを保護する DELETE→INSERT の置換処理。
      - テスト容易性のため _call_openai_api の差し替え（patch）が可能。
      - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動型）200日移動平均乖離とマクロニュースの LLM センチメントを重み付け（70% / 30%）して市場レジーム（bull / neutral / bear）を判定し market_regime テーブルに保存する処理を実装。
      - ルックアヘッドバイアス防止: target_date 未満のみを参照、datetime.today()/date.today() を用いない設計。
      - マクロキーワードで raw_news を抽出し OpenAI に投げる処理（_score_macro）を実装。API 障害時はフェイルセーフで macro_sentiment=0.0。
      - リトライ・エラーハンドリング（RateLimit, APIConnection, APITimeout, APIError の 5xx 判定）を実装。
      - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、例外時は ROLLBACK を試行して再送出。
      - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

    - src/kabusys/ai/__init__.py
      - score_news を公開（__all__ に score_news を追加）。

  - データ基盤ユーティリティ:
    - src/kabusys/data/calendar_management.py
      - JPX マーケットカレンダー（祝日・半日・SQ日）に関する判定・探索関数を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - market_calendar テーブルが未取得の場合は曜日ベースのフォールバック（平日を営業日とする）。
      - 最大探索日数制限 (_MAX_SEARCH_DAYS)、バックフィル・健全性チェック等を実装。
      - calendar_update_job(conn, lookahead_days) により J-Quants から差分取得→保存を行う処理を提供（jq.fetch_market_calendar / jq.save_market_calendar を利用）。

    - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
      - ETL パイプラインの骨格を実装。
      - 差分取得、保存（jquants_client 経由で idempotent 保存を想定）、品質チェック（quality モジュールによる収集）を設計に組み込む。
      - ETLResult dataclass を実装し etl 実行の結果（取得・保存件数、品質問題一覧、エラー一覧）を表現。to_dict() により品質問題をシリアライズ可能。
      - DuckDB テーブル存在チェック・最大日付取得ユーティリティを提供。
      - ETL の設計方針や backfill の挙動を明文化。

    - src/kabusys/data/__init__.py
      - ETLResult を再エクスポート（kabusys.data.etl の形で公開）。

    - jquants_client / quality 等のクライアントは参照して使用する設計（実具体実装は別モジュール想定）。

  - 研究（Research）モジュール:
    - src/kabusys/research/factor_research.py
      - モメンタム（1m/3m/6m リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）などを DuckDB の prices_daily / raw_financials から計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
      - データ不足時の扱い（必要データ未満は None を返す）やスキャン範囲（バッファ）を明確化。
      - 出力は date, code を含む dict のリスト形式。

    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）算出（calc_ic）、ランク変換ユーティリティ（rank）、およびファクター統計サマリー（factor_summary）を実装。
      - Spearman（ランク相関）をランク化（同順位は平均ランク）して計算。入力バリデーションと NaN/有限性のチェックを行う。
      - pandas 等の外部依存を避け、標準ライブラリと DuckDB クエリで完結する設計。
      - src/kabusys/research/__init__.py で主要関数群を公開。

  - 共通設計上の注意点（ドキュメント化・実装内コメント）:
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計方針を徹底。
    - OpenAI 呼び出しについては JSON Mode を利用し、パース失敗や一部テキスト混入に対する復元ロジックを備える。
    - API 呼び出しはリトライ + 指数バックオフを採用し、致命的失敗ではフェイルセーフなデフォルト値（例: macro_sentiment=0.0）を用いる。
    - DuckDB の互換性・制約（executemany の空リスト不可等）に配慮した実装。
    - テストしやすさを考慮し、API 呼び出し箇所（内部 _call_openai_api 等）を差し替え可能に設計。

Security
- 環境変数の扱いで OS 環境変数を保護するため .env 読み込み時に既存 OS 環境変数を保護するロジックを実装。
- API キー未設定時は明示的に ValueError を送出して安全に停止する箇所を用意（score_news / score_regime 等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Known limitations
- jquants_client, quality 等の外部クライアント実装は別モジュールに依存するため、実際の ETL 実行や calendar_update_job 実行時はそれらの実装が必要。
- OpenAI API 呼び出しは gpt-4o-mini を想定して実装している。API の将来的な仕様変更（例: SDK のレスポンス形式変更等）には注意。
- strategy / execution / monitoring パッケージは __all__ に含まれるが、本スナップショットに完全な発注ロジック等の実装が含まれていない可能性がある（研究・データ・NLP 基盤が中心の初期フェーズ）。

以上。
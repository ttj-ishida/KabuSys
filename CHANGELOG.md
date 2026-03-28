CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
現在のパッケージバージョン: 0.1.0

Unreleased
----------

（なし）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初回リリース (kabusys 0.1.0)
  - パッケージのエントリポイントを追加
    - src/kabusys/__init__.py: __version__ = "0.1.0"、公開モジュール名の定義（data, strategy, execution, monitoring）
  - 環境設定・自動 .env ロード
    - src/kabusys/config.py:
      - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を起点に探索）。
      - .env / .env.local の自動読み込み機能（OS 環境変数を保護し、.env.local は override=true）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
      - .env パーサの実装：コメント行、export プレフィックス、クォート文字列、エスケープ、インラインコメント処理に対応。
      - Settings クラスを導入し、アプリ設定をプロパティ経由で取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。
      - env / log_level の値検証（有効な値セットを定義し、不正値で ValueError を発生）。
  - AI（NLP）モジュール
    - src/kabusys/ai/news_nlp.py:
      - raw_news / news_symbols を基に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ保存する処理を実装。
      - 時間ウィンドウ（JST基準: 前日15:00〜当日08:30）を計算する calc_news_window を提供。
      - API バッチ送信（チャンクサイズ _BATCH_SIZE=20）、1銘柄あたりのトリム（最大記事数・最大文字数）や JSON mode を想定したレスポンスバリデーション実装。
      - 再試行ポリシー（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）、失敗時はスキップ（フェイルセーフ）。
      - レスポンス検証ロジック（JSON 抽出、results 配列検証、未知コード無視、スコアの数値性検査、±1.0 にクリップ）。
      - テスト用フック: _call_openai_api を patch して差し替え可能。
    - src/kabusys/ai/regime_detector.py:
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する score_regime を実装。
      - prices_daily / raw_news からデータ取得、OpenAI（gpt-4o-mini）呼び出し、冪等的な market_regime テーブルへの書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバック。API リトライ（最大回数・バックオフ）を備える。
      - デザイン方針として datetime.today()/date.today() を参照せず、ルックアヘッドバイアスを排除。
  - Data / ETL / カレンダー
    - src/kabusys/data/pipeline.py:
      - ETL の結果を保持する ETLResult dataclass を公開（取得件数・保存件数・品質問題・エラー集約・ユーティリティメソッド to_dict を提供）。
      - 差分取得のための内部ユーティリティ（テーブル存在確認、最大日付取得など）を実装。
      - ETL の設計方針（backfill、品質チェックの扱い等）を実装に反映。
    - src/kabusys/data/etl.py:
      - pipeline.ETLResult を再エクスポート（外部公開インターフェース）。
    - src/kabusys/data/calendar_management.py:
      - market_calendar を用いた営業日判定機能を実装:
        - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
      - DB にデータがない日については曜日ベース（土日）でフォールバックする一貫したロジック。
      - calendar_update_job: J-Quants API からカレンダーを差分取得して保存する夜間ジョブ（バックフィル・健全性チェック・API エラー時の例外処理を実装）。
      - 最大探索日数制限、バックフィル日数、先読み日数などの定数を定義。
  - Research（ファクター・特徴量解析）
    - src/kabusys/research/factor_research.py:
      - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金/出来高比）、バリュー（PER, ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
      - DuckDB の SQL ウィンドウ関数を多用し、欠損やデータ不足時に None を扱う設計。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算 calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算 calc_ic、ランク関数 rank、ファクター統計 summary（factor_summary）を実装。
      - pandas 等に依存せず標準ライブラリのみで実装。
    - src/kabusys/research/__init__.py:
      - 主要関数を再エクスポートして公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - データユーティリティ（空の __init__ を配置してパッケージ化）

Security
- OpenAI / 各種 API キーの取り扱いに注意
  - news_nlp.score_news, regime_detector.score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必須とする（未設定時は ValueError を送出）。
  - 環境変数読み込み時に OS 環境変数を保護する実装（protected set）。.env.local は既存環境変数を上書きするが、OS の環境変数は上書きされない。

Design / Reliability Notes
- ルックアヘッドバイアス対策: 全ての AI / 研究ロジックは内部で datetime.today() を参照せず、呼び出し元が target_date を明示する設計。
- DuckDB への書き込みは冪等性を重視（DELETE→INSERT のパターンや ON CONFLICT を想定）。トランザクション（BEGIN/COMMIT/ROLLBACK）を適切に扱う。
- OpenAI 呼び出しは JSON mode（厳密な JSON 出力）を期待しつつ、パーサ耐性（前後に余計なテキストが混入した場合の {} 抽出など）を実装。
- テスト容易性のため、AI 呼び出し部分に patch 可能な内部関数（_call_openai_api 等）を用意。

Known limitations / Notes
- release 0.1.0 は初期実装のため以下の点が残る可能性あり:
  - strategy / execution / monitoring パッケージの具体実装はこの差分内に含まれていない（__all__ に名前がある）。
  - 現時点では gpt-4o-mini を想定したプロンプト・レスポンス形式に密接に依存しているため、別モデルや将来の API 変更には対応が必要な箇所がある。
  - DuckDB バージョン依存のバインド仕様（executemany に空リストを渡せない等）に対するワークアラウンドを含む実装があるため、環境によっては挙動確認が必要。

以上が初回リリース（0.1.0）で導入された主な機能・設計上の注意点です。追加でセクション分けや詳細化（例: 各関数の引数・戻り値の変更履歴など）が必要であればお知らせください。
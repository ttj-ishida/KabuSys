CHANGELOG
=========

すべての重要な変更点をここに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

v0.1.0 - 2026-03-31
-------------------

Added
- 初期リリース。日本株自動売買プラットフォーム「KabuSys」のコアモジュールを追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__ = "0.1.0"、主要サブパッケージを __all__ で公開。
  - 環境変数・設定管理
    - src/kabusys/config.py
      - .env / .env.local をプロジェクトルートから自動読み込み（優先順: OS 環境 > .env.local > .env）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
      - .env パーサは export KEY=val 形式、引用符（シングル/ダブル）内のバックスラッシュエスケープ、行中コメント処理に対応。
      - 既存 OS 環境変数を保護するための protected キー処理を実装。
      - Settings クラスを提供し、J-Quants / kabu API / Slack / DB /監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL）のプロパティを安全に取得・検証。
  - AI ニュース NLP / レジーム判定
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode でセンチメントを取得。
      - チャンク処理（1回最大 20 銘柄）、1銘柄あたりの最大記事数・文字数でトリム、レスポンスの厳密なバリデーション、スコアを ±1 にクリップ。
      - API 失敗（429 / ネットワーク / タイムアウト / 5xx）に対して指数バックオフでリトライ。失敗時はフェイルセーフでスキップし継続。
      - DuckDB への書き込みは部分失敗時に既存データを保護するため、対象コードのみ DELETE → INSERT（BEGIN/COMMIT）で実施。DuckDB 0.10 の executemany 空リスト制約に配慮。
      - calc_news_window により JST ベースのニュース収集ウィンドウを厳密に計算（ルックアヘッドバイアス防止）。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
      - マクロ記事抽出はキーワードフィルタを使用、LLM 呼び出しは独立実装でリトライ／フェイルセーフを備える。
      - 計算結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。
  - データプラットフォーム（ETL・カレンダー・品質）
    - src/kabusys/data/calendar_management.py
      - market_calendar を用いた営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した設計。
      - calendar_update_job により J-Quants から差分取得して market_calendar を冪等的に更新。バックフィル・健全性チェックを実装。
    - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
      - ETLResult データクラスの実装と公開（ETL 実行結果の集約、品質チェック結果・エラーの保持）。
      - 差分更新・backfill・品質チェックに関する設計方針を実装（詳細はモジュール内 docstring）。
  - リサーチ機能（ファクター計算・特徴量解析）
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高変化率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算。
      - データ不足や条件不成立時は None を返す安全設計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ランク変換ユーティリティ、ファクター統計サマリーを実装。
      - 外部ライブラリに依存せず標準ライブラリのみで実装。ルックアヘッドバイアス回避に配慮。
  - その他ユーティリティ
    - src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py, src/kabusys/data/__init__.py 等で API を整理して再エクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは関数引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に失敗するようにして誤設定を早期検出。

Notes / 設計上の重要点
- ルックアヘッドバイアス対策
  - AI モジュール（news_nlp, regime_detector）およびリサーチ関数では date.today()/datetime.today() を内部で使用せず、必ず呼び出し元から target_date を受け取る設計になっています。
- DuckDB 互換性考慮
  - executemany に空リストを与えない、リスト型バインドの不安定さ回避など DuckDB の制約に配慮した実装。
- フェイルセーフ
  - 外部 API の一時エラーやレスポンス不備に対しては、例外を上位へそのまま投げずにログとフォールバック値（例: macro_sentiment=0.0）で継続するケースがあるため、運用時にはログ監視を推奨します。

Acknowledgements / Exported API
- settings = kabusys.config.Settings() を介して設定へアクセス可能（例: from kabusys.config import settings）。
- 主要な公開関数：
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.calendar_management.{is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job}
  - kabusys.data.ETLResult

今後の予定（例）
- テストカバレッジの拡充（外部 API のモック含む）
- OpenAI モデル切替やプロンプト改善のための設定化
- ETL パイプラインのスケジューリング / メトリクス統合

--- End of CHANGELOG ---
CHANGELOG
=========

すべての重要な変更を一貫した形式で記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はセマンティックバージョニングに従います。
- 日付はリリース日の YYYY-MM-DD。

[Unreleased]
-------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初期公開。
  - パッケージ名: kabusys, バージョン: 0.1.0
  - パッケージトップ: src/kabusys/__init__.py にて __version__ を定義、主要サブパッケージを __all__ で公開 (data, strategy, execution, monitoring)。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート検出は .git または pyproject.toml を起点に探索（配布後の実行環境でも動作）。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応。
    - OS 環境変数を保護するため protected キーセットを使用し、override の挙動を制御。
  - Settings クラスでアプリケーション設定をプロパティとして提供 (例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN, DUCKDB_PATH 等)。
  - env / log_level / paper_fill_mode 等の入力バリデーションを実装。
  - パス設定は expanduser を用いて ~ に対応。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント (ai_score) を計算。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に計算する util を提供 (calc_news_window)。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事数・文字数トリム、JSON Mode の厳密なレスポンスバリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / サーバ 5xx に対する指数バックオフとリトライを実装。
    - レスポンスパース失敗や API エラー時はフェイルセーフでスキップ（例外を波及させず継続）。
    - テスト容易性のため、API 呼び出しを差し替え可能（unittest.mock.patch で _call_openai_api をモック可）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次で市場レジーム (bull / neutral / bear) を判定。
    - マクロキーワードによる記事フィルタ、OpenAI API 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment を 0.0 にフォールバックして継続。
    - 同様に _call_openai_api は独立実装でテスト時に差し替え可能。

- データプラットフォーム / ETL (src/kabusys/data)
  - ETL 用データクラス ETLResult を公開 (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)。
    - ETL の結果（取得件数、保存件数、品質問題、エラー等）を一元管理する dataclass を提供。
  - ETL パイプライン基礎 (src/kabusys/data/pipeline.py)
    - 差分取得、バックフィル、品質チェックを行う設計方針を実装（J-Quants クライアント呼び出し箇所を想定）。
    - デフォルトのバックフィルやカレンダー先読み等の定数を定義。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを用いた営業日判定ロジックを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - DB にデータがない場合は曜日ベースのフォールバック（週末を休日扱い）。
      - calendar_update_job により J-Quants から差分取得→冪等保存（ON CONFLICT 相当）を行う処理を実装。
      - バックフィルや健全性チェック（未来日付の異常検知）を実装。

- リサーチツール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、出来高指標）、Value（PER, ROE）等の計算関数を実装。
    - DuckDB 上の SQL とウィンドウ関数を駆使して高速に集計。データ不足時の None ハンドリングあり。
  - 特徴量探索と統計 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（任意ホライズン）、IC 計算（Spearman）、ランク化ユーティリティ、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - 研究向けユーティリティの公開（zscore_normalize 再エクスポート等）。

- テストしやすさ・安全性設計
  - OpenAI 呼び出しをモック可能にしてユニットテストを容易に。
  - DB 書き込みは冪等操作（BEGIN/DELETE/INSERT/COMMIT 等）を採用して部分失敗が既存データを壊さないよう配慮。
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接利用せず、ターゲット日を明示的に渡す設計。

Security
- .env の自動ロードは OS 環境変数を保護（既存 OS 環境変数は上書きされない）し、override 挙動や protected キーセットで上書き制御を行う。
- OpenAI API キーは関数引数か環境変数 OPENAI_API_KEY から取得。未設定時は AI 関連関数は ValueError を送出して明示的に扱う。

Known issues / Notes
- DuckDB バインド/ executemany の挙動に合わせた defensive コード（空リストを渡さない等）を採用。
- OpenAI レスポンスは JSON Mode を使う想定だが、余剰テキスト混入ケースに対しても復元処理を追加。
- paper trading の挙動制御（PAPER_FILL_MODE）や paper 用 SQLite パス等は環境変数で設定可能（デフォルト値あり）。
- 一部の関数は J-Quants クライアント（kabusys.data.jquants_client）や外部 API を前提としており、実行時にそれら実装が必要。

Acknowledgements
- 初期実装。今後、機能追加・改善 (ログ周り、エラーハンドリングの更なる強化、型アノテーション拡張、CI テスト整備 等) を予定。

-----
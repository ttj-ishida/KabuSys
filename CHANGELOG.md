# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベースから推測できる変更点・機能を日本語で記載しています。

全般的な注意
- 本リリースでは DuckDB を主要データストアとして利用する設計で、各モジュールは DuckDB 接続を引数に受け取って処理します。
- OpenAI（gpt-4o-mini）を用いた JSON Mode 呼び出しを使った NLP 処理を含みます。API 呼び出しは堅牢化（リトライ・バックオフ・フェイルセーフ）されています。
- ルックアヘッドバイアスを避ける設計方針（datetime.today()/date.today() を直接参照しない、クエリで date < target_date を使う等）が各所に反映されています。

Unreleased
- （なし）

[0.1.0] - 2026-03-28
Added
- 基本パッケージ初期実装
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - パッケージ公開 API 想定: data, strategy, execution, monitoring を __all__ に設定

- 環境設定管理 (src/kabusys/config.py)
  - .env（.env.local も含む）自動読み込み機能（プロジェクトルートは .git または pyproject.toml で検出）
  - .env ファイルのパーサ実装（コメント行、export プレフィックス、シングル／ダブルクォート、エスケープ対応）
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート
  - 設定取得ラッパー Settings クラス：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須化（_require）
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH にデフォルト値
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証ロジック
    - is_live / is_paper / is_dev のヘルパー

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news + news_symbols を集約して銘柄ごとのテキストを OpenAI に送り、銘柄別 ai_score を ai_scores テーブルへ書き込む処理を実装
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、UTC 変換）を提供（calc_news_window）
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたりの記事数／文字数上限のトリミングを実装
    - レスポンスの厳密なバリデーションと ±1.0 でのクリップ
    - リトライ（RateLimit/接続断/タイムアウト/5xx）・指数バックオフ
    - DuckDB 互換性配慮（executemany に空リストを渡さない等）
  - レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定
    - マクロキーワードで raw_news をフィルタして LLM に渡すロジック
    - OpenAI 呼び出しの独立実装（news_nlp と内部関数を共有しない）
    - API エラー時は macro_sentiment = 0.0 とするフェイルセーフ
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
  - AI ヘルパーとして score_news を ai パッケージ内で公開（src/kabusys/ai/__init__.py）

- データ関連 (src/kabusys/data)
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - ETLResult データクラス（ETL の取得数・保存数・品質問題・エラーの集約）
    - 差分取得・バックフィル、品質チェック呼び出し等の設計に基づくユーティリティ
    - DuckDB 上での最大日付取得やテーブル存在チェック等のヘルパー
  - calendar_management (src/kabusys/data/calendar_management.py)
    - JPX マーケットカレンダーの夜間バッチ更新ロジック（calendar_update_job）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定 API
    - market_calendar 未取得時の曜日ベースフォールバック、DB 優先の一貫した挙動
    - lookahead / backfill / 健全性チェック（未来日付の異常検出）を備えた実装
  - ETL の公開インターフェース再エクスポート (src/kabusys/data/etl.py)

- Research（研究）モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）等の計算関数を実装
    - DuckDB SQL を用いた高効率実装、データ不足時の None 戻し
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（任意 horizon、デフォルト [1,5,21]）
    - IC（Information Coefficient, Spearman の ρ）計算、ランク変換ユーティリティ
    - factor_summary による基本統計量算出
  - re-export と __all__ の整備（研究用ユーティリティの公開）

Changed
- 設計方針の明確化（ドキュメンテーション的追加）
  - ルックアヘッドバイアス回避のため日付扱いの方針を各モジュールの docstring に明記
  - DuckDB のバージョン差異（executemany の空引数制約等）に対する実装上の配慮を反映

Fixed
- API 呼び出しの堅牢化（AI モジュール群）
  - OpenAI 呼び出し時の各種エラーに対して適切にリトライ／フォールバックするように実装
  - JSON モードで返るレスポンスの前後余分テキスト抽出・パース耐性を実装（news_nlp の _validate_and_extract）

Notes / Limitations
- OpenAI API キーは引数で注入可能だが、デフォルトは環境変数 OPENAI_API_KEY を参照する。
- 現在の ai_score／sentiment_score は同値として扱われる（将来的な差分処理は未実装）。
- 一部テーブル（prices_daily, raw_news, raw_financials, market_calendar, ai_scores, market_regime, news_symbols 等）のスキーマを前提としている。初期 DB 構造の準備が必要。
- strategy / execution / monitoring の具象実装はこのコードベースでは公開 API 想定のみ（実装が含まれていないか別ファイルに存在する想定）。

Security
- 機密情報（API トークン等）は環境変数管理を推奨。.env 自動ロード時に OS 環境変数を保護する機構（protected set）を実装。

今後の予定（推測）
- strategy / execution / monitoring の具体実装追加（注文発注ロジック・監視アラート等）
- テストカバレッジ強化（AI 呼び出しのモック、DuckDB の統合テスト）
- パフォーマンス改善（ETL の並列化、DuckDB クエリ最適化）

---
（注）本 CHANGELOG は提示されたソースコードから推測して作成しています。実際の変更履歴やコミットメッセージはリポジトリの VCS 履歴に基づくものを参照してください。
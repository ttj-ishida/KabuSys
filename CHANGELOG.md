CHANGELOG
=========

このCHANGELOGは Keep a Changelog の慣例に従い、kabusys パッケージの主要な変更点・追加機能を日本語でまとめたものです。

※ バージョン番号は src/kabusys/__init__.py の __version__ に基づきます。

Unreleased
----------
- 次期リリースに向けた変更は現在ありません。

[0.1.0] - 2026-04-03
-------------------

Added
- パッケージ初期リリース: KabuSys - 日本株自動売買・リサーチ基盤のコア機能群を追加。
  - 基本情報
    - バージョン: 0.1.0
    - パッケージ説明: 日本株自動売買システムの基盤モジュール群を提供。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定は .git / pyproject.toml を探索）。
  - .env パーサーは以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント扱いの判定（クォート外かつ直前が空白の場合）
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で使用）。
  - OS 環境変数を保護する仕組み（.env ファイル上書き時に保護されたキーを除外）。
  - Settings クラスを提供し、主要な環境変数をプロパティ経由で安全に取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID/KILL ファイルパス、kill フラグ動作設定
    - CPU/MEM/DISK の閾値（監視用）
    - KABUSYS_ENV / LOG_LEVEL の検証ロジックと is_live/is_paper/is_dev ヘルパー

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI (gpt-4o-mini) に送信しセンチメントを算出。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事数・文字数上限（トリム）を実装。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフ処理。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造検査、未知コードスキップ、スコア数値化・クリップ）。
    - ai_scores テーブルへの冪等的な置換（対象コードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出しポイントに差し替え（patch）可能な内部関数を設置。
    - 公開 API: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジームを判定（bull/neutral/bear）。
    - prices_daily / raw_news / market_regime を用いた計算と DuckDB への冪等書き込みを実装。
    - マクロニュース抽出（キーワードベース、最大 20 件）と LLM 呼び出し（gpt-4o-mini）で macro_sentiment を評価。
    - API エラーやパース失敗時は macro_sentiment=0.0 のフェイルセーフ挙動を採用。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを利用した営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値優先、未登録日のフォールバックは曜日ベース（週末判定）。
    - next/prev の探索には最大探索範囲（_MAX_SEARCH_DAYS）を設定し無限ループを防止。
    - night-batch 用 calendar_update_job を実装（J-Quants から差分取得 → 保存、バックフィル、健全性チェック）。

  - ETL パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - 差分更新・保存・品質チェックを想定した ETLResult データクラスを実装。
    - ETL の設計方針（差分更新・backfill・品質チェック継続方針等）をコード上に明記。
    - jquants_client / quality モジュールとの連携を想定した構成。
    - etl 入口の型安全な戻り値（to_dict でログ出力用整形）を実装。

  - jquants_client など外部クライアント想定のプレースホルダ利用（DataPlatform 連携を想定）。

- リサーチ・ファクター群 (src/kabusys/research)
  - factor_research.py:
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE） を DuckDB クエリで計算。
    - データ不足時の None 扱い、結果は (date, code) ベースの dict リストで返却。
  - feature_exploration.py:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman rank）計算、ランク変換、ファクター統計サマリーを実装。
    - pandas 等に依存しない純標準ライブラリ実装。
  - re-export: zscore_normalize を含むユーティリティの公開。

- 共通実装・設計上の配慮
  - DuckDB をデータストアとして前提（すべての分析/ETL ロジックは DuckDB 接続を受け取る）。
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - DB 書き込みは冪等化（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK）を重視。
  - OpenAI 呼び出し部分は外部依存（OpenAI SDK）だが、テストで差し替えやすい設計とした。
  - ロギングを多用し、失敗時は WARN/INFO を出しつつフェイルセーフで継続する方針。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- .env ロード時に OS 環境変数を保護（.env が OS 環境を上書きしないよう保護セットを導入）。
- API キーの取得ロジックは明示的に api_key 引数または OPENAI_API_KEY 環境変数を検査。未設定時は ValueError を投げて早期検出。

Deprecated
- 該当なし。

Removed
- 該当なし。

Migration notes
- 0.1.0 は初回公開版のため、既存ユーザからの移行は不要。
- 環境変数や DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）が想定されているため、初回導入時は README や DataPlatform.md に従いスキーマ準備・.env 設定を行ってください。

参考（実装上の重要なデフォルト）
- OpenAI モデル: gpt-4o-mini（news_nlp / regime_detector 共通）
- news_nlp バッチサイズ: 20 銘柄/リクエスト
- news 時間ウィンドウ（JST）: 前日 15:00 ～ 当日 08:30（UTC 変換で前日 06:00 ～ 23:30）
- マクロキーワード一覧は regime_detector にハードコーディング
- データベース既定パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

今後の予定（例）
- AI モデルやバッチ設定の外部化・チューニング
- テストカバレッジの拡充（特に OpenAI 呼び出しのモック化）
- J-Quants クライアントの実装・接続例の追加
- モニタリング/実行モジュールの拡張（既に __all__ に "execution", "monitoring" が用意されています）

---

この CHANGELOG はソース内のドキュメント文字列・実装から推測して作成しています。実際の変更履歴やリリースノートと差分がある場合は、プロジェクトの公式リリースノートに合わせて調整してください。
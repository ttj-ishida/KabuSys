# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従っています。  

<!-- リリース履歴は古い順ではなく新しい順に記載します -->

## [0.1.0] - 2026-03-31

初回公開リリース — KabuSys 日本株自動売買システムの基盤的機能を実装しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを公開。バージョンは `0.1.0`。
  - パッケージ公開シンボルに data, strategy, execution, monitoring を含める。

- 設定管理 (kabusys.config)
  - 環境変数 / .env ファイルの自動ロード機能を実装。
    - プロジェクトルート検出は `__file__` を起点に親ディレクトリから `.git` または `pyproject.toml` を探索。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能（テスト用）。
    - `.env` パーサは export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメント等に対応。
    - 既存 OS 環境変数を保護するための protected キー処理をサポート（.env の上書きを制御）。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能:
    - J-Quants / kabu ステーション / Slack / データベースパス等の設定（必須キーは未設定時に ValueError を送出）。
    - 環境 (`KABUSYS_ENV`) とログレベル (`LOG_LEVEL`) の値検証を実装。
    - SQLite / DuckDB のパスを Path 型で取得。

- ニュース NLP（AI）機能 (kabusys.ai.news_nlp)
  - raw_news / news_symbols を元に銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して `ai_scores` テーブルへ書き込み。
  - 主な特徴:
    - JST ベースの時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と UTC 換算用ユーティリティ `calc_news_window`。
    - 1銘柄あたり最大記事数・最大文字数でトリムしてトークン肥大化を抑制（チャンク化）。
    - 1回の API 呼び出しで最大 20 銘柄バッチ処理（`_BATCH_SIZE`）。
    - 429/ネットワークエラー/タイムアウト/5xx に対する指数バックオフによるリトライ実装。
    - OpenAI JSON mode のレスポンスを堅牢にパース・バリデーション。余分な前後テキストが混ざる場合でも `{}` を抽出して復元を試みる。
    - スコアは ±1.0 にクリップ。サーバーエラー等で取得できない場合はフェイルセーフでスキップ。
    - DuckDB の executemany の制約を考慮した idempotent な DELETE→INSERT 処理（部分失敗時に既存スコアを保護）。
  - 公開 API: `score_news(conn, target_date, api_key=None)` を提供。戻り値は書き込んだ銘柄数。

- 市場レジーム判定（AI + 指標合成）(kabusys.ai.regime_detector)
  - 日次で市場レジーム（bull / neutral / bear）を判定し `market_regime` テーブルに冪等書き込みする機能を実装。
  - 主な処理:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ系ニュースの LLM センチメント（重み 30%）を合成してレジームスコアを算出。
    - DuckDB から過去データを取得する際にルックアヘッドを防ぐため target_date 未満のデータのみ参照。
    - LLM 呼び出しは OpenAI SDK を使用。API エラー時は macro_sentiment=0.0 のフォールバックを採用（例外を投げず継続）。
    - 冪等な DB 書き込み（BEGIN / DELETE WHERE date=? / INSERT / COMMIT）。失敗時は ROLLBACK を行い例外を上位へ伝播。
  - 公開 API: `score_regime(conn, target_date, api_key=None)` を提供。戻り値は成功時に 1。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時は None を返す設計。
    - ボラティリティ/流動性 (calc_volatility): 20 日 ATR、ATR 相対比、20 日平均売買代金、出来高比を計算。
    - バリュー (calc_value): raw_financials から直近の財務情報を取得して PER / ROE を算出（EPS が 0 または欠損時は None）。
    - いずれも DuckDB + SQL で実装し、本番取引 API へアクセスしない設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns)：指定ホライズン（営業日）後のリターンを計算。入力検証あり。
    - IC 計算 (calc_ic)：スピアマンのランク相関（Information Coefficient）を実装。データ不足時は None。
    - ランク変換ユーティリティ (rank)：同順位は平均ランクを返す。
    - 統計サマリー (factor_summary)：count/mean/std/min/max/median を計算。
  - research パッケージ __init__ で主要関数を再エクスポート。

- データ管理 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー（market_calendar）を基にした営業日判定ユーティリティ群を提供:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - DB にカレンダーがない場合は曜日（土日）ベースでフォールバック。
    - next/prev/get のロジックは DB 登録日を優先し未登録日は曜日フォールバックするため、DB がまばらでも一貫した判定を実現。
    - 夜間バッチ `calendar_update_job(conn, lookahead_days=...)` を実装。J-Quants クライアント経由で差分取得→保存（バックフィル・健全性チェック含む）。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを提供（取得件数・保存件数・品質検査結果・エラー等を保持）。
    - ETL 用の内部ユーティリティ（テーブル存在確認、最大日付取得、マーケットカレンダー補正等）を実装。
    - ETLResult を etl モジュールで再エクスポート。

- テスト性/運用上の考慮
  - OpenAI 呼び出しは各モジュールで `_call_openai_api` として抽象化しており、単体テストで unittest.mock.patch により差し替え可能。
  - 多くの箇所で「ルックアヘッドバイアス防止」の設計が明示されている（datetime.today()/date.today() を内部で参照しない等）。
  - API エラー時に例外を投げずフォールバックして継続するパターンを採用（フェイルセーフ設計）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注記:
- このリリースはコードベースの最初の公開状態を基に推測して作成しています。実際の変更履歴やコミットメッセージが存在する場合は、それらを元に詳細化することを推奨します。
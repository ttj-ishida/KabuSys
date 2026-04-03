# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-03

初回リリース。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys。バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - 公開サブパッケージ: data, research, ai, などのモジュール群をエクスポート。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（デフォルトで有効）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export KEY=val 形式・クォート処理・インラインコメント処理に対応。
  - Settings クラスを提供し、アプリ設定をプロパティとして取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）、LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 監視用ファイルパス: PID_FILE_PATH、KILL_FLAG_PATH、KILL_FLAG_CLEAR_ON_START
    - リソース閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（デフォルト値あり）
    - 環境設定検証: KABUSYS_ENV（development|paper_trading|live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証。
  - 環境変数未設定時は明示的な ValueError を投げるヘルパーを実装（必須キー用）。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメント (news_nlp.score_news)
    - raw_news と news_symbols を用い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）の JSON Mode へバッチ送信しセンチメントスコアを取得。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC で前日 06:00 ～ 23:30）を計算する util を提供（calc_news_window）。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・3000 文字までトリム。
    - 再試行/バックオフ: 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON パース、"results" の構造検証、未知コードの無視、スコアの数値化と ±1.0 クリップ。
    - DB 書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT（冪等性と既存データ保護を考慮）。
    - API キーは引数で注入可能（テスト容易化）。未指定時は OPENAI_API_KEY 環境変数を参照。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ書き込み。
    - MA 計算では target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止。
    - マクロニュース抽出は定義済みキーワード群でタイトルをフィルタ。
    - OpenAI 呼び出しは堅牢にリトライを行い、失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の構成で冪等性を確保。例外時は ROLLBACK を試行。

- リサーチ（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の eps/roe を取得して PER・ROE を算出（EPS が 0/欠損時は None）。
    - 実装は DuckDB SQL＋最小限の Python ロジックで実行（外部 API 呼び出しなし）。
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: ファクター値と将来リターンのスピアマン（ランク相関）による IC を計算（有効レコード不足時は None）。
    - rank, factor_summary: ランキング変換（同順位は平均ランク）、列ごとの基本統計量（count/mean/std/min/max/median）を算出。
    - pandas 等に依存しない純標準ライブラリ実装。

- データ系（src/kabusys/data）
  - カレンダー管理（calendar_management.py）
    - market_calendar を利用した営業日判定ロジック:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末を非営業日）で一貫性ある判定を提供。
    - カレンダー夜間更新ジョブ (calendar_update_job): J-Quants クライアント経由で差分取得・保存（バックフィルや健全性チェック実装）。
    - 最大探索日数制限で無限ループ防止。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題・エラー一覧を保持）。
    - 差分取得、保存（jquants_client 経由の idempotent 保存）、品質チェックを想定した設計。
    - デフォルトのバックフィル日数・カレンダー先読み等の定数を定義。

- 依存する DB テーブル（想定）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar などを使用する SQL を実装。

### 変更
- （該当なし）初回リリースのため、後方互換性を壊す変更はありません。

### 修正
- （該当なし）初回リリース。

### セキュリティ
- 環境変数の取扱い: .env 読み込み時に既存 OS 環境変数を保護する仕組み（protected set）を導入。自動読み込みを明示的に無効化可能。

### 設計上の重要な注意点 / 行動方針（ドキュメント的追記）
- ルックアヘッドバイアス防止: 主要な AI/指標計算関数は datetime.today()/date.today() を直接参照せず、必ず target_date を受け取る設計。
- フェイルセーフ: 外部 API（OpenAI, J-Quants 等）失敗時は例外を即投げず、可能な限りフェールセーフ（0 やスキップ）で継続し、ログに警告を出力する方針。
- 冪等性: DB への書き込みは削除→挿入、あるいは ON CONFLICT を想定した冪等処理で、部分失敗時のデータ消失を抑制。
- テスト容易性: OpenAI 等の呼び出しポイントは内部で置換可能（テスト時にモックで差し替えられる設計）。

### 既知の制限 / 今後の TODO（抜粋）
- news_nlp と regime_detector は OpenAI の gpt-4o-mini を想定。将来的なモデル切替や API 仕様変更への対応が必要になる可能性あり。
- 一部 SQL バインドの DuckDB バージョン依存対策を実装しているが、動作確認は利用する DuckDB バージョンで行うこと。
- PBR・配当利回りなどのバリューファクターは未実装（calc_value に注記あり）。

---

この CHANGELOG はコードベースの現状（初回公開）から推測して作成しています。実際のリリースノートには運用上の注意点や外部依存のバージョン等を適宜追記してください。
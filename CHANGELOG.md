# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- Unreleased：開発中の変更（ここでは空）
- 各リリースはバージョン・日付・カテゴリ別（Added / Changed / Fixed / Removed / Security）で記載

※この CHANGELOG はコードベースの内容から推測して作成しています。

## Unreleased

（なし）

---

## 0.1.0 - 2026-03-31

### Added
- パッケージの初期リリース (kabusys v0.1.0)
  - パッケージのメタ情報を公開（src/kabusys/__init__.py に __version__ = "0.1.0"、主要サブパッケージを __all__ で宣言）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート判定は .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env パーサーは以下をサポート：
    - コメント・空行スキップ、`export KEY=val` 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープの処理
    - クォートなしでのインラインコメント認識（直前が空白またはタブの場合のみ）
  - .env 読み込み優先順位：OS 環境 > .env.local > .env。既存 OS 環境は protected として上書き回避。
  - 自動ロード無効化フラグ：`KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - Settings クラスでアプリケーション設定をプロパティとして公開（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、DUCKDB_PATH、KABUSYS_ENV、LOG_LEVEL 等）。
  - 設定値のバリデーション（KABUSYS_ENV と LOG_LEVEL の許容値チェック、必須キー未設定時は ValueError を送出）。

- AI（ニュース NLP / レジーム判定）（src/kabusys/ai）
  - ニュースセンチメント解析（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元にタイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）内の記事を銘柄別に集約。
    - 1 銘柄あたり最大記事数・最大文字数でトリム（デフォルト: 最大10記事、3000文字）。
    - 最大 20 銘柄 / チャンクで OpenAI（gpt-4o-mini、JSON mode）に送信して一括評価。
    - レート制限 (429)、ネットワーク断、タイムアウト、5xx サーバエラーに対し指数バックオフでリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、"results" 配列、code の正規化、score の数値・有限性チェック）、スコアは ±1.0 にクリップ。
    - 処理完了後、ai_scores テーブルへ冪等的に置換（対象コードのみ DELETE → INSERT。DuckDB executemany の空配列制約に配慮）。
    - API キー未設定時は ValueError を送出。API 呼び出し失敗時は部分的にスキップし続行（フェイルセーフ）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（'bull' / 'neutral' / 'bear'）を判定。
    - マクロキーワードで raw_news をフィルタ（最大 20 件）。記事が無ければ LLM 呼び出しをスキップし macro_sentiment=0.0 とする。
    - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を使用、429/ネットワーク/タイムアウト/5xx はリトライ（最大 3 回）し、それ以外の失敗やパース失敗は 0.0 にフォールバックして継続。
    - レジームスコア合成ロジックと閾値（bull/bear）を定義し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - API キー未設定時は ValueError を送出。

- 研究（Research）モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比）、Value（PER、ROE）を計算する関数を実装（calc_momentum、calc_volatility、calc_value）。
    - DuckDB 上の SQL ウィンドウ関数を多用し、価格・財務データのみを参照。データ不足時は None を返す仕様。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、デフォルト horizons=[1,5,21]、horizons の妥当性チェック）。
    - IC（Information Coefficient）計算（calc_ic、Spearman ランク相関を実装）。
    - ランク変換ユーティリティ（rank）およびファクター統計サマリー（factor_summary）。
  - データ正規化ユーティリティを再エクスポート（zscore_normalize を kabusys.data.stats から import）。

- データプラットフォーム / ETL（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定・探索ユーティリティを提供（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）。
    - DB データがある場合は DB 値を優先、未登録日は曜日ベースのフォールバック（土日を非営業日扱い）。最大探索範囲で無限ループ回避。
    - 夜間バッチ更新ジョブ（calendar_update_job）: J-Quants API から差分取得 → 保存（jq.fetch_market_calendar / jq.save_market_calendar）し、バックフィルや健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラーの集約）。
    - 差分更新・バックフィル日数のデフォルトや品質チェック方針を実装。DuckDB テーブル確認ユーティリティ等を提供。
  - ETLResult を公開（src/kabusys/data/etl.py で再エクスポート）。

### Changed
- （初回リリースのため特記する変更はなし）

### Fixed
- （初回リリースのため特記する修正はなし）

### Removed
- （初回リリースのため該当なし）

### Security
- （該当なし）

---

Notes / 補足
- DuckDB を主要なローカル分析 DB として前提（関数群は DuckDB 接続を直接受け取る）。
- ルックアヘッドバイアス防止の設計方針に一貫性あり：
  - 各処理は内部で datetime.today() / date.today() を参照せず、必ず caller から target_date を受ける。
  - DB クエリは target_date 未満／以前の条件でデータ参照を制限。
- OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を利用する想定。テスト容易性のため _call_openai_api 関数をモジュール内で分離しており、unit test でパッチ可能。
- フェイルセーフ設計：
  - LLM API の失敗やパースエラー時はゼロスコア（中立）にフォールバックする箇所がある（news_nlp/_score_macro 等）。
  - ETL や DB 書き込みは冪等保存やトランザクション扱い（BEGIN/COMMIT/ROLLBACK）で安全性を確保。
- J-Quants / kabu ステーション / Slack 等の外部サービス設定は環境変数で管理（必須項目は Settings で require）。  

もし特定の変更点をより詳細に記載したい、あるいは将来のバージョン向けのセクション（Unreleased）に作業予定を記載したい場合は、要望を教えてください。
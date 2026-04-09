# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-09

### 追加
- パッケージ初回公開: kabusys（日本株自動売買システム）を導入。
  - パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml に基づく）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサを実装（export 形式対応、クォートとエスケープ処理、行内コメント処理）。
  - 環境変数取得ユーティリティ Settings を提供（J-Quants / kabu API / LINE / DB パス / Paper Trading 等の設定プロパティ）。
  - 設定値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック）。
  - PID ファイル/キルフラグパス、資源閾値（CPU/メモリ/ディスク）など監視向け設定を追加。

- AI 関連
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用（calc_news_window を提供）。
    - チャンク処理: 最大 20 銘柄バッチ、1 銘柄当たり最大記事数・文字数でトリム。
    - JSON Mode を用いた出力検証と堅牢なレスポンスパース（前後ノイズからの復元処理含む）。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装し、失敗はフェイルセーフでスキップ。
    - DuckDB への書き込みは冪等（取得済みコードのみ DELETE → INSERT）で部分失敗から既存データを保護。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出は news_nlp.calc_news_window と raw_news テーブルから実施（キーワードでフィルタ）。
    - OpenAI 呼び出しは専用実装（news_nlp の内部関数と共有しない設計）。
    - API リトライとフェイルセーフ: API 失敗時は macro_sentiment=0.0 にフォールバック。
    - レジームスコアの合成とクリッピング、閾値判定（_BULL_THRESHOLD/_BEAR_THRESHOLD）を実装。
    - 結果は market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX 市場カレンダー（market_calendar）の夜間差分更新ジョブ calendar_update_job を実装（J-Quants から差分取得し保存）。
    - 営業日判定ユーティリティを実装:
      - is_trading_day(conn, d), is_sq_day(conn, d)
      - next_trading_day(conn, d), prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
    - カレンダー未取得時は曜日ベースのフォールバック（土日を非営業日扱い）を採用して一貫性を確保。
    - バックフィル、先読み、健全性チェック（将来日付の異常検出）などを実装。

  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETL の公開インターフェースとして ETLResult を導入（保存件数、品質チェック結果、エラー一覧を含む）。
    - ETLResult は has_errors / has_quality_errors プロパティと to_dict メソッドを提供し、監査ログや上位処理の判定に利用可能。
    - 差分取得・バックフィル方針、保存は冪等（ON CONFLICT）での実装方針を想定（jquants_client / quality モジュールとの連携を前提）。

- リサーチ（kabusys.research）
  - ファクター計算・探索ツールを提供:
    - factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
      - Momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None を返す）
      - Volatility/Liquidity: 20日 ATR、相対 ATR、平均売買代金、出来高比率
      - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials の最新レコードを使用）
    - feature_exploration: calc_forward_returns（デフォルト horizons=[1,5,21]）、calc_ic（Spearman ランク相関）、factor_summary、rank（同順位は平均ランク）
    - research パッケージ初期エクスポートに zscore_normalize の再エクスポートを追加（kabusys.data.stats から）。

### 修正
- 各モジュールは「ルックアヘッドバイアス」を避けるため、datetime.today()/date.today() の直接参照を避ける設計を採用（target_date を明示的に受け取る）。
- DuckDB に対する互換性配慮:
  - executemany に空リストを渡さないチェックを導入（DuckDB 0.10 の制約回避）。
  - 日付型の取り扱いで安全に date オブジェクトへ変換するユーティリティを追加。

### 既知の注意点（ドキュメント的記載）
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を指定する必要がある。未指定時は ValueError を送出。
- OpenAI 呼び出し部分はテスト容易性のため内部呼び出し関数をモック可能に設計（unittest.mock.patch による差し替えを想定）。
- 一部機能は外部モジュール（jquants_client, quality, data.stats 等）との連携を前提としており、実動作にはそれらの実装が必要。

### セキュリティ
- 特に無し。

---

注: 上記はソースコードから推測して作成した変更履歴です。実際のリリースノート作成時はコミット履歴やリリース日、追加の破壊的変更や既知のバグ情報を併せて確認してください。
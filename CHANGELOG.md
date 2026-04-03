# CHANGELOG

すべての注目すべき変更を記載します。フォーマットは「Keep a Changelog」に準拠しています。

最新更新日: 2026-04-03

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化: `src/kabusys/__init__.py` にバージョン `0.1.0` と公開モジュール (`data`, `strategy`, `execution`, `monitoring`) を定義。

- 環境設定管理
  - `kabusys.config` モジュールを追加。
    - .env ファイル（`.env`, `.env.local`）および環境変数から設定をロードする自動ロード機構を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行い、CI/配布後でも動作するように設計。
    - `.env` のパースは `export KEY=val` 形式・シングル/ダブルクォート・エスケープ・コメント処理に対応。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - 必須環境変数取得用 `_require()`、および `Settings` クラスを公開（J-Quants / kabu API / LINE / DB パス / 監視設定 / ログ・環境判定等のプロパティを提供）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の値検証と便利なフラグ (`is_live`, `is_paper`, `is_dev`) を提供。

- AI（ニュース NLP / レジーム判定）
  - `kabusys.ai.news_nlp`
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出、`ai_scores` テーブルへ書き込む処理を実装。
    - JST ベースのニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算するユーティリティ `calc_news_window` を提供。
    - 銘柄ごとに記事数・文字数上限でトリムし、最大 20 銘柄ずつのバッチ送信を行うことで効率化。
    - API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフで再試行。その他エラーはフェイルセーフによりスキップして継続。
    - OpenAI レスポンス検証（JSON 抽出、results 配列、code/score 検証、数値変換、±1.0 クリップ）を実装。レスポンスが不正な場合はスキップして他の銘柄を保護。
    - 部分成功時に既存の他コードスコアを壊さない idempotent な DB 書き込み（DELETE → INSERT）を実施。
  - `kabusys.ai.regime_detector`
    - ETF 1321（日経225 連動 ETF）200 日移動平均乖離（重み 70%）とニュース（マクロセンチメント、重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定して `market_regime` テーブルへ書き込む機能を実装。
    - マクロセンチメントはニュースタイトルを抽出して OpenAI により JSON 出力で評価。記事がない場合や API 失敗時は macro_sentiment=0.0 にフォールバック。
    - LLM 呼び出しはリトライ・エクスポネンシャルバックオフ対応。レスポンスパース失敗時もフェイルセーフで継続。
    - レジームスコア合成ロジック（スコアのクリップ、閾値によりラベル付与）と冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK ログ）を実装。
    - 設計上、内部で datetime.today()/date.today() を直接参照せず、与えられた target_date を基準に処理することでルックアヘッドバイアスを回避。

- 研究（Research）モジュール
  - `kabusys.research.factor_research`
    - ファクター計算機能を実装（モメンタム / ボラティリティ / バリュー）。
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を算出。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を算出。
      - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS が 0/欠損の場合は None）。
    - DuckDB を利用した SQL ベースの実装で、prices_daily / raw_financials のみを参照（取引系 API にはアクセスしない）。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）の将来終値リターンを一括クエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン順位相関でファクター有効性を評価（有効レコード数が 3 未満の場合 None）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
    - ランキングユーティリティ（rank）: 同順位は平均ランク。浮動小数丸めによる tie を考慮。

- データプラットフォーム（Data）
  - `kabusys.data.calendar_management`
    - JPX マーケットカレンダー管理（market_calendar）の参照・判定ユーティリティを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB にカレンダーがない場合は土日ベースのフォールバックを使用。
      - next/prev は最大探索日数を設けて無限ループを防止し、DB 登録日を優先する一貫した振る舞いを実装。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants API から差分取得・バックフィル・健全性チェック・保存）。
  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL パイプラインの基盤を実装。
      - 差分更新方針、バックフィル、品質チェック連携を想定。
      - `ETLResult` データクラスを公開（target_date、取得/保存件数、quality_issues、errors、ユーティリティプロパティおよび to_dict）。
      - DuckDB を前提としたテーブル存在確認や最大日付取得などのユーティリティを実装。
    - `kabusys.data.etl` は `ETLResult` を公開再エクスポート。

- その他
  - `kabusys.research.__init__` で主要関数を再エクスポート（使いやすさ向上）。
  - OpenAI クライアント利用箇所に共通の実装方針（JSON mode, temperature=0, timeout, 返却検証）を採用。
  - API 呼び出し失敗時のフォールバック方針（LLM 失敗での 0.0 フォールバック、部分失敗時に既存データ保護）を一貫して実装。

### Design / Implementation Notes
- ルックアヘッドバイアス対策
  - AI/研究の各モジュールは内部で date.today()/datetime.today() を参照せず、必ず呼び出し側から `target_date` を受け取る設計。
  - DB クエリは常に target_date 未満 or target_date を適切に扱うことで将来情報の漏洩を防止。
- フェイルセーフ設計
  - LLM / API 呼び出しの不安定性を考慮し、致命的ではないエラーはログに記録して処理を継続する方針（ただし DB 書き込み失敗時は例外を伝播）。
- Idempotency と部分失敗への配慮
  - DB への置換操作（DELETE → INSERT）により、再実行や部分失敗時にも既存データの保護を図る。
- 依存
  - DuckDB と OpenAI Python SDK を利用する想定（対応する環境変数に API キーが必要）。
  - jquants_client 等の外部クライアントモジュールを参照（実装は別ファイル）。

### Removed
- （無し）

### Fixed
- （初回リリースにつき該当なし）

### Security
- OpenAI API キー等の機密情報は環境変数で管理する設計。`.env.local` を優先して読み込む挙動あり。自動ロードを無効化するフラグを提供。

---

注記:
- 本 CHANGELOG はリポジトリ内のソースコード内容から推測して作成した初回リリース向けの変更履歴です。実際のリリースノート作成時にはビルド手順、依存バージョン、互換性情報、既知の問題（Known issues）などを必要に応じて追記してください。
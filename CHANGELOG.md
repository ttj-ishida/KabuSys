# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
このファイルはプロジェクトのリリース履歴を日本語で要約したものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-04

初版リリース — 日本株自動売買 / データ基盤・リサーチ・AI 支援機能を提供する最初の実装。

### 追加 (Added)
- パッケージ基礎
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を導入。
  - パブリック API のエクスポート: data, strategy, execution, monitoring（将来のモジュール用の名前空間）。

- 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数からの設定読み込みを自動で行う機能を実装。
    - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に __file__ から上位ディレクトリを探索することで、CWD に依存しない自動ロードを行う。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト時に有用）。
    - .env パーサ:
      - `export KEY=val` 形式に対応。
      - シングル/ダブルクォート内のエスケープ処理を考慮。
      - 行内コメントの取り扱い（クォート外のみ、直前にスペース/タブがある `#` をコメント扱い）を実装。
    - 読み込み時の例外は警告として扱い、安全に継続。
    - 重要キーを保護するため、OS 環境変数名セットを protected として扱い上書きを防止。
  - 設定アクセス用クラス `Settings` を提供（単一インスタンス `settings`）。
    - J-Quants / kabu-station / LINE / DB パス / 監視閾値 / ログ設定等をプロパティとして取得。
    - 必須変数未設定時は `_require` が ValueError を送出（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の値チェックを実装（許容値以外は ValueError）。
    - デフォルトの DB パス: DuckDB = `data/kabusys.duckdb`, SQLite = `data/monitoring.db`。
    - 監視用デフォルトパス/閾値（PID ファイル、kill flag、CPU/Memory/Disk 閾値等）。

- AI: ニュース NLP / レジーム判定 (`kabusys.ai`)
  - news_nlp モジュール (`score_news`)
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメントを算出し、`ai_scores` テーブルへ書き込む処理を実装。
    - 処理の流れ、バッチサイズ（デフォルト 20 銘柄）、1銘柄あたりの最大記事数/文字数トリム、JSON レスポンス検証、スコアの ±1.0 クリップなどを実装。
    - リトライポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。その他のエラーはスキップして継続（フェイルセーフ）。
    - DB 書き込みは部分失敗を考慮し、取得成功したコードのみ DELETE→INSERT で置換（DuckDB の executemany の制約に配慮）。
    - target_date のニュースウィンドウ計算（JST 基準、UTC 変換）を `calc_news_window` で提供。ルックアヘッドバイアス防止のため、内部で現在時刻を参照しない設計。
    - テスト容易性: OpenAI 呼び出し `_call_openai_api` を patch 可能。
  - regime_detector モジュール (`score_regime`)
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - LLM は gpt-4o-mini を使用。マクロキーワードで raw_news タイトルを抽出してスコアリング。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）で `market_regime` テーブルへ保存。API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - OpenAI 呼び出しのリトライ・エラー処理を実装（RateLimit/接続エラー/タイムアウト/5xx の再試行、非5xxやパース失敗はフォールバック）。

- データプラットフォーム (`kabusys.data`)
  - calendar_management モジュール
    - JPX カレンダー管理ロジック（市場カレンダーの夜間差分更新、営業日判定、next/prev trading day、get_trading_days、is_sq_day）を実装。
    - DB にデータが無い場合は曜日（平日）ベースでフォールバックする一貫した動作。
    - カレンダー更新ジョブ `calendar_update_job` は J-Quants クライアントから差分取得し、バックフィルと健全性チェックを行ったうえで保存。
    - 最大探索・安全性のため各種最大日数制限を導入（例: 最大探索 60 日、バックフィル 7 日、異常先読み検知 365 日など）。
  - ETL / pipeline (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL 実行結果を表す dataclass `ETLResult` を公開（取得/保存件数、品質チェック結果、エラー一覧等を保持）。
    - 差分取得・保存・品質チェック・バックフィルの方針を実装するための基盤を整備。
    - テーブル存在確認や最大日付取得等のユーティリティを実装。
    - jquants_client と quality モジュールを想定した連携ポイントを用意。

- リサーチ (`kabusys.research`)
  - factor_research モジュール
    - モメンタム、ボラティリティ（ATR）、バリュー（PER/ROE）等のファクター計算を DuckDB クエリで実装。
    - 関数: `calc_momentum`, `calc_volatility`, `calc_value`。すべて prices_daily / raw_financials のみを参照し、実取引 API へのアクセスは行わない設計。
    - データ不足時の取り扱い（必要行数未満 → None）やスキャン範囲バッファを実装。
  - feature_exploration モジュール
    - 将来リターン計算 (`calc_forward_returns`)：指定ホライズン（例: 1,5,21 営業日）のリターン算出。horizons のバリデーションを実装。
    - IC（スピアマンのランク相関）計算 (`calc_ic`) とランク化ユーティリティ (`rank`)。
    - ファクター統計サマリー (`factor_summary`)：count/mean/std/min/max/median を計算。
    - 外部依存（pandas 等）を使わず標準ライブラリ + DuckDB で実装。

### 変更点 (Changed)
- 初版リリースのため過去リリースとの変更点はありません。

### 修正 (Fixed)
- 初版リリースのため過去リリースとの修正点はありません。

### 注意事項 / 既知の設計方針
- ルックアヘッドバイアス防止:
  - 多くのモジュール（news scoring, regime scoring, research utilities）は内部で datetime.today() / date.today() に依存せず、引数で渡された target_date を基準に処理する設計です。
- OpenAI 連携:
  - gpt-4o-mini を用いた JSON mode を想定。レスポンスのパース失敗や API 障害時はフェイルセーフ（スコアを 0.0 とするか該当銘柄をスキップ）で継続する実装です。
  - テスト容易性のため OpenAI 呼び出し部を patch できるよう設計されています。
- DB 書き込み:
  - DuckDB 特有の挙動（executemany に空リストが不可等）に配慮した実装を行っています。
  - 多くの書き込みは冪等性（DELETE→INSERT、ON CONFLICT など）を重視しています。
- 環境変数:
  - 必須変数が未設定のまま処理を実行すると ValueError を投げて失敗する箇所があります（明示的にキーを要求する箇所は例外で通知する設計）。
  - 自動 .env ロードはルート検出に成功した場合のみ実行。CI/テスト等で自動ロードを無効化可能。
- ロギング:
  - 各モジュールで情報 / 警告 / 例外ログを適切に出力するようになっています。`Settings.log_level` を用いた制御が可能。

### 将来の改善候補（メモ）
- strategy / execution / monitoring の具体実装（現状名前空間のみ）。
- より詳細な品質チェックルールや通知（LINE 連携等）の実装。
- テストカバレッジと CI の整備（OpenAI 呼び出しのモックパターン等）。
- DB スキーマ定義とマイグレーションツールの付属。

---

（注）本CHANGELOGはソースコードのコメント・実装に基づき推測して作成しています。実際のリリースノートとして公開する前に、実際の変更点・バージョンポリシーに合わせて調整してください。
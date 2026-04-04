# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います: https://semver.org/

## [Unreleased]

特になし。

## [0.1.0] - 2026-04-04

初回リリース — 「KabuSys: 日本株自動売買システム」コアライブラリ公開。

### 追加 (Added)

- パッケージ基盤
  - パッケージ名 `kabusys` を公開。バージョンは `0.1.0`。
  - 公開サブパッケージ: `data`, `strategy`, `execution`, `monitoring` を __all__ で明示。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索（CWD に依存しない）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
    - .env パースは `export KEY=val`、クォート・エスケープ、インラインコメントに対応。
    - ファイル読み込み失敗時は警告発行して継続。
  - `Settings` クラスを提供し、以下の設定プロパティを取得可能（例: `settings.jquants_refresh_token` 等）。
    - J-Quants / kabu API / LINE Messaging / DB パス（DuckDB/SQLite）/監視関連 (PID, kill flag, CPU/メモリ/ディスク閾値) / ログレベル・環境（development/paper_trading/live）など。
    - 必須項目未設定時は `ValueError` を送出するメソッド `_require` を実装。

- AI（NLP）モジュール (kabusys.ai)
  - ニュースセンチメント解析 (news_nlp.score_news)
    - raw_news / news_symbols テーブルのデータを銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してスコアリング。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - バッチサイズ、1銘柄当たりの最大記事数・文字数制限 (_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK) を導入。
    - レスポンスの堅牢なバリデーション（JSON 抜き出し処理、results フォーマット検査、未知銘柄の無視、数値チェック、±1.0 クリップ）。
    - 429/ネットワーク/タイムアウト/5xx は指数バックオフでリトライ。その他のエラーはスキップして継続（フェイルセーフ）。
    - 書き込みは部分成功を考慮し、取得済みコードのみ DELETE → INSERT で差し替え（DuckDB の executemany 空リスト制約に注意）。
    - テスト容易性のため、内部の OpenAI 呼び出し `_call_openai_api` を patch して差し替え可能。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロ記事抽出のためのキーワードリスト `_MACRO_KEYWORDS` を実装。
    - OpenAI 呼び出しは独立実装（news_nlp と private 関数を共有しない設計）。
    - API 失敗時は macro_sentiment = 0.0 として処理を継続（フェイルセーフ）。結果は `market_regime` テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 主要な閾値や重み、リトライ設定はモジュール定数で管理。

- データプラットフォーム (kabusys.data)
  - ETL/パイプライン
    - ETL 結果を表現するデータクラス `ETLResult` を公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl 経由で再エクスポート）。
    - ETL の設計：差分取得、保存（idempotent）、品質チェック（quality モジュール）を想定したパイプライン基盤。
    - ETLResult は品質問題・エラー一覧・各種取得/保存件数を保持し、辞書化メソッド `to_dict()` を持つ。
  - カレンダー管理 (calendar_management)
    - JPX カレンダーを管理する夜間バッチ `calendar_update_job` を実装（J-Quants API 経由で差分取得 → 保存）。
    - market_calendar テーブルの存在有無に応じたフォールバックロジック（未取得時は曜日ベースで土日を非営業日扱い）。
    - 営業日判定ユーティリティ:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - 最大探索日数やバックフィル、健全性チェック（未来日付の異常検出）を実装し、安全性を確保。
    - DB 登録値優先・未登録日は曜日フォールバックという一貫した挙動。
  - ジェネラルユーティリティ
    - 各種 DB テーブル存在確認や日付変換関数など、DuckDB と親和性の高いユーティリティを実装。

- リサーチ（特徴量・ファクター） (kabusys.research)
  - ファクター計算モジュール
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: PER / ROE を raw_financials と prices_daily を組み合わせて計算。
    - 各関数は DuckDB 接続を受け取り、外部 API を呼ばずに SQL + Python で計算する仕様。
    - データ不足時は None を返す設計（安全）。
  - 特徴量探索モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマン（ランク）による IC（Information Coefficient）計算を実装（結合は code ベース）。
    - rank: 同順位は平均ランクを返すランク関数（round(v, 12) による丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー実装。
  - これらは研究環境向けに、外部依存（pandas 等）を使わずに標準ライブラリ + DuckDB で実装。

### 変更 (Changed)

- 設計方針の明示化
  - 全ての分析・スコアリング処理は datetime.today() / date.today() に直接依存しない（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しに対する堅牢性（リトライ・フォールバック・ログ出力）を重点的に組み込み。
  - DB 書き込みは可能な限り冪等性を保つ（DELETE → INSERT、ON CONFLICT の想定）。
  - DuckDB の executemany における空リスト制約を考慮した実装。

### 修正 (Fixed)

- 初期版のため既知のバグ修正履歴は無し（初回リリース）。

### 注意点 / マイグレーション（開発者向け）

- OpenAI API キーは `OPENAI_API_KEY` 環境変数または関数引数で指定する必要がある。未指定時は ValueError を送出する。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後やテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化することを推奨。
- DuckDB に関する挙動（executemany の空リスト不可等）を前提にコーディングしているため、将来の DuckDB バージョンで仕様が変わる場合は注意が必要。
- AI モジュールの内部 OpenAI 呼び出しはテストで差し替え可能（unittest.mock.patch を利用）。

### セキュリティ (Security)

- 本バージョンにおける重大なセキュリティ修正は無し。API キー等の秘密情報は環境変数や .env で管理する想定。セキュリティ上のベストプラクティスに従って管理してください。

---

（備考）本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートやユーザ向けドキュメントは運用ポリシーや追加機能に応じて更新してください。
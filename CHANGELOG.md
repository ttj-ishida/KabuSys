# Changelog

すべての注記は Keep a Changelog 準拠です。  
このプロジェクトの初回公開バージョンを示します。

## [0.1.0] - 2026-04-03

### 追加 (Added)
- 初版リリース:
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境・設定管理:
  - 自動 .env 読み込みを実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env パース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視設定 等のプロパティ経由で取得可能。

- データプラットフォーム（data モジュール）:
  - calendar_management: JPX マーケットカレンダー管理、営業日判定、次/前営業日取得、期間内営業日取得、SQ日判定、夜間更新ジョブ(calendar_update_job) を実装。
    - market_calendar が未取得時の曜日ベースフォールバックをサポート。
    - DB 優先・未登録日は曜日フォールバックにより next/prev/get の一貫性を確保。
    - バックフィルや健全性チェックを実装。
  - ETL パイプライン：pipeline モジュールの公開（差分取得・保存・品質チェック方針を実装）。
  - ETLResult データクラスを公開（ETL 実行結果の構造化・辞書化ユーティリティ含む）。
  - etl モジュールで pipeline.ETLResult を再エクスポート。

- AI（自然言語処理）:
  - news_nlp.score_news:
    - raw_news + news_symbols の記事を銘柄別に集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを評価。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで処理。
    - レスポンスの厳密なバリデーションを実施し、ai_scores テーブルへ冪等的に書き込み（DELETE→INSERT）。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない設計（target_date ベース）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュース収集は news_nlp.calc_news_window を利用。
    - OpenAI 呼び出し（独自の内部呼び出し実装）を行い、API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、ROLLBACK 保護）。
    - ルックアヘッドバイアス回避設計（prices_daily で date < target_date を使用）。

- リサーチ（research モジュール）:
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対ATR(atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS=0/欠損時は None）。
    - DuckDB SQL を活用した実装。結果は (date, code) ベースの dict リストで返却。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証（正の整数かつ <=252）。
    - calc_ic: factor と forward の Spearman（ランク相関）IC 計算（無効レコード除外、最小有効数 3）。
    - rank: 同順位は平均ランクで処理（丸めにより ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算。

- 共通実装・設計上の特徴:
  - DuckDB を主要な DB として想定（関数は DuckDBPyConnection を受け取る）。
  - DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 方針の呼び出しなど）。
  - OpenAI 呼び出しに対する堅牢なエラーハンドリング（リトライ・バックオフ・非5xx の即時フォールバック）。
  - スコアは所定の範囲でクリップ（例: ±1.0）。
  - テスト容易性のため、OpenAI 呼び出しの内部関数は (unittest.mock.patch) で差し替え可能に実装。
  - 外部依存を最小化（Research の統計部分は標準ライブラリのみで実装）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能（api_key 引数）かつ環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を投げる仕組みで誤使用を防止。

### 既知の注意点 / 将来改善候補 (Notes)
- .env 読み込みはプロジェクトルート探索に依存するため、配布後や特殊な配置では自動ロードを期待通り動作させるために KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して手動で読み込む運用を推奨。
- DuckDB の executemany に空リストを渡せないバージョン対応のため、空チェックを明示的に行っている。
- news_nlp / regime_detector の OpenAI 呼び出しは JSON Mode を想定したパースロジックを含むが、将来的な API 仕様変更に伴う互換性対応が必要になる可能性がある。
- 現時点では PBR・配当利回り等のバリュー指標は未実装（calc_value の拡張余地あり）。

---

（本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして使用する場合は、必要に応じて運用上の変更点やマイグレーション手順を追記してください。）
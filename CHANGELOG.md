# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
このリポジトリの初期公開バージョンとして 0.1.0 を記録します。

なお、ここに記載した内容はソースコードから推測してまとめたものであり、実装意図やドキュメント等に基づいて調整しています。

## [0.1.0] - 2026-04-02
初期リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys/__init__.py にてバージョン (0.1.0) と主要サブパッケージ（data, strategy, execution, monitoring）の公開を追加。

- 環境変数 / 設定管理 (kabusys.config)
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml を探す）から自動読み込みする仕組みを実装。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサー実装（export 形式対応、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメント処理等を考慮）。
  - .env の読み込み時に OS 環境変数を保護するための protected set 機構を導入（.env.local は上書き可能だが OS 変数は保護）。
  - 必須設定取得用の _require() と Settings クラスを提供。主要なプロパティを定義:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等のファイルパス（Path オブジェクトで返却）
    - CPU/MEMORY/DISK の閾値設定（float）
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live, is_paper, is_dev

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini, JSON mode）でバッチ（最大20銘柄）センチメントスコアを取得。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC 換算で適切に扱う calc_news_window を実装。
    - 入力サイズ制限（1銘柄あたり最大記事数・最大文字数）やレスポンスの厳密なバリデーションを実装。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで行い、失敗時は該当チャンクをスキップして他銘柄の処理継続（フェイルセーフ）。
    - レスポンスパース/バリデーション失敗時はログ出力してスコア取得をスキップ、DB への書き込みは取得に成功したコードのみ置換（DELETE → INSERT）することで部分失敗に強い設計。
    - スコアは ±1.0 にクリップして保存。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - ma200_ratio は DuckDB から target_date 未満のデータのみを用いて算出し、データ不足時は中立（1.0）にフォールバック。
    - マクロニュースは news_nlp の calc_news_window を利用してフィルタし、OpenAI を用いて JSON レスポンスを期待してスコアリング。API 失敗時は macro_sentiment=0.0 として継続。
    - レジーム合成スコアはクリップ後に閾値でラベル決定し、market_regime テーブルへ冪等的に（BEGIN/DELETE/INSERT/COMMIT）書き込み。DB 書き込み失敗時は ROLLBACK を試行して例外を上位へ伝播。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理機能（market_calendar テーブル参照）と営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録がない場合は曜日ベース（週末除外）でフォールバック。DB 登録あり → DB 値優先、未登録日は曜日フォールバックで一貫性を保つ。
    - calendar_update_job により J-Quants から差分取得して market_calendar を更新。バックフィル（直近 _BACKFILL_DAYS）と健全性チェック（将来日付が不正に遠い場合はスキップ）を実装。
  - pipeline / ETL:
    - ETLResult データクラスを導入し、ETL の取得・保存件数、品質チェック結果、エラー一覧を structured に管理する仕組みを提供。
    - 差分更新・backfill・品質チェック（quality モジュール連携）を想定した設計。jquants_client を利用した保存処理を想定。
    - _table_exists / _get_max_date などのユーティリティ追加（DuckDB 前提）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離等を DuckDB SQL で高速取得。データ不足時は None を返却。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に扱う実装。
    - calc_value: raw_financials を参照して PER / ROE を算出。価格と財務データを組み合わせる。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを LEAD を用いて一括取得。
    - calc_ic: ファクターと将来リターンのランク相関（Spearman の ρ）を計算。データ不足時は None。
    - rank / factor_summary: 同順位は平均ランク扱い、各カラムの基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで計算。

- 小さな公開インターフェース
  - kabusys.data.etl が pipeline.ETLResult を再エクスポート。
  - kabusys.ai.__init__ で score_news のエクスポート。
  - kabusys.research.__init__ で主要な関数群をエクスポート。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- OpenAI API キーが未設定の場合は明確に ValueError を投げるようにしており、API キーの暗黙的な不在で静かに失敗することを防止。
- .env 読み込み時に OS 環境変数を上書きしない保護ロジックを採用（.env.local は明示的に上書き可能だが OS 環境は保護）。

### 注意事項 / マイグレーションノート
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。パッケージ配布後に CWD に依存せず動作する設計です。テストや特殊な実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY を環境変数に設定するか、各関数の api_key 引数で明示的に渡す必要があります。未設定時は ValueError が発生します。
- DuckDB を前提とした SQL 実装になっているため、DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）が存在することが前提です。
- news_nlp と regime_detector は API 呼び出し失敗時でもフェイルセーフ（スコア 0 やチャンクスキップ）で継続する設計ですが、部分的にスコアが欠落する場合があるため downstream での扱いに注意してください。

---

今後のリリースでは以下のような項目が想定されます:
- strategy / execution / monitoring の具体的実装とテスト
- DB スキーマ定義（マイグレーション）とサンプルデータ
- ユニットテスト・統合テストの追加（API 呼び出しをモックするヘルパー等）
- ドキュメント（設計資料・運用手順・環境変数一覧）の整備

---
# Changelog

すべての重要な変更点を Keep a Changelog の形式に従って記録します。  
このプロジェクトはセマンティックバージョニングを採用しています。  

注意: 下記はソースコードから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な機能・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージを初期化（バージョン: 0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ としてエクスポート。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読込（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサー実装: export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱いなどに対応。
  - 読み込み時の上書き制御（override）および OS 環境変数を保護する protected 機能。
  - Settings クラスでアプリ設定をプロパティとして公開（J-Quants, kabu API, Slack, DB パス, 環境フラグ、ログレベルなど）。
  - バリデーション: KABUSYS_ENV / LOG_LEVEL の許容値チェック、必須キー未設定時に ValueError。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースの NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価。
    - タイムウィンドウ計算（JST基準 → UTC naive datetime を返す calc_news_window）。
    - バッチ処理（最大 20 銘柄 / API コール）、記事数・文字数上限（1銘柄あたり最大記事数・最大文字数）でトークン肥大化を抑制。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 構造、コード整合性、スコア数値性、スコアの ±1.0 クリップ）。
    - 成功した銘柄のみ ai_scores テーブルに置換（DELETE → INSERT）することで部分失敗時の既存データ保護。
    - テスト容易性: OpenAI 呼び出し箇所をモジュール内でラップしており unittest.mock.patch にて差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull / neutral / bear）。
    - マクロキーワードによる raw_news フィルタリング、最大記事数制限。
    - OpenAI 呼び出しは JSON mode を使用し、リトライ・エラーハンドリングを実装（API エラー時は macro_sentiment=0.0 でフォールバック）。
    - DuckDB 上の market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、例外時は ROLLBACK を試行。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）の夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - 営業日判定ユーティリティ群（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバック（週末は非営業日扱い）。最大探索日数ガードあり。
    - J-Quants クライアント経由で差分取得し冪等保存（fetch/save を呼び出す想定）。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー一覧等を保持）。
    - 差分取得、バックフィル（デフォルト数日前再取得）を想定した設計。DuckDB を利用した最大日付取得ユーティリティ等を実装。
    - 品質チェックモジュール (kabusys.data.quality) と連携する設計（品質問題は収集して呼び出し元に伝搬）。

  - jquants_client との連携を想定した設計（fetch/save を呼ぶ形）。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility: 20 日 ATR（平均 true range）、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: PER（price / EPS）および ROE（raw_financials から最新レコードを取得）。
    - DuckDB のウィンドウ関数を活用した SQL ベース実装。データ不足時には None を返す。結果は (date, code) をキーとする dict リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）のリターンを LEAD で計算。
    - IC 計算（calc_ic）: ランク相関（Spearman の ρ）を実装（同順位は平均ランクで処理）。
    - rank ユーティリティ: 値をランクに変換（丸めによる ties の扱いを考慮）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算（None を除外）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー管理
  - OpenAI キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出することで誤使用を防止。

### Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策
  - 多くの処理で datetime.today()/date.today() を直接参照せず、caller が target_date を渡すことで将来情報の混入を防止する設計。
  - DB クエリは target_date 未満／未満等でルックアヘッドを避ける条件が明示的に組まれている。

- フェイルセーフ設計
  - OpenAI 呼び出しや API エラー時は例外を上位に上げずフォールバック（例: macro_sentiment=0.0）して処理を継続する箇所が存在。
  - DB 書き込みはトランザクション（BEGIN / COMMIT / ROLLBACK）で保護。

- テスト容易性
  - OpenAI への実際の API 呼び出し部分をラップしており、unittest.mock.patch による差し替えでテスト可能。

- デフォルト設定
  - DuckDB/SQLite のパス等のデフォルトを Settings で定義（例: data/kabusys.duckdb, data/monitoring.db）。
  - KABUSYS_ENV は development / paper_trading / live のいずれかを期待。

### Breaking Changes
- （初回リリースのため該当なし）

---

作成者注:
- 本 CHANGELOG はリポジトリ内のソースコードからの推測に基づいています。実際のドキュメントやリリースノートとして使用する際は、ビルド手順・外部依存・運用上の注意点（API キー発行手順、DuckDB テーブルスキーマ、jquants_client の挙動等）を加筆してください。
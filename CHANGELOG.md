# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
このファイルはコードベースから推測して作成したリリースノートです。

フォーマット: [Unreleased] とリリースごとのセクションを用意しています。

## [Unreleased]

- なし

---

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買システムのコアライブラリをまとめて提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョン（バージョン文字列: 0.1.0）。
  - サブパッケージ公開: data, research, ai, execution, monitoring（__all__ による公開制御）。

- 設定管理 (.env / 環境変数)
  - kabusys.config: プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み機能を実装。
  - .env パーサーの実装:
    - コメント / 空行無視、export KEY=val 形式対応、クォート文字列取り扱い（エスケープ対応）、非クォート時のインラインコメント処理などの堅牢なパーシング。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - Settings クラスで主要な設定をプロパティとして公開（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベルなど）。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須環境変数取得時のエラー通知（_require）。

- AI モジュール（OpenAI 連携）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントスコアを取得して ai_scores に書き込む機能（score_news）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を行う calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり最大記事数と文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - API 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）と応答の厳密なバリデーション（JSON 抽出、results 配列、code/score 検証、スコアのクリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、executemany を利用）と部分失敗時の既存データ保護。
    - テストしやすさのため _call_openai_api を patch 可能に設計。
  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（70% 重み）とニュース由来の LLM マクロセンチメント（30% 重み）を合成して市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - マクロキーワードによる raw_news フィルタ、OpenAI の利用（gpt-4o-mini、JSON 出力要求）、API リトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームスコア合成ロジック、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス対策: target_date 未満のデータのみ使用、datetime.today() 参照を回避。

- データ基盤（DuckDB ベース）
  - kabusys.data.calendar_management
    - 市場カレンダーの取得・保存と営業日判定 API を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - calendar_update_job による J-Quants からの差分取得と保存（バックフィル、健全性チェック、ON CONFLICT 相当の保存を想定）。
    - カレンダーデータ未取得時の曜日ベースのフォールバックや、DB 登録値優先の一貫した挙動を保証。
  - kabusys.data.pipeline / etl
    - ETLResult データクラスを公開（etl 実行結果、品質チェック結果、エラー集約などを保持）。
    - ETL 処理方針（差分更新、backfill、品質チェック、idempotent 保存）を実装する基礎（jquants_client との連携想定）。
  - duckdb を想定した SQL 実装が多数（prices_daily, raw_news, raw_financials, market_calendar, ai_scores 等の操作）。

- リサーチモジュール
  - kabusys.research.factor_research
    - ファクター計算: モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、流動性指標（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）等を SQL/Window 関数で計算する関数群（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の None 扱い、結果を (date, code) ベースの dict リストで返す設計。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の rank 相関）計算（calc_ic）、rank ユーティリティ、統計サマリー（factor_summary）を実装。
    - 外部依存を持たない標準ライブラリのみでの実装を意識。

### Changed
- なし（初回公開）

### Fixed
- なし（初回公開）

### Security
- 環境変数読み込み時に OS 環境変数を protected として上書き防止する実装を導入（.env の上書きから重要な OS 環境変数を保護）。
- OpenAI API キー等の必須項目は取得時に明示的エラーを投げる設計（未設定時に ValueError）。

### Notes（設計上の重要ポイント・既知の制約）
- ルックアヘッドバイアス回避: 各 AI/研究モジュールは内部で datetime.today()/date.today() を参照せず、必ず呼び出し側が target_date を渡す設計。
- OpenAI 呼び出しは JSON Mode を想定して厳密にパースするが、稀に余計な前後テキストが混ざるケースに備えて外側の {} を抽出して復元する耐性を持つ。
- API 呼び出しのリトライは 429 / ネットワーク断 / タイムアウト / 5xx を対象とし、その他のエラーは即時スキップするフェイルセーフ（サービスの継続性を重視）。
- DuckDB の executemany の挙動（空リスト不可など）を考慮した実装になっている（部分的な書込み保護、冪等性を確保）。
- テスト容易性: OpenAI 呼び出し部分はユニットテストで差し替え可能（_call_openai_api を patch）。
- 外部発注（kabu / 実行エンジン）への接続コードは本リリースでは含まれておらず、本パッケージは主にデータ処理・解析・スコアリング基盤を提供することを意図。

---

今後の予定（想定）
- モデルやプロンプト改善、より細かい品質チェックルール拡張。
- ETL の実行スケジューラ / モニタリング機能強化。
- 実注文エンジンとの安全な接続・シミュレーション機能の追加。

もしリリースノートに追記してほしい点（例えば依存関係の明記や既知のバグなど）があれば教えてください。
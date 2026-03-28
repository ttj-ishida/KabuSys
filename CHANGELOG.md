# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています（簡易化バージョン）。

※ 本 CHANGELOG はリポジトリ内のコードから機能・設計意図を推測して作成しています。実際の開発履歴と差異がある可能性があります。

## [0.1.0] - 2026-03-28 (initial release)

### Added
- パッケージ全体
  - 初期リリース。本ライブラリは「日本株自動売買システム」（KabuSys）向けのデータ収集・研究・AI支援・カレンダー管理・ETL ユーティリティ群を提供。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 環境設定/設定管理 (`kabusys.config`)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` のサポート。
  - .env パーサーは `export KEY=val` 形式、クォート文字列（シンプルなバックスラッシュエスケープ考慮）、インラインコメントの扱いなどに対応。
  - `Settings` クラスを提供。以下の主要なプロパティを持つ:
    - J-Quants / kabu API / Slack トークン等の必須項目を `_require()` で検証（未設定時は ValueError）。
    - DB パス（DuckDB / SQLite）の既定値と `Path` 正規化。
    - `KABUSYS_ENV`（development / paper_trading / live）と `LOG_LEVEL` の検証ロジック。
    - `is_live`, `is_paper`, `is_dev` のブール判定ユーティリティ。

- AI モジュール (`kabusys.ai`)
  - ニュースセンチメントスコアリング (`news_nlp.score_news`)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合、OpenAI（gpt-4o-mini）でセンチメント評価。
    - バッチ処理（最大20銘柄／チャンク）、トークン肥大対策（記事数・文字数制限）、JSON Mode を利用した出力・バリデーション。
    - API エラー（429、ネットワーク、タイムアウト、5xx）に対するエクスポネンシャルバックオフ＆リトライ。
    - レスポンスの厳格なバリデーションとスコアの ±1.0 クリップ。
    - 書き込みは部分更新保護（DELETE → INSERT）により冪等性を確保。DuckDB の executemany の空リスト制約に対応。
    - テスト容易性のため OpenAI 呼び出し箇所をモジュール内でラップ（ユニットテストで差し替え可能）。
  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース由来の LLM センチメント（重み30%）を合成して日次のレジーム（bull/neutral/bear）を算出。
    - マクロ記事のフィルタリング（キーワード群）→ LLM 評価（JSON 出力）→ スコア合成。
    - API 再試行・フォールバック戦略（API失敗時は macro_sentiment=0.0）。
    - 計算結果は market_regime に冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス回避の設計（date < target_date の排他クエリ、datetime.today() を参照しない）。

- データ（Data）モジュール
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - market_calendar を元に営業日判定を行うユーティリティ群：
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得の場合は曜日（平日）ベースのフォールバックを使用。
    - カレンダー夜間更新ジョブ（calendar_update_job）: J-Quants から差分取得、バックフィル、健全性チェック、冪等保存。
    - 探索範囲上限やバックフィル日数などの安全策を実装。
  - ETL パイプライン (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL 実行結果を表す `ETLResult` データクラスを提供（取得数・保存数・品質検査結果・エラー一覧等を保持）。
    - 差分取得、backfill、品質チェックの設計方針、DuckDB テーブル存在チェック等のユーティリティを実装。
    - デフォルトの最小データ開始日・バックフィル日数等を定義。
    - `kabusys.data.etl` で `ETLResult` を公開再エクスポート。

- リサーチ（Research）
  - ファクター計算 (`kabusys.research.factor_research`)
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）を DuckDB 上の SQL と Python で計算する関数群:
      - calc_momentum, calc_volatility, calc_value。
    - データ不足時の None 扱い、設計上本番APIにはアクセスしないことを明示。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン算出（calc_forward_returns、可変ホライズン対応）、IC（calc_ic）、ランク変換（rank）、統計サマリ（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
  - research パッケージの __init__ で主要関数を公開。

- その他の実装上の配慮
  - 各所で DuckDB の振る舞い（executemany の空リスト制約、日付形式）への互換性対策を実施。
  - ロギングを充実させ、失敗時も一部機能を継続（フェイルセーフ）する設計。
  - テストしやすい実装（外部依存呼び出しをラップして差し替え可能）を意識。

### Changed
- （初版のため過去の変更履歴なし）設計注記として:
  - すべての AI 連携機能は OpenAI API キー（引数または環境変数 OPENAI_API_KEY）依存。未設定時は ValueError を投げる動作を採用。
  - レスポンスパース失敗や API エラー時は例外を上位へ伝播させず、該当チャンク/処理をスキップして他処理を継続するフェイルセーフ設計。

### Fixed
- （初版のため修正履歴なし）

### Security
- 機密情報取り扱い:
  - 必須トークン（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）は Settings で明示的に要求。未設定時はエラーで通知。
  - .env の読み込みは process 環境変数を protected として扱い、`.env.local` を上書きで読み込む実装。テスト時の自動ロード停止フラグあり。

### Notes / Known limitations
- OpenAI の呼び出しは外部ネットワークに依存するため、API レート制限・ネットワーク断・料金などの運用注意が必要。
- DuckDB のバージョンや実行環境によっては SQL の一部振る舞い（リストバインド等）に差異が出る可能性があり、そのための互換性対策がコード中に含まれます。
- AI モジュールは出力の形式（LLM が返す JSON の正確さ）に依存するため、LLM側の挙動変化やモデル差分によりパース処理が影響を受ける可能性があります。レスポンスパース失敗時はスコアをスキップまたは 0 にフォールバックします。
- 現時点でユニットテストやCIの実装有無は不明（コードはテスト差替え用のフックを用意）。

### Migration / Usage notes
- 初回導入時
  - 必要な環境変数を設定（.env/.env.local をプロジェクトルートに配置するか OS 環境変数を設定）。
  - OpenAI を利用する機能（score_news / score_regime）を利用する場合は OPENAI_API_KEY を用意。
  - DuckDB（および必要なテーブル：prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を準備。
- ETL/カレンダー
  - calendar_update_job を運用する場合は J-Quants API のクライアント（jquants_client）が適切に設定されていることを確認。
- ローカルテスト
  - 自動で .env 読み込みが行われるため、テスト実行時に環境干渉を避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化してください。

---

今後のリリースでは、テストカバレッジ、より詳細な品質チェック、モデル差分対応、追加のファクターや発注/実行（execution）・モニタリング（monitoring）機能の拡充などを予定しています。
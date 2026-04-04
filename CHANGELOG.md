# Changelog

すべての変更は「Keep a Changelog」規約に従い、Semantic Versioning を採用しています。  

履歴はできる限りコードベースから推測して記載しています。不足・誤りがあればお知らせください。

## [Unreleased]

## [0.1.0] - 2026-04-04

初回リリース — 日本株自動売買／リサーチ用ライブラリ「KabuSys」初版。

### 追加 (Added)
- パッケージ基礎
  - パッケージルート: `kabusys` を公開。バージョンは `0.1.0`。
  - サブモジュール公開: `data`, `strategy`, `execution`, `monitoring` を `__all__` でエクスポート。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートの検出に `.git` または `pyproject.toml` を使用）。
  - 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`。`.env.local` は上書き（override）するが OS 環境変数は保護される設計。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で使用可能）。
  - `.env` パーサ実装:
    - コメント行（先頭 `#`）・空行を無視。
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープに対応。
    - クォートなし値でのインラインコメント判定（`#` の直前が空白またはタブの場合のみコメントと扱う）を実装。
  - `Settings` クラスを提供し、各種設定値をプロパティ経由で取得可能:
    - J-Quants / kabuステーション / LINE / DB (DuckDB/SQLite) / 監視閾値等の設定を取得。
    - 必須環境変数取得時（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）は未設定なら `ValueError` を送出。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）と利便性プロパティ (`is_live`, `is_paper`, `is_dev`) を追加。

- AI（NLP / レジーム検出）
  - ニュースセンチメント (`kabusys.ai.news_nlp`)
    - 指定時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を対象に raw_news と news_symbols を集約し、銘柄単位にニュースをまとめるロジックを実装。
    - OpenAI（gpt-4o-mini、JSON Mode）へ最大 20 銘柄／チャンクでバッチ送信してスコアリング。
    - 1銘柄あたりの記事数・文字数制限（トークン肥大化対策）を実装（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ処理を実装。
    - リトライ戦略（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実装。
    - 処理はフェイルセーフ: API 失敗やバリデーション失敗時は該当チャンク／銘柄をスキップし、その他銘柄は継続。
    - テスト容易性: OpenAI 呼び出しを行う内部関数 `_call_openai_api` を patch して差し替え可能。
    - 実行関数 `score_news(conn, target_date, api_key=None)` を提供。取得したスコアを `ai_scores` テーブルへ冪等的に書き込む（DELETE → INSERT）。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定を行う機能を実装。
    - マクロキーワードで raw_news タイトルを抽出し、OpenAI に JSON 出力を要求してマクロセンチメントを取得。
    - API 呼び出しのリトライ・エラーハンドリングを実装。最終的にフェイルセーフで macro_sentiment=0.0 にフォールバック。
    - レジームスコアの閾値により `bull` / `neutral` / `bear` ラベルを決定し、`market_regime` テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - テスト容易性のため `_call_openai_api` は別実装にしてモジュール結合を抑制。
    - 実行関数 `score_regime(conn, target_date, api_key=None)` を提供。

- データプラットフォーム（Data）
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの取り扱い、営業日判定、次/前営業日取得、期間内営業日の取得、SQ 判定などのユーティリティを実装。
    - DB（`market_calendar`）が空または未整備の場合は曜日ベース（週末除外）でフォールバックする堅牢設計。
    - `calendar_update_job(conn, lookahead_days=90)` により J-Quants から差分取得 → 冪等保存（jquants_client を利用）を行う夜間バッチ処理を実装。バックフィル／健全性チェックを備える。
  - ETL パイプライン (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL 結果を保持するデータクラス `ETLResult` を実装・公開（`kabusys.data.etl` で再エクスポート）。
    - 差分更新ロジック、バックフィル、品質チェック統合の方針と基本ユーティリティを実装（jquants_client と quality モジュール連携想定）。
    - 品質チェックは重大な問題があっても処理を続け、呼び出し元で判断する設計（Fail-Fast しない）。
    - DuckDB の互換性配慮（executemany の空リスト制約等）を考慮した実装。

- リサーチ（Research）
  - ファクター計算 (`kabusys.research.factor_research`)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER、ROE）の計算関数を実装。
    - DuckDB 上の SQL と Python を組み合わせた実装で、外部 API へはアクセスしない設計。
    - 各関数は (date, code) をキーとする辞書リストを返す（テスト／上流ロジックとの結合が容易）。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算（`calc_forward_returns`）、IC（Information Coefficient）計算（`calc_ic`）、ファクター統計サマリ（`factor_summary`）、ランク変換ユーティリティ（`rank`）などを実装。
    - pandas 等へ依存せず、標準ライブラリのみで実装。リターン計算はホライズン検証（正の整数かつ <= 252）を行う。

### 変更 (Changed)
- （初版のため履歴上の変更はありません）

### 修正 (Fixed)
- （初版のため履歴上の修正はありません）

### 非推奨 (Deprecated)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- OpenAI API キーはコード内にハードコーディングされず、`api_key` 引数または環境変数 `OPENAI_API_KEY` を利用する設計。未設定時は `ValueError` を発生させるため誤使用が早期に検出される。

### 注意事項 / 補足
- 多くの処理（AI 呼び出し、DB 書き込み）はフェイルセーフ（失敗時に処理継続 or 部分保存）を意識して設計されていますが、本番運用前に環境（API キー、DB スキーマ、テーブル存在など）の検証が必要です。
- DuckDB 固有の実装上の注意（`executemany` に空リストを渡せない等）が随所に考慮されています。DuckDB のバージョン差異により挙動が変わる可能性があります。
- 自動 .env ロードはプロジェクトルート検出に依存するため、パッケージ配布後や CWD が異なる状況でも期待通りに動くよう設計されています。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- テスト性を高めるため、OpenAI 呼び出し点は内部関数を patch して差し替え可能にしてあります（ユニットテストでのモックが容易）。

---

（以上）
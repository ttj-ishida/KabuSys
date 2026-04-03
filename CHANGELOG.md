# Changelog

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
このファイルはコードベースの内容から推測して作成しています。

すべての変更は非互換な変更（Breaking Changes）、追加（Added）、変更（Changed）、修正（Fixed）等に分類しています。初回リリース（v0.1.0）相当の機能をまとめています。

## [Unreleased]
- 次回リリースに向けた未確定の変更点はありません。

## [0.1.0] - 2026-04-03
初期リリース相当。以下の主要機能・実装を追加。

### Added
- パッケージ基盤
  - パッケージ名: `kabusys`。トップレベルで `"data"`, `"strategy"`, `"execution"`, `"monitoring"` をエクスポート。
  - バージョン定義: `__version__ = "0.1.0"`。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを `.git` または `pyproject.toml` から探索）。
  - 読み込み優先度: OS 環境変数 > `.env.local` > `.env`。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーを実装:
    - `export KEY=val` 形式に対応。
    - シングル・ダブルクォートのバックスラッシュエスケープ処理。
    - コメント (inline) の扱い、無効行のスキップ等の堅牢なパースロジック。
  - `Settings` クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / 監視関連 / システム設定等のプロパティを環境変数から取得（必須変数は `_require` で検証）。
  - `KABUSYS_ENV`（development/paper_trading/live）や `LOG_LEVEL` のバリデーション、`is_live` / `is_paper` / `is_dev` のヘルパーを実装。

- ニュース・NLP / AI モジュール
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp.score_news`)
    - 前日 15:00 JST ～ 当日 08:30 JST 相当のニュースウィンドウ計算（UTC 換算）を実装。
    - `raw_news` と `news_symbols` を結合して銘柄ごとに記事を集約（件数／文字数上限でトリム）。
    - OpenAI（`gpt-4o-mini`）の JSON Mode を用いたバッチ評価（1 API コールあたり最大 20 銘柄）を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフによるリトライ、レスポンスの堅牢なバリデーション、スコアの ±1.0 クリップ。
    - 取得したスコアを `ai_scores` に冪等的に書き込む（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（モック可能）。

  - 市場レジーム判定 (`kabusys.ai.regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロキーワードでニュースを抽出、LLM（`gpt-4o-mini`）でマクロセンチメントを JSON 出力で取得。
    - レジームスコアの合成・閾値によるラベル付け・`market_regime` テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK の試行とログ出力。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - news_nlp とは OpenAI 呼び出し実装を分離し、モジュール結合を避ける設計。

  - 共通設計指針（AI 関連）
    - いずれの関数も datetime.today() / date.today() を直接参照せず、与えられた `target_date` に基づいて処理（ルックアヘッドバイアス対策）。
    - OpenAI API キーは引数経由で注入可能（テスト容易性）かつ環境変数 `OPENAI_API_KEY` をサポート。

- リサーチ（因子計算 / 特徴量探索）
  - `kabusys.research.factor_research`
    - `calc_momentum`: 1M/3M/6M リターン・200日 MA 乖離の計算。データ不足時の None 処理。
    - `calc_volatility`: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。
    - `calc_value`: raw_financials から最新財務データを取得して PER（EPS が有効な場合）、ROE を計算。
    - DuckDB のウィンドウ関数や LAG/LEAD を用いた SQL ベースの実装で、外部 API 呼び出しなし。
  - `kabusys.research.feature_exploration`
    - `calc_forward_returns`: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで計算。
    - `calc_ic`: スピアマン（ランク）相関による IC 計算（同順位は平均ランクで処理）。有効レコード不足時は None を返す。
    - `factor_summary`: count/mean/std/min/max/median を計算する統計ユーティリティ。
    - `rank`: ランク付け（同順位は平均ランク）。浮動小数の丸めを行って ties を安定化。

- データプラットフォーム / ETL
  - `kabusys.data.calendar_management`
    - JPX カレンダー管理ロジック（`market_calendar` テーブル利用）。
    - 営業日判定: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（平日を営業日扱い）。
    - 夜間バッチ job `calendar_update_job` を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存）。
  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL の差分取得・保存・品質チェックの枠組みを実装。
    - ETL 実行結果を表す `ETLResult` データクラスを提供（fetch/save 件数、品質問題、エラーメッセージ等を保持、`to_dict()` をサポート）。
    - 差分更新のデフォルト戦略（営業日単位、自動的に未取得レンジ計算）、バックフィル日数、品質チェックの扱い（検出しても処理継続）などを実装。
    - `etl.ETLResult` を `kabusys.data.etl` で再エクスポート。

- DuckDB / DB 操作の堅牢化
  - トランザクション制御（BEGIN/COMMIT/ROLLBACK）と ROLLBACK 失敗時のログ。
  - `executemany` へ空リストを渡さないガード（DuckDB 0.10 向け互換性考慮）。
  - 日付変換ユーティリティ（DuckDB からの値 → `datetime.date`）の実装。

- ロギング・エラーハンドリング
  - 各種処理で詳細な INFO/WARNING/DEBUG ログを出力。
  - 外部 API（OpenAI / J-Quants）呼び出しの例外分類とリトライポリシー（指数バックオフ）。
  - レスポンスパース失敗やデータ不足時のフェイルセーフ設計（例外を投げずに安全側の値で継続する箇所多数）。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Deprecated
- （初回リリースのためなし）

### Removed
- （初回リリースのためなし）

### Security
- API キーの取り扱い: OpenAI キーは引数で注入可能。環境変数に依存する場合でも `_require` で明示的にチェックし、未設定時は例外を投げる（誤用の早期発見を支援）。

---

注記:
- 実装はテストしやすさ（モック可能な API 呼び出し、環境読み込みの無効化）とルックアヘッドバイアス防止を重視して設計されています。
- 上記はソースコードから推測してまとめた CHANGELOG です。実際のリリースノートとして使用する場合は、追加の実績（テスト結果・既知の制限・インストール手順等）を補足してください。
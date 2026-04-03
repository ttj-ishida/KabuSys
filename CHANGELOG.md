# CHANGELOG

すべての変更は Keep a Changelog の仕様に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います（例: MAJOR.MINOR.PATCH）。

## [0.1.0] - 2026-04-03

初回公開リリース。

### 追加
- パッケージエントリポイント
  - `kabusys` パッケージの公開 API を定義（`__version__ = "0.1.0"`、`__all__ = ["data", "strategy", "execution", "monitoring"]`）。

- 環境設定 / 設定管理
  - `kabusys.config` モジュールを追加。
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサーで以下をサポート:
    - コメント行・空行スキップ、`export KEY=val` 形式、シングル・ダブルクォートのエスケープ処理、行内コメントの扱い（クォート有無での差異）。
  - `Settings` クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境・ログレベル等のプロパティを公開。
  - 必須環境変数チェック（`_require`）により未設定時は明示的なエラーメッセージを返す。
  - 有効な環境 (`development`, `paper_trading`, `live`) とログレベルの検証を実装。

- AI（ニュース・レジーム判定）
  - `kabusys.ai.news_nlp` を追加: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメントを算出し、`ai_scores` テーブルへ保存する機能。
    - JST 時間ウィンドウ（前日 15:00 ～ 当日 08:30）に基づく対象選定（UTC 変換済み）。
    - 1 銘柄あたり記事数・文字数のトリム、最大バッチサイズ、JSON Mode を用いたレスポンス処理。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスのバリデーション、スコアの ±1.0 クリッピング。
    - DuckDB への冪等書き込み（DELETE → INSERT）と DuckDB executemany の空リスト対策。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能に設計（`_call_openai_api` を patch 可能）。
  - `kabusys.ai.regime_detector` を追加: ETF 1321（225 連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出し、`market_regime` テーブルへ冪等書き込み。
    - マクロニュース抽出用キーワードリスト、最大記事数制限、OpenAI 呼び出し時のリトライ／フォールバック（失敗時 macro_sentiment=0.0）。
    - レジームスコアの合成と閾値判定、ログ出力。

- データプラットフォーム（ETL / カレンダー等）
  - `kabusys.data.calendar_management` を追加:
    - JPX カレンダーの夜間差分更新ジョブ（`calendar_update_job`）、market_calendar の保存ロジック。
    - 営業日判定ユーティリティ: `is_trading_day` / `next_trading_day` / `prev_trading_day` / `get_trading_days` / `is_sq_day` を実装。
    - カレンダー未取得時の曜日ベースフォールバック、最大探索日数制限および健全性チェック、DB 値優先の一貫した振る舞い。
  - `kabusys.data.pipeline`（ETL パイプライン）を追加:
    - 差分取得・保存・品質チェックの流れを実装するためのユーティリティ。
    - ETL 実行結果を表す `ETLResult` データクラスを公開（取得/保存件数、品質問題、エラー一覧、ヘルパーメソッドを含む）。
    - 固有の設計方針を文書化（差分単位、backfill、品質チェックの扱いなど）。
  - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- リサーチ / ファクター計算
  - `kabusys.research` パッケージを追加。
  - `factor_research`:
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金／出来高変化率）、バリュー（PER, ROE）を計算する関数群（`calc_momentum`, `calc_volatility`, `calc_value`）。
    - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials のみ参照する設計。
  - `feature_exploration`:
    - 将来リターン算出（`calc_forward_returns`）、IC（スピアマン ρ）計算（`calc_ic`）、ランク変換（`rank`）、統計サマリー（`factor_summary`）を実装。
    - pandas 等外部依存なしの純標準ライブラリ実装。
  - `research.__init__` で主要関数を再エクスポート。

### 変更（設計上の重要点）
- ルックアヘッドバイアス対策
  - AI 評価・ファクター計算・ニュースウィンドウ等のすべてで `datetime.today()` / `date.today()` を直接参照せず、呼び出し側から `target_date` を受け取る設計に統一。
  - DB クエリは target_date 未満 / 排他条件などで過去データのみを使用するよう配慮。

- OpenAI 統合の堅牢化
  - gpt-4o-mini をデフォルトモデルとして使用。
  - JSON Mode を期待しつつ、前後余計なテキストが混ざる場合の復元ロジックや厳格なバリデーションを実装。
  - リトライ戦略（指数バックオフ）と 5xx の振る舞い区別、API エラー時のログ＆フェイルセーフ（例: 0.0 にフォールバック）を導入。

- DuckDB 書き込みの冪等性
  - market_regime / ai_scores 等へは DELETE→INSERT の形で冪等に上書き（トランザクション: BEGIN/COMMIT/ROLLBACK）。
  - DuckDB executemany に対して空リストを渡すと失敗するため、空チェックを挟む等の互換性対策を実施。

- テスト容易性
  - OpenAI 呼び出しをラップする内部関数（`_call_openai_api`）を用意し、unit test で差し替え（patch）可能にしている。

### 修正（安定性/エラー処理）
- 各所でのエラー/例外ハンドリング改善:
  - .env ファイル読み込み失敗時に警告を出力して継続。
  - OpenAI 呼び出し失敗や JSON パース例外時に WARNING を出し、フェイルセーフ値で継続（全面停止させない）。
  - トランザクション中の例外発生時にロールバックを試行し、ロールバック失敗時はログ出力。
  - calendar_update_job / pipeline の外部 API 呼び出し時に例外捕捉して 0 を返し呼び出し元での扱いを明確化。

### ドキュメント・注記
- 各モジュールに詳細な docstring を追加し、設計方針・想定テーブル構造・時間ウィンドウ・フェイルセーフの挙動を明記。
- 外部依存（OpenAI、J-Quants、kabu API、DuckDB）とのインターフェース仕様と想定挙動をコメントにて明示。

### 既知の制限
- PBR・配当利回りなど一部のバリューファクターは未実装（calc_value 参照）。
- News/NLP の出力は LLM に依存するため、モデル変更時はプロンプトやレスポンス検証ロジックの調整が必要。
- DuckDB のバージョンによるバインド挙動の差異に注意（executemany の空リスト等）。

---

今後の予定（例）
- 0.2.0: 実運用向けの監視・モニタリング機能（monitoring）と実行（execution）モジュールの充実、戦略モジュール（strategy）の実装拡張、より詳細なドキュメントと CI テスト整備。
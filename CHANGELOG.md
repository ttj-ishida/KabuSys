# Changelog

すべての重要な変更点は Keep a Changelog の慣習に従って記載します。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成したリリースノートです。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買・データ基盤・リサーチ支援のためのコアライブラリを実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージのバージョンを `__version__ = "0.1.0"` として公開。パッケージの公開 API として `data`, `strategy`, `execution`, `monitoring` を `__all__` に定義。

- 環境設定管理 (`kabusys.config`)
  - `.env` / `.env.local` 自動読み込み機能を実装（ルート検出は `.git` または `pyproject.toml` を基準）。
  - 自動読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - `.env` ファイルパーサを実装：コメント・`export KEY=...`、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱いを考慮。
  - OS 環境変数を保護するための `protected` セットを採用し、`.env.local` による上書き制御を実現。
  - `Settings` クラスを提供：J-Quants / kabu API / Slack / DB パス / 監視設定 / システム設定（env, log_level 等）を環境変数から取得、必須項目は未設定時に明示的に例外を発生させる。

- ニュース NLP（AI）モジュール (`kabusys.ai.news_nlp`)
  - OpenAI（gpt-4o-mini）の JSON Mode を使ったニュースセンチメントスコアリング機能を実装。
  - ターゲット日の「前日 15:00 JST ～ 当日 08:30 JST」を基にニュースウィンドウを算出する `calc_news_window` を実装（UTC naive datetime で返却）。
  - raw_news と news_symbols を集約し、銘柄ごとに複数記事を結合（最大記事数・文字数でトリム）。
  - バッチ処理（最大20銘柄/チャンク）で API 呼び出しを行い、レスポンスをバリデーションして `ai_scores` テーブルへ冪等的に書き込み。
  - リトライ（429 / ネットワーク / タイムアウト / 5xx）や指数バックオフ、API 失敗時のフェイルセーフ（該当チャンクはスキップ）を実装。
  - レスポンスの柔軟なパース（前後テキスト混入からの {} 抽出等）とスコアの ±1.0 クリップ。

- 市場レジーム判定モジュール (`kabusys.ai.regime_detector`)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（`bull`/`neutral`/`bear`）を算出する `score_regime` を実装。
  - マクロ記事フィルタリング（複数のキーワード）と OpenAI 呼び出し（gpt-4o-mini, JSON モード）を用いたセンチメント算出を実装。
  - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
  - DuckDB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試みる。

- データ基盤・ETL (`kabusys.data.pipeline`, `kabusys.data.etl`)
  - ETL 実行結果を表す `ETLResult` データクラスを実装（取得件数・保存件数・品質問題・エラーの集約）。
  - ETL の設計方針（差分更新、バックフィル、品質チェックの扱い）をコードコメントとして明記し、後続開発が実装しやすいインターフェースを提供。
  - `kabusys.data` 経由で `ETLResult` を再エクスポート。

- マーケットカレンダー管理 (`kabusys.data.calendar_management`)
  - JPX カレンダーを管理するためのユーティリティ群を実装。
  - 営業日判定関数：`is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days` を実装。DB にデータがない場合は曜日ベースでフォールバック。
  - カレンダー差分取得・保存の夜間バッチジョブ `calendar_update_job` を実装（J-Quants クライアント経由で取得、保存は idempotent）。
  - バックフィル・健全性チェック（未来日付の異常検出）を実装。

- リサーチ（ファクター計算・特徴量探索） (`kabusys.research.*`)
  - ファクター計算 (`calc_momentum`, `calc_volatility`, `calc_value`) を実装：
    - Momentum: 1M/3M/6M リターン・200 日 MA 乖離
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - Value: PER（EPS による分岐）と ROE（raw_financials の最新値を参照）
  - 特徴量探索（forward returns、IC、rank、factor_summary）を実装：
    - 将来リターン `calc_forward_returns` は複数ホライズンに対応（デフォルト [1,5,21]）。
    - `calc_ic` はランク相関（Spearman ρ）を実装（3 銘柄未満は None）。
    - `rank` は同順位の平均ランク処理を採用。
    - `factor_summary` は count/mean/std/min/max/median を計算。
  - z-score 正規化ユーティリティを `kabusys.data.stats` から再エクスポートする設計（モジュール連携）。

### 変更 (Changed)
- 実装方針・安全対策（コード内コメントとして明示）
  - 全ての AI / リサーチ関数は日時の取得において `datetime.today()` / `date.today()` を直接参照しない方針を採用（ルックアヘッドバイアスの防止）。
  - OpenAI 呼出箇所にはテスト置換ができるよう `_call_openai_api` を定義（unittest.mock.patch による差し替え容易化）。
  - DuckDB の互換性を考慮し、`executemany` に空リストを渡さないガードを実装（DuckDB 0.10 の制約対応）。
  - API エラー処理で 5xx とそれ以外を分けたリトライロジックを採用。

### 修正 (Fixed)
- エッジケース処理の追加
  - .env パーサで不正行やキーなし行を無視するようにし、クォート内のエスケープ処理やインラインコメントの誤解釈を防止。
  - 移動平均 / ATR 等のウィンドウ内データ不足時は None または中立値（例: ma200_ratio=1.0）を返すことで downstream の例外化を防ぐ。
  - OpenAI レスポンスが不正な JSON を返した場合の部分復元（最外の {} を抽出して再パース）を行い、不要な例外伝播を抑制。
  - DB 書き込み時に例外発生 → ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログに残す。

### セキュリティ (Security)
- 外部 API キー（OpenAI 等）は引数で注入可能にし、環境変数参照に依存しすぎない設計。必須未設定時は明示的に例外を発生させることで誤使用を防ぐ。

### 既知の制約 / 注意事項 (Known issues / Notes)
- OpenAI モデル `gpt-4o-mini` の JSON Mode に依存しており、API 仕様変更があった場合は対応が必要。
- 一部の処理（例: `kabusys.research` 関連）は純粋に DuckDB と標準ライブラリで実装しており、Pandas 等の利用は行っていないため、大規模データ時のパフォーマンス評価が必要。
- パッケージ公開 API に `monitoring` が含まれるが、本差分に関する具体実装は提示されていない（将来的な拡張想定）。
- この CHANGELOG はソースコードのコメント・実装から推測して作成しています。細部の実装方針や未公開のユーティリティについては実際のコミット履歴を参照してください。

---

参考: Keep a Changelog のカテゴリ (Added / Changed / Fixed / Security / Notes) に準拠して要約しています。
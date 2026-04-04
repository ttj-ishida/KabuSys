# Changelog

すべての重要な変更点をこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット:
- 変更は [Unreleased] または セマンティックバージョン（例: 0.1.0 - YYYY-MM-DD）ごとに分類します。
- セクションは Added / Changed / Deprecated / Removed / Fixed / Security を使います。

## [0.1.0] - 2026-04-04

初回公開リリース。日本株自動売買システムのコアライブラリを実装。以下の主要機能とモジュールを含む。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。
  - バージョンは `0.1.0` に設定。

- 設定管理
  - 環境変数・.env ファイル自動読み込み機能（src/kabusys/config.py）。
    - プロジェクトルートを `.git` または `pyproject.toml` を起点に探索して .env を読み込む（カレントワーキングディレクトリに依存しない挙動）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
    - .env のパースは `export KEY=val` 形式、引用符・エスケープ、インラインコメントを考慮。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / リソース閾値 / 実行環境 (development/paper_trading/live) / ログレベル等を環境変数から取得・検証。

- データプラットフォーム (DuckDB ベース)
  - ETL 結果を表す ETLResult データクラス（src/kabusys/data/pipeline.py, exported via src/kabusys/data/etl.py）。
    - 品質チェック結果の格納、エラー検出プロパティなど。
  - market_calendar（JPXカレンダー）管理・ユーティリティ（src/kabusys/data/calendar_management.py）。
    - 営業日判定: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - カレンダーが未登録の場合は曜日（土日）ベースのフォールバックを適用。
    - カレンダー夜間バッチ更新ジョブ: calendar_update_job（J-Quants から差分取得・冪等保存・バックフィル・健全性チェック）。
  - ETL パイプラインの基礎（設計方針を含む）：差分更新・backfill・品質チェック（pipeline モジュールに詳細ロジックの土台）。

- 研究（Research）モジュール
  - ファクター計算群（src/kabusys/research/factor_research.py）
    - モメンタム: calc_momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ/流動性: calc_volatility（20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比）
    - バリュー: calc_value（PER, ROE を raw_financials から取得）
    - DuckDB SQL を用いた実装。欠損・データ不足時は None を返す設計。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns（任意ホライズン, デフォルト [1,5,21]）
    - IC 計算: calc_ic（スピアマンのランク相関）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - ランク変換ユーティリティ: rank（同順位は平均ランク）

- AI（自然言語処理）モジュール
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）へ JSON モードでバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - チャンク処理（最大 20 銘柄/回）、記事・文字数上限、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアのクリップ、冪等的な ai_scores 書き込み（DELETE → INSERT）を実装。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。
    - 時刻ウィンドウ計算: calc_news_window（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出し・リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - 結果を market_regime テーブルへ冪等書き込み。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。

- モジュール分割・エクスポート
  - ai パッケージは score_news を公開（src/kabusys/ai/__init__.py）。
  - research パッケージは主要ファンクション群を公開（src/kabusys/research/__init__.py）。
  - data パッケージは ETLResult を再エクスポート（src/kabusys/data/etl.py）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security / Notes
- OpenAI API の利用には API キーが必要。score_news / score_regime は引数で api_key を注入可能。未設定の場合は環境変数 `OPENAI_API_KEY` を参照し、未設定時は ValueError を送出して処理を中断する。
- .env 自動読み込みはデフォルトで有効。CI/テストで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すること。
- DB 書き込みは冪等性を意識して実装（DELETE→INSERT / ON CONFLICT を想定）。
- DuckDB のバージョン差異に留意（executemany の空リスト制約などへの対応が組み込まれている）。

---

今後の予定（例）
- モジュール単位のユニットテスト追加（特に OpenAI 呼び出し周りのモック化）
- J-Quants クライアントの詳細実装・統合テスト
- モデル/パラメータのチューニング・監視・運用ジョブの整備

（必要があればリリース日や差分の粒度を調整して、より詳細な CHANGELOG を生成します。）
# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン番号はパッケージ内の __version__ に合わせています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージの初期リリースを公開。
- 基本パッケージ構成を導入:
  - kabusys (トップパッケージ)
  - サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に公開）
- 環境設定管理:
  - kabusys.config: .env ファイルおよび環境変数からの設定読み込み、自動ロード機能（プロジェクトルート検出による .env / .env.local の読み込み）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベルなどの設定プロパティを公開。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化、読み込み時の保護キー(protected)対応。
- AI 関連:
  - kabusys.ai.news_nlp: ニュースをまとめて OpenAI（gpt-4o-mini）に投げ、銘柄ごとのセンチメント(ai_score)を ai_scores テーブルへ格納するバッチ処理機能を実装。
    - タイムウィンドウ計算、記事トリム、チャンク化（最大20銘柄/チャンク）、リトライ（指数バックオフ）、レスポンス検証、DuckDB への冪等書き込み（DELETE → INSERT）を実装。
  - kabusys.ai.regime_detector: ETF (1321) の 200日移動平均乖離とニュース由来のマクロセンチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、OpenAI 呼び出し（独立実装）、スコア合成ロジック、フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
- データプラットフォーム:
  - kabusys.data.pipeline / ETLResult: ETL パイプライン用データクラスと補助ユーティリティを追加（差分取得・保存・品質チェックを想定した設計）。
  - kabusys.data.etl: ETLResult の再エクスポートを追加。
  - kabusys.data.calendar_management: JPX カレンダー管理と営業日判定ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day、calendar_update_job）。
    - DB に情報がある場合は優先して使用、未登録日は曜日ベースでフォールバックする一貫したロジックを提供。
- リサーチ / ファクター分析:
  - kabusys.research.factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日ATR、相対ATR）、バリュー（PER, ROE）等の計算関数を実装。DuckDB SQL を用いた実行。結果は (date, code) ベースの辞書リストで返却。
  - kabusys.research.feature_exploration: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、ランク化ユーティリティ(rank)、統計サマリー(factor_summary) を追加。
- データユーティリティ:
  - DuckDB 接続を前提にした各種 SQL ベースの処理を多数実装（prices_daily / raw_news / raw_financials / market_calendar / ai_scores 等を参照）。
- ロギングと設計ドキュメント:
  - 各モジュールに詳細な docstring と設計方針を記載。ルックアヘッドバイアス回避やフェイルセーフ方針を明示。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- .env パーサーの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、キー無効行のスキップなど多数のケースに対応。
  - .env の読み込みで既存の OS 環境変数が保護されるよう protected キーセットを導入。
- OpenAI レスポンスパース/検証の堅牢化:
  - news_nlp および regime_detector で JSON Mode を想定しつつ、前後に余計なテキストが混在するケースに対して最外の {} を抽出して復元するフェールセーフロジックを追加。
  - レスポンスのキー検証、型検証、未知コードの無視、数値のクリップ（±1.0）を実装。
- OpenAI API 呼び出しのエラーハンドリングとリトライ:
  - 429 / ネットワーク断 / タイムアウト / 5xx などを対象に指数バックオフで再試行。再試行上限超過時は警告ログを出しフォールバック（スコア0.0 または該当チャンクスキップ）して処理を継続。
  - APIError の status_code を安全に参照する実装。
- DuckDB 側の互換性考慮:
  - executemany に空リストを渡さないガード（DuckDB 0.10 の制約への対応）。
  - idempotent な DB 書き込み（DELETE → INSERT）により部分失敗時のデータ保護。
- 日付/時間に関する扱い:
  - calc_news_window 等で JST と UTC の変換を明確化し、target_date ベースで「前日15:00 JST〜当日08:30 JST 相当」を正しく UTC naive datetime に変換。
  - 各モジュールで datetime.today() / date.today() の直接参照を避け、引数で基準日を渡す設計（ルックアヘッドバイアス防止）。
- カレンダー周りの堅牢性:
  - market_calendar が未登録またはデータ欠損時のフォールバック挙動を明確化。最大探索日数制限(_MAX_SEARCH_DAYS)による無限ループ防止。
  - calendar_update_job: バックフィル・健全性チェック・J-Quants API 呼び出しのエラー処理を実装。

### セキュリティ (Security)
- 環境変数読み込みで OS 環境変数を上書きしないデフォルト挙動を採用。必要に応じて .env.local を override として読み込めるが、起動時に KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
- OpenAI API キーや Slack トークンなど重要情報は Settings 経由で必須取得し、未設定時は ValueError を送出して誤動作を防止。

### ドキュメント (Documentation)
- 各モジュールに詳細な処理フロー、設計方針、例外処理やフェイルセーフ動作を docstring として記載。テスト向けに内部 API 呼び出し関数を差し替え可能にする設計（unittest.mock.patch を想定）。

---

注:
- 本リリースは「初期実装」をまとめたものです。実運用時は OpenAI API キーや各種外部サービス設定（J-Quants、kabuステーション、Slack など）を環境変数で適切に設定してください。
- 各関数の動作は docstring に詳細があるため、利用前にそちらを参照してください。
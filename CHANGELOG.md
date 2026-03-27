# Keep a Changelog
すべての変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

全般:
- ルール: https://keepachangelog.com/（日本語訳を参考）
- バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システムの基盤機能群を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys（src/kabusys）。
  - エクスポート: data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動読み込みを無効にするためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしの場合は行内コメント（#）を適切に扱う。
  - 環境変数の保護:
    - OS 環境変数は protected として上書きされない。
  - Settings クラスを提供（settings でインスタンスを公開）。
    - J-Quants、kabu ステーション、Slack、データベースパス等の必須/既定値を取得するプロパティ。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - duckdb/sqlite のデフォルトパス（DUCKDB_PATH, SQLITE_PATH）。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルに書き込む。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換で DB クエリを実行）。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄で API に一括送信。
    - 1銘柄あたりのトリム: 最大記事数 / 最大文字数で制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode を利用し厳密な JSON レスポンスを期待。レスポンスのバリデーションと数値クリップ（±1.0）。
    - リトライ戦略: 429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフ（_MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - API 呼出し部分は _call_openai_api 関数で切り出しており、テスト時にモック可能。
    - 部分失敗時に既存スコアを保護するため、書き込みは対象コード絞り込みの DELETE → INSERT による置換。
    - フェイルセーフ: API 失敗時はそのチャンクをスキップして処理継続。APIキー未設定時は ValueError を送出。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - 処理フロー: ma200_ratio 計算 → マクロニュース抽出 → OpenAI で macro_sentiment を評価 → スコア合成 → market_regime テーブルへ冪等書き込み。
    - API 呼び出しは独立実装（news_nlp と内部関数共有を避ける）。
    - API 失敗時は macro_sentiment=0.0 としてフォールバック。リトライは指数バックオフ。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターン、例外時は ROLLBACK を試行。

- データ管理・ETL (src/kabusys/data)
  - ETL パイプライン (src/kabusys/data/pipeline.py)
    - 差分取得、保存（jquants_client の save_* を利用して冪等保存）、品質チェック（quality モジュール）を統合する基盤実装。
    - ETLResult データクラスを導入（target_date, fetched/saved counts, quality_issues, errors 等を保持）。
    - テーブル最大日付取得、テーブル存在チェック等のユーティリティを提供。
    - バックフィル（デフォルト数日）をサポートし、API の後出し修正を吸収する仕組み。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB にデータがない場合は曜日ベース（土日休）でフォールバックする設計。
    - calendar_update_job を実装: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを含む。
    - 最大探索日数・先読み・バックフィルなど安全用定数を設定。

- リサーチ（特徴量・ファクター） (src/kabusys/research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）等を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比等を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS=0/欠損は None）。
    - 全関数は DuckDB と prices_daily/raw_financials のみを参照し外部 API に依存しない設計。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証あり。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 件未満の場合は None を返す。
    - rank: 同順位は平均ランクにする実装（丸め処理で ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を計算。
  - export: research パッケージで主要関数を __all__ にて公開。

- DB/運用周りの堅牢化
  - DuckDB ミドルウェアを前提に設計（sql 文内での NULL/欠損扱いに注意）。
  - executemany に対する DuckDB バージョン差異を考慮（空リストは送らないガード）。

### 修正 (Changed)
- なし（初回リリース）。

### 修正 (Fixed)
- なし（初回リリース）。

### 非推奨 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- 環境変数取り扱いに注意しており、API キー未設定時は明示的にエラーを返す箇所がある（OpenAI API キー等）。  
- .env の自動読み込みはテストなどで無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

備考 / 設計上の重要ポイント（要約）
- ルックアヘッドバイアスの回避: 各種スコアリング/判定で datetime.today()/date.today() を内部参照せず、必ず呼び出し側から target_date を受ける設計。
- フェイルセーフ: OpenAI 等の外部 API 失敗時はゼロやスキップで継続し、致命的停止を避ける方針（ただし API キー未設定は即時エラー）。
- テスト容易性: OpenAI 呼び出しを内部関数で切り出し、unittest.mock で差し替え可能。
- DB 書き込みは冪等化を意識（DELETE → INSERT、ON CONFLICT などを利用）し、例外時に ROLLBACK を実行する安全策を採用。

今後の改善想定（例）
- strategy / execution / monitoring の実装拡張（現状はパッケージ構成のみ露出）。
- より細かな品質チェックルールや監査ログ強化。
- OpenAI レスポンス検証のさらなる厳格化（スキーマ検証等）。
- テストカバレッジの拡充（特に外部 API 周りと DB 操作）。
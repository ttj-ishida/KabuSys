# Changelog

すべての重要な変更をこのファイルに記録します。形式は「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージの初期リリースを公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エントリポイント: src/kabusys/__init__.py（__all__ に data, strategy, execution, monitoring を公開）

- 設定・環境変数管理
  - Settings クラスを提供（src/kabusys/config.py）。
  - .env 自動読み込み機能を実装（プロジェクトルート判定：.git または pyproject.toml を探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env パーサを実装（export プレフィックス対応、クォート・エスケープ処理、インラインコメント処理）。
  - 環境変数の必須チェック（_require）、env/log_level のバリデーション、パスプロパティ（duckdb/sqlite path）を提供。

- AI 関連機能
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）へ送信し、ai_scores テーブルへ書き込み。
    - チャンク処理（デフォルト 20 銘柄/チャンク）、記事数/文字数トリム、JSON Mode の利用。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ実装。
    - レスポンスの厳密なバリデーションとスコア クリッピング（±1.0）。
    - DuckDB 互換性考慮（executemany に空リストを渡さない保護）。
    - calc_news_window ユーティリティ（タイムウィンドウ計算）を実装。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して market_regime へ書き込み。
    - マクロキーワードによる記事抽出、OpenAI への問い合わせ、API障害時のフェイルセーフ（macro_sentiment=0.0）。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理。
    - テスト時に差し替え可能な設計（_call_openai_api の差し替えを想定）。

- リサーチ・ファクター群（src/kabusys/research/）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と株価から PER / ROE を計算（EPS が 0/欠損時の保護）。
    - 全て DuckDB SQL ベースで計算し、外部 API に依存しない実装。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得（複数ホライズン対応）。
    - calc_ic: スピアマンランク相関（IC）を実装（結合・欠損除外、最小レコード数チェック）。
    - factor_summary: count/mean/std/min/max/median の統計サマリを実装。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ。
  - research パッケージで便利関数群を再エクスポート（zscore_normalize 等）。

- データプラットフォーム機能（src/kabusys/data/）
  - カレンダー管理（calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar 未取得時の曜日ベースフォールバック（週末を休日扱い）。
    - カレンダー夜間更新ジョブ calendar_update_job（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索範囲・バックフィル・サニティチェック等の安全策を導入。

  - ETL パイプライン（pipeline.py, etl.py）
    - ETLResult データクラスを定義（取得/保存レコード数、品質問題、エラー一覧、has_errors 等）。
    - 差分更新・バックフィル・品質チェックを想定した設計。jquants_client および quality モジュールと連携。
    - data.etl で ETLResult を再エクスポート。

- ロギングとエラー耐性
  - 各モジュールで詳細なログ出力（info/warning/debug/exception）を実装。
  - DB トランザクション失敗時のロールバック試行とロギング。
  - LLM/API 失敗は例外を投げずフォールバックする設計の箇所が多数（フェイルセーフ）。

- テスト容易性
  - OpenAI 呼び出しを内部関数化し、テスト時に patch により差し替え可能な設計を採用。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- DuckDB の executemany に空リストを渡すと失敗する制約に対応（空チェックを挟む）：
  - news_nlp.score_news のデータベース書き込み時に対応。
- ニュース NLP レスポンスパースの強化：
  - JSON Mode でも前後に余計なテキストが混入する場合に最外の {} を抽出して復元するロジックを実装。
- .env パースの堅牢化：
  - export プレフィックス対応、クォート内エスケープ処理、インラインコメント扱いの改善。

### セキュリティ (Security)
- OpenAI API キーの取り扱い：
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必須とし、未設定時は ValueError を送出して誤用を防止。
- .env 自動ロード時に既存 OS 環境変数を保護する仕組みを導入（読み込み時 protected set を利用）。

### 既知の制約 / 注意事項 (Known issues / Notes)
- research モジュールは DuckDB の prices_daily / raw_financials を前提とする（外部データ依存）。
- datetime.today()/date.today() を内部で参照しない設計（ルックアヘッドバイアス対策）。ETL/スコアリングは target_date を明示的に渡して使用すること。
- OpenAI 呼び出し周りは外部サービスに依存するため、API 仕様変更や認証方式の変化に注意が必要。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、故意に共有していない（モジュール間の密結合回避）。

---

（将来の変更はこのファイルに日付順・セクション別に記録してください。）
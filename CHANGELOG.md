# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトの最初の公開リリースを記録しています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
  - パッケージ公開用の top-level エクスポート: __all__ に data, strategy, execution, monitoring を定義（将来的なサブパッケージ構成を想定）。

- 環境設定・自動 .env ロード機能 (src/kabusys/config.py)
  - プロジェクトルートを .git または pyproject.toml から探索して自動で .env / .env.local を読み込む機能を実装。
  - .env のパース機能を実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメント処理（クォート有無での挙動差分）対応
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。既存 OS 環境変数を保護するため protected セットを使用して上書きを制御。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）や既定値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH）を取得できるように実装。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。is_live / is_paper / is_dev のユーティリティプロパティを提供。

- ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を評価して ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ計算（JST 基準: 前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）。
  - バッチ処理: 最大 20 銘柄単位で API コール、1 銘柄あたり最大記事数・文字数でトリム。
  - 再試行ポリシー: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
  - JSON Mode のレスポンスを厳密にバリデーション（results リスト・code/score 構造・既知コード照合・数値チェック）し、スコアを ±1.0 にクリップ。
  - 部分失敗に強い DB 書き込みロジック: 取得済みコードのみを DELETE → INSERT（部分失敗時に既存スコアを保護）。
  - テスト容易性を考慮し、OpenAI 呼び出し関数をモック差替え可能に設計。

- 市場レジーム判定モジュール (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
  - prices_daily から ma200_ratio を計算し、raw_news をマクロキーワードでフィルタして LLM（gpt-4o-mini）へ送信して macro_sentiment を算出。
  - API 失敗時は macro_sentiment=0.0 としてフェイルセーフで継続する設計。
  - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルを更新。
  - LLM 呼び出し部分は news_nlp と独立した実装にしてモジュール結合を抑制。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）等の定量ファクター計算関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を用いた堅牢な実装で、データ不足時は None を返す挙動。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic：Spearman の ρ）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を使用せず標準ライブラリで完結する設計。
  - research パッケージの __init__ で主要関数を再エクスポート。

- データプラットフォーム（Data）モジュール (src/kabusys/data/)
  - calendar_management.py:
    - JPX カレンダー（market_calendar）を用いた営業日判定・next/prev_trading_day・get_trading_days・is_sq_day 等の実装。
    - DB にカレンダーがない場合は曜日ベースでフォールバック（週末除外）。
    - calendar_update_job を実装し、J-Quants API（jquants_client）から差分取得して冪等保存。バックフィルや健全性チェックを備える。
  - pipeline.py / etl.py:
    - ETLResult dataclass を実装して ETL の実行結果（取得数・保存数・品質問題・エラー等）を表現。
    - ETL の差分更新・バックフィル・品質チェック・idempotent 保存（jquants_client の save_* を想定）など設計を明記。
    - data.etl は ETLResult を再エクスポート。

### 変更 (Changed)
- 設計方針・実装上の「安全策」を明示的に採用:
  - すべての時刻計算で datetime.today() / date.today() を直接参照しない（ルックアヘッドバイアス防止のため）。多くの関数は target_date を引数で受け取る設計。
  - DuckDB に対する executemany の空リストバインドに対する互換性チェックを導入（空時には実行をスキップ）。
  - OpenAI 呼び出しに対する詳細な例外分類とリトライ方針を統一（RateLimitError / APIConnectionError / APITimeoutError / APIError の扱い等）。

### 修正 (Fixed)
- エラーハンドリングの堅牢化:
  - DB 書き込み失敗時のトランザクション（ROLLBACK）を確実に試行し、ROLLBACK 自体が失敗した場合にも警告ログを出すようにした。
  - OpenAI レスポンスの JSON パース失敗や非期待フォーマットに対し、該当チャンクをスキップして処理継続するフェイルセーフを導入。

### 注意点 / 既知の制約 (Notes)
- OpenAI API キーは関数引数(api_key) で注入可能。引数が None の場合は環境変数 OPENAI_API_KEY を参照する。未設定だと ValueError を送出する。
- news_nlp と regime_detector の OpenAI 呼び出しはそれぞれ独立実装であり、テスト時は内部の _call_openai_api をパッチしてモック可能。
- config.Settings の自動 .env ロードはプロジェクトルート検出に .git / pyproject.toml を使用するため、パッケージ配布後の挙動にも配慮しているが、プロジェクトルートが見つからない場合は自動ロードをスキップする。
- __all__ に含まれる strategy / execution / monitoring パッケージはトップレベルの公開枠として記載されているが、本リリースに含まれるのは主に data, ai, research 関連モジュール。将来のサブパッケージ拡張を想定。

### セキュリティ (Security)
- このリリースで特に報告されたセキュリティ修正はありません。

---

今後のリリース案内（例）
- マイナーリリース: API の安定化、追加のファクターや戦略実装、strategy / execution / monitoring サブパッケージの実装
- パッチリリース: バグ修正、OpenAI SDK の非互換対応、DuckDB バージョン差分への対応

（必要に応じて各モジュール別の詳細な変更履歴を追記できます。）
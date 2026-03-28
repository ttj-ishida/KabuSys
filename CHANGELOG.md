# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ初期リリース。モジュール群を追加。
  - kabusys
    - パッケージメタ情報（__version__ = "0.1.0"）。
  - kabusys.config
    - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
      - 読み込み優先順位: OS環境変数 > .env.local > .env
      - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
      - .env パーサ: コメント、`export KEY=val`、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
      - 読み込み失敗時は警告を出力して継続。
      - OS 環境変数を保護するための protected キーセット機能を実装（上書き制御）。
    - Settings クラスを提供し、以下の設定プロパティを環境変数から取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live のバリデーション）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
      - 環境チェック用のユーティリティプロパティ: is_live / is_paper / is_dev
  - kabusys.ai
    - news_nlp モジュール（score_news）
      - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode で銘柄ごとのセンチメント（-1.0〜1.0）を計算して ai_scores テーブルへ永続化。
      - 処理仕様:
        - タイムウィンドウ：前日 15:00 JST ～ 当日 08:30 JST（UTC で前日 06:00 ～ 23:30）をサポート（calc_news_window）。
        - 1銘柄あたり最大記事数: 10、最大文字数トリム: 3000 文字。
        - バッチサイズ: 最大 20 銘柄 / API 呼び出し。
        - レスポンス検証: JSON パース、results 配列、code と score の妥当性チェック、スコアの ±1.0 クリップ。
        - リトライ: 429, ネットワーク断, タイムアウト, 5xx に対して指数バックオフで再試行（デフォルト上限）。
        - フェイルセーフ: API 失敗やパース失敗時は該当チャンクをスキップし、処理を継続。
        - テスト容易性: OpenAI 呼び出し関数を patch で差し替え可能。
      - DB 書き込みは部分失敗を考慮して、取得済みコードのみ DELETE → INSERT の置換で書き込む実装。
    - regime_detector モジュール（score_regime）
      - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して日次の市場レジームを判定（bull / neutral / bear）。
      - 処理仕様:
        - MA 乖離を ma200_ratio として計算し、足りないデータは中立(1.0)にフォールバック。
        - マクロ記事はマクロキーワードに基づき最大 20 件を取得し、OpenAI（gpt-4o-mini）にて macro_sentiment を評価。
        - 合成式: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
        - しきい値: bull if >= 0.2, bear if <= -0.2、その他は neutral。
        - API エラー・パース失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
        - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。
      - OpenAI 呼び出しは独立実装で news_nlp と内部関数を共有しない設計（モジュール結合を軽減）。
  - kabusys.research
    - factor_research モジュール
      - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）を計算。
      - Volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
      - Value: PER（株価 / EPS）、ROE（raw_financials から取得）。
      - DuckDB を利用した SQL ベース実装で、prices_daily / raw_financials を参照。データ不足時は None を返す。
    - feature_exploration モジュール
      - calc_forward_returns: 指定ホライズン（日数）先の将来リターンを一括 SQL で取得（デフォルト [1,5,21]）。
      - calc_ic: スピアマンランク相関（Information Coefficient）を計算。利用不可（レコード数 < 3）の場合は None を返す。
      - rank: 同順位は平均ランクで処理（丸めで ties を安定検出）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - kabusys.data
    - calendar_management モジュール
      - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ:
        - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
      - DB 登録がない / NULL の場合は曜日（土日）ベースでフォールバックする一貫した挙動。
      - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得→保存、バックフィル・健全性チェックあり）。
      - 最大探索範囲やバックフィル日数等の安全パラメータを導入。
    - pipeline / etl モジュール
      - ETLResult データクラスを公開（etl の実行結果トラッキング用）。
      - 差分取得、保存（idempotent）、品質チェック（quality モジュールとの連携）に基づく ETL パイプラインの基礎実装（設計文書に準拠）。
      - 保存件数・取得件数・品質問題・エラー一覧を ETLResult で返却。
    - jquants_client, quality 等のクライアント / 品質チェック連携を想定した設計（実装ファイルの分割を前提）。
  - テスト・運用面の配慮
    - 各所で lookahead（datetime.today() / date.today() の直接参照）を避ける実装によりルックアヘッドバイアスを防止。
    - OpenAI 呼び出し関数が patch で差し替え可能（テスト容易性）。
    - DuckDB 互換性を考慮した executemany 空リスト回避ロジックの実装。

### 変更 (Changed)
- 初回リリースにつき該当なし。

### 修正 (Fixed)
- 初回リリースにつき該当なし。

### 破壊的変更 (Deprecated / Removed)
- 初回リリースにつき該当なし。

### セキュリティ (Security)
- API キー（OpenAI）は関数引数で注入可能（テスト・運用での安全性向上）。
- 環境変数の自動ロードで OS 環境変数が上書きされないよう protected 機構を導入。

### 既知の制限・注意点 (Known issues / Notes)
- OpenAI API 呼び出しは gpt-4o-mini を想定しており、利用には OPENAI_API_KEY が必要。未設定時は ValueError を送出する。
- DuckDB のバージョン差異により list 型バインドが不安定なため、DELETE は executemany を用いた個別削除で実装している。
- ai_scores / market_regime などの書き込みは部分失敗を避けるため、取得済みコードのみ置換する設計だが、同時実行や外部トランザクションとの相互作用は運用で注意が必要。
- calendar_update_job 等は外部 J-Quants クライアントのエラーや API 仕様変更の影響を受けるため、実運用ではリトライや監視を推奨。

---

このリリースは機能実装主体の初期版（0.1.0）です。今後、ユニットテストの追加、ドキュメント整備、OpenAI モデル/パラメータの運用チューニング、例外ハンドリングの改善などを予定しています。
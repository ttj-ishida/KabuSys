# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-04

初回リリース。

### 追加
- 基本パッケージ構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装
    - プロジェクトルートは .git または pyproject.toml を基準に探索（__file__ 起点で探索するため CWD に依存しない）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
    - OS 環境変数を保護するための protected キーセットを使用し、.env.local は既存環境変数を上書き可能
  - .env パーサの実装
    - コメント行、`export KEY=val` 形式、クォートされた値（エスケープ対応）、インラインコメント（条件付き）に対応
  - Settings クラスによるアプリケーション設定の提供
    - J-Quants / kabuステーション / LINE / データベースパス / 監視設定 / システム設定等のプロパティを提供
    - 環境変数の必須チェック (_require) と値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）
    - パスは Path 型で返却し expanduser を適用
    - 監視用設定（PID ファイル、kill フラグ、閾値など）を提供

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini, JSON mode）へバッチ送信
    - JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）
    - 1銘柄あたりの記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）
    - バッチ処理（最大 _BATCH_SIZE 銘柄）・最大20銘柄ごとに送信
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ）
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code と score の型チェック、スコアの有限性確認）
    - スコアは ±1.0 にクリップ、ai_scores テーブルへ部分置換（DELETE → INSERT）して部分失敗時に他コードを保護
    - テスト用に _call_openai_api を patch 可能に設計
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定
    - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足時は中立 1.0 にフォールバック）
    - マクロニュースは raw_news からキーワードで抽出（最大件数制限）
    - OpenAI 呼び出しのリトライ・エラーハンドリング（API の各種例外に対応、フェイルセーフとして macro_sentiment=0.0 にフォールバック）
    - レジームスコア合成と閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、ROLLBACK 処理あり）
    - OpenAI client は引数/環境変数で API キーを解決

- データ管理 / ETL (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー（market_calendar）に基づく営業日判定ユーティリティを提供
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を非営業日扱い）
    - DB 登録値優先、未登録日は曜日ベースフォールバックで一貫性を確保
    - 夜間バッチ更新 job (calendar_update_job)：J-Quants API から差分取得し保存、バックフィルと健全性チェックを実装
  - ETL パイプライン基盤 (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを実装（取得/保存件数・品質問題・エラーの集約）
    - 差分更新・バックフィル・品質チェックの設計方針を実装するための基礎を提供
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを含む
    - jquants_client と quality モジュールとの統合を想定

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
      - データ不足銘柄は None を返す
    - ボラティリティ / 流動性: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率
      - true_range の NULL 伝播制御、ウィンドウ内不足時は None を返す
    - バリュー: PER（EPS が 0/欠損時は None）、ROE（raw_financials からの最新値を結合）
    - DuckDB 上での SQL ベース実装／返却形式は dict のリスト（date, code をキー）
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns): 複数ホライズン対応、入力検証（horizons の値域チェック）、LEAD を用いた単一クエリ取得
    - IC（Information Coefficient）計算 (calc_ic): Spearman 的ランク相関（ランクは同順位は平均ランク）を算出、十分なサンプルがない場合は None
    - rank ユーティリティ: 同順位は平均ランク、round(v, 12) により ties の検出安定化
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を計算

- ロギング・堅牢性
  - 各モジュールで詳細な logger を使用して情報・警告・例外を記録
  - DB 書き込みはトランザクションで行い、ROLLBACK 処理と失敗時のログ出力を実装
  - API 呼び出し失敗時はフェイルセーフ（スコア 0.0 や処理スキップ）で継続する設計

### 既知の設計上の注意点
- OpenAI 呼び出しは gpt-4o-mini と JSON mode を想定しているため、実際の利用時は対応する SDK と API の挙動に注意してください。
- DuckDB の executemany の挙動（空リスト不可）に配慮した実装を行っていますが、使用する DuckDB のバージョンに依存する挙動に注意してください。
- 一部インターフェース（例: jquants_client, quality モジュール）はこのコードベースから参照されていますが、外部の実装が必要です。
- パッケージの __all__ には "strategy", "execution", "monitoring" が含まれますが、本リリースのスニペットには該当モジュールの実装が含まれていません（将来的な追加想定）。

### マイグレーション / 互換性
- 初回リリースのため互換性破壊は該当しません。

---

今後のリリースでは、strategy / execution / monitoring 周りの実装、テストカバレッジの拡充、外部 API クライアントの抽象化やモック用フックの追加などを予定しています。必要があれば CHANGELOG を追って詳細を書き足します。
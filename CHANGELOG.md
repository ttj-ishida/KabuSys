# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従っています。  
タグ付けやリリースは SemVer を使用します。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下のとおりです。

### 追加
- パッケージ基盤
  - kabusys パッケージの公開エントリポイントを追加（data, strategy, execution, monitoring を公開）。
  - バージョン情報を __version__ = "0.1.0" に設定。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定値を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数により自動ロードを無効化可能（テスト用）。
    - .git または pyproject.toml を基準にプロジェクトルートを探索して自動ロード（CWD 非依存）。
  - .env のパースはシェル形式（export KEY=val、シングル/ダブルクォート、インラインコメント等）に対応。
  - 環境変数保護機能（読み込み時に既存 OS 環境変数を protected として上書き防止）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを取得可能。
    - KABUSYS_ENV の値検証（development / paper_trading / live）
    - LOG_LEVEL の値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の補助プロパティ

- データ基盤（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日ロジックを実装
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を休日扱い）
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得 → 冪等保存）
    - 最大探索日数やバックフィル、健全性チェックの導入で無限ループや異常を防止
  - pipeline / etl / ETLResult: ETL パイプラインのインターフェースと結果データクラスを実装
    - 差分更新、バックフィル、品質チェック（kabusys.data.quality 参照）の想定設計
    - ETLResult に品質問題・エラー一覧・集計値を保持し to_dict 出力を提供（監査ログ向け）
  - etl/pipeline モジュールは DuckDB を前提とした差分取得・保存ロジックを想定

- AI・NLP（kabusys.ai）
  - news_nlp: ニュース記事の銘柄ごとセンチメント集約スコアリング機能を実装
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST に対応）
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数・文字数の上限でトリム）
    - OpenAI (gpt-4o-mini) の JSON Mode を用いたバッチスコアリング（最大 20 銘柄/チャンク）
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ
    - レスポンスのバリデーション・スコアの ±1.0 クリップ
    - 部分失敗発生時に既存データを保護するため、スコア取得済みコードのみ DELETE → INSERT（冪等）
    - テスト用フック: _call_openai_api を patch して差し替え可能
  - regime_detector: 市場レジーム判定（bull/neutral/bear）を実装
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成
    - OpenAI を用いたマクロセンチメント評価（gpt-4o-mini、JSON 出力想定）
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 としてフェイルセーフ
    - レジームスコア計算後、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - テスト用フック: _call_openai_api を patch して差し替え可能
  - 共通設計方針:
    - datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取ることでルックアヘッドバイアスを排除
    - OpenAI API 呼び出しは明示的にクライアントを生成して安全に扱う

- リサーチ（kabusys.research）
  - factor_research: モメンタム / バリュー / ボラティリティ等のファクター計算を実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（データ不足時の None ハンドリング）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - calc_value: PER（EPS が 0 または欠損なら None）、ROE（raw_financials から最新値）
    - DuckDB の SQL ウィンドウ関数を活用した実装
  - feature_exploration: 将来リターンや IC（Spearman）・統計サマリー等のユーティリティを実装
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算
    - calc_ic: ランク相関（Spearman）を実装、データ不足時に None を返す
    - rank / factor_summary: ランク付け（同順位は平均ランク）や基本統計量計算を提供
    - 標準ライブラリのみで実装（pandas 等に依存しない）

- DuckDB を中心とした永続化を前提に各所で SQL を利用
  - 各モジュールは DuckDB 接続（DuckDBPyConnection）を受け取り、prices_daily / raw_news / raw_financials / market_calendar / ai_scores / market_regime 等のテーブル操作を行う

### 変更（設計上の注意）
- OpenAI 呼び出しに関するエラーハンドリングを堅牢化（リトライ・ログ・フォールバック）
- DB への書き込みは冪等性を重視（DELETE → INSERT や ON CONFLICT を想定）
- DuckDB の実装差異（executemany の空リスト等）を考慮した防御的実装
- 市場カレンダー未登録時のフォールバックや健全性チェックを導入して運用安全性を確保

### 修正（バグ修正・堅牢化）
- API レスポンスの JSON パース失敗や不整合に対してスキップして継続するフェイルセーフを導入（例: news_nlp / regime_detector）
- .env 読み込み時のファイル読み込み失敗を警告に留める実装（IOError を捕捉）
- レスポンス中の数値型変換や有限性チェックを追加し、NaN/Inf 等の異常値を除外

### テスト支援
- OpenAI 呼び出し部分に対して unittest.mock.patch で差し替え可能な内部関数を用意（テスト容易性向上）
- 環境変数自動ロードの抑止フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）により CI/テストでの副作用を回避可能

### ドキュメント（コード内）
- 各モジュールに設計方針や処理フロー、重要な注意点（ルックアヘッド回避、フェイルセーフ挙動等）を詳細にコメントとして記載

---

今後のリリースでは、strategy / execution / monitoring の実装拡充、J-Quants API クライアント実装の公開、より詳細な品質チェック（quality モジュール）の追加、テストカバレッジ向上、その他運用向け機能（メトリクス / アラート / Slack 通知等）を予定しています。
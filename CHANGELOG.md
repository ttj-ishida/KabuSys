# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従い、セマンティックバージョニングを使用します。

- リリース日付はコミット時点のソースから推測しています。
- 記載はコード内容から実装された機能・設計意図・安全策等を推測してまとめたものです。

## [Unreleased]
（無し）

## [0.1.0] - 2026-03-31
初回リリース。本パッケージは日本株のデータ取得・ETL・研究（リサーチ）・AIベースのニュース／市場レジーム判定を含む一連の基盤機能を提供します。

### Added
- パッケージ基盤
  - kabusys パッケージの公開インターフェースを追加（data, strategy, execution, monitoring を __all__ で公開）。
  - パッケージバージョンを "0.1.0" として定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - 自動ロード順序: OS環境変数 > .env.local > .env
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、__file__ を起点に親ディレクトリを探索（CWD に依存しない方式）。
  - .env ファイルの柔軟なパースを実装:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート、バックスラッシュによるエスケープ対応
    - 行コメントの扱い（クォート有無に応じた挙動）
  - 環境変数の保護機構:
    - OS 環境変数を protected として .env の上書きを防止するオプション（override フラグ、protected set）。
  - 必須環境変数取得用のヘルパー _require と、Settings クラスを追加:
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供
    - KABUSYS_ENV, LOG_LEVEL のバリデーション（許容値チェック）
    - is_live / is_paper / is_dev の判定ヘルパー

- AI モジュール (kabusys.ai)
  - ニュースセンチメント (kabusys.ai.news_nlp)
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ保存する処理を実装。
    - ニュース収集ウィンドウ計算 (calc_news_window)：JST ベースのウィンドウ（前日 15:00 ～ 当日 08:30）を UTC naive datetime で返す。
    - バッチ処理: 最大 20 銘柄ずつ API に送信、1 銘柄あたりの記事数・文字数上限を採用（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しは JSON mode を想定し、レスポンスのバリデーション・抽出ロジックを実装（_validate_and_extract）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装（_MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - レスポンスの安全性確保:
      - スコアは ±1.0 にクリップ
      - JSON パース失敗やバリデーション不備は該当チャンクをスキップして継続（フェイルセーフ）
      - DuckDB の executemany の互換性を考慮した書き込み（部分書き換え: 対象コードのみ DELETE → INSERT）
    - テスト用の差し替えポイント: _call_openai_api を unittest.mock.patch で差し替え可能に設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - 処理フロー:
      - ma200_ratio 計算（_calc_ma200_ratio）: target_date 未満のデータのみを用いることでルックアヘッドバイアスを防止。データ不足時は中立（1.0）を採用。
      - マクロキーワードで raw_news をフィルタしてタイトルを取得（_fetch_macro_news）。
      - OpenAI を使ってマクロセンチメント評価（_score_macro）、API エラー時は 0.0 でフォールバック。
      - 合成スコアは重み付け（デフォルト: MA 70%, マクロ 30%）して -1.0〜1.0 にクリップ。
      - 結果を market_regime テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行。
    - OpenAI 呼び出しは個別実装でモジュール結合を避ける設計。

- データ基盤 (kabusys.data)
  - ETL パイプライン
    - ETLResult データクラスを pipeline モジュールに実装し、data.etl で再エクスポート。
    - ETLResult は取得件数・保存件数・品質チェック結果・エラー一覧等を保持し、has_errors / has_quality_errors の簡易判定・辞書化 to_dict を実装。
    - ETL パイプライン設計: 差分更新、バックフィル、品質チェックの方針をソース内ドキュメントで明示。
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを用いた営業日判定ユーティリティ群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダー情報がない場合は曜日ベース（週末除外）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新する夜間バッチロジックを提供。
      - バックフィル日数、先読み日数、健全性チェック（極端な将来日付の検出）などを実装。
    - 内部ユーティリティ: テーブル存在確認、NULL ハンドリング、DuckDB からの date 型変換などを実装。

- 研究（Research）モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を銘柄ごとに計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。true_range の NULL 伝搬制御を考慮。
    - calc_value: raw_financials から最新の EPS/ROE を取って PER/ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB ベースの SQL+Python 実装で外部 API に依存しない設計。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算するクエリを実装（LEAD を使用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算する関数。レコード数が少ない場合は None を返す。
    - rank: 同順位は平均ランクにするランク変換ユーティリティ（浮動小数の丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - research パッケージの __all__ を整備して上記関数を公開。

### Changed
- （初回リリースのため、既存機能の変更履歴は無し）

### Fixed
- （初回リリースのため、バグ修正履歴は無し）

### Security
- OpenAI API キーの取り扱い:
  - 関数は api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照する設計。キー未設定時は ValueError を発生させるようにしており、誤使用を防止。

### Notes / 設計方針（ドキュメント的な変更）
- ルックアヘッドバイアス回避:
  - AI/スコアリング系関数（score_news, score_regime 等）は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB クエリは target_date 未満や排他条件を利用して未来情報の利用を防止。
- フェイルセーフ志向:
  - 外部 API 失敗時は例外で全体を止めるのではなく、該当チャンクやスコアを 0.0/スキップ として継続できるようにしている（運用安全重視）。
- テスト容易性:
  - OpenAI 呼び出しポイント（_call_openai_api）を patch 可能にし、ユニットテストで外部呼び出しを差し替えられるよう配慮。
- DuckDB 互換性:
  - executemany の空リスト回避、list 型バインドの不安定性回避など DuckDB の制約を考慮した実装。

--- 

今後のリリースで想定される追加項目（例）
- strategy / execution / monitoring の具体実装と統合テスト
- エンドツーエンド ETL / スコアリングの CI テストケース
- より詳細なエラーロギング・メトリクス（Prometheus 等）やアラート連携
- OpenAI レスポンスフォーマットの堅牢化（スキーマ検証・サニタイズ）

（この CHANGELOG はソースコードの現状から推測して作成しています。実際のコミット履歴やリリースノートに合わせて適宜調整してください。）
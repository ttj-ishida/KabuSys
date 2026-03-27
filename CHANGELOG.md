# Changelog

すべての注記は Keep a Changelog の形式に従い、重要な変更・追加点を日本語でまとめています。

全般方針:
- バージョンは semantic versioning に準拠します。
- 日付はコードベース解析時点の推測（2026-03-27）を使用しています。
- 実装上の設計判断やフェイルセーフ挙動、外部依存（DuckDB / OpenAI など）の取り扱いも記載しています。

## [Unreleased]
- 現在の開発継続中の変更はここに記載します。

## [0.1.0] - 2026-03-27

### Added
- パッケージの基礎
  - kabusys パッケージ初期リリース。主要サブパッケージとして data, research, ai, execution, monitoring, strategy（__all__ に含む）を公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 高度な .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。
  - auto-load を無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得（J-Quants / kabu ステーション / Slack / DB パス / 環境種別 / ログレベルなど）。
  - 必須環境変数未設定時は ValueError を送出する _require 実装。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値の検査）を実装。
  - OS 環境変数の保護（.env 上書きのルール）をサポート。

- AI 関連 (kabusys.ai)
  - ニュースセンチメント（score_news）と市場レジーム判定（score_regime）を実装。
  - OpenAI（gpt-4o-mini + JSON mode）を用いた API 呼び出しを行い、レスポンスのバリデーションとフェイルセーフ（API 失敗時はスコアを 0 にフォールバック）を実装。
  - news_nlp:
    - ニュースウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30）を実装。
    - raw_news と news_symbols を集約して銘柄ごとにテキストをまとめ、最大文字数・記事数でトリム。
    - バッチ処理（1 回につき最大 20 銘柄）で API 呼び出し。429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。
    - レスポンスの厳密な構造検証（results 配列、code/score の存在、数値変換、未知コード無視、スコアクリップ）を実装。
    - ai_scores テーブルへ冪等的に（DELETE→INSERT）スコアを保存。部分失敗時に既存スコアを保護する設計。
  - regime_detector:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて市場レジーム（bull/neutral/bear）を日次算出。
    - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロキーワードによる raw_news フィルタリング、最大取得記事数制限。
    - OpenAI 呼び出しは内部で独立実装し、失敗時は macro_sentiment=0.0 で継続。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- データ基盤ユーティリティ (kabusys.data)
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを定義し、取得数・保存数・品質問題・エラーの集約を提供。
    - 差分取得、バックフィル、品質チェックフローの設計方針を反映。
  - calendar_management:
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）実装（J-Quants API 経由で差分取得、バックフィル、健全性チェック、冪等保存）。
    - 営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - カレンダー未取得時の曜日ベースフォールバック（週末除外）を実装し、DB にある値を優先する一貫性を確保。
  - ETL / pipeline 内部ユーティリティ:
    - DuckDB 上でのテーブル存在確認や最大日付取得、トレーディング日調整ロジックを実装。

- Research / ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比）、
      バリュー（PER, ROE）を DuckDB クエリで計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、営業日ベースのホライズン取り扱い、ルックアヘッド防止のための date 範囲制御などを実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証）を実装。
    - IC（Information Coefficient）計算（スピアマンのランク相関）を実装（calc_ic）。
    - 値のランク変換（rank）とファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリで完結する設計。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Security
- 環境変数の必須チェックと .env 読み込み時の OS 環境変数保護を導入。
- OpenAI API キーは明示的に引数から注入可能（テスト容易化）で、未設定時は明示的なエラーにより早期検出。

### Notes / Implementation highlights
- ルックアヘッドバイアス防止: AI モジュール（news_nlp, regime_detector）やリサーチ系関数は datetime.today() / date.today() を直接参照せず、常に呼び出し側から target_date を受け取る設計。
- フェイルセーフ: LLM や外部 API 呼び出しの失敗は致命的にせず、0.0 やスキップで継続する挙動を優先（ログ出力あり）。ただし DB 書き込み失敗時は例外を伝播させる設計。
- DuckDB を主要なローカル分析 DB として利用。executemany の空配列を避けるなど DuckDB のバージョン差異に配慮した実装（互換性対策）。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なパースとバリデーションを行う（余計な前後テキストの復元ロジックも実装）。
- モジュール間の結合を低く保つため、内部の OpenAI 呼び出しヘルパー関数はファイル内で独立実装（テストでモック差し替え可能）。

---

将来的なリリースでは、以下が想定されます（今後の TODO／改善案の例）:
- ai スコア算出ロジックのチューニングおよびモデル切替のサポート。
- ETL のスケジューリング・観測用メトリクスの追加。
- execution（発注） / monitoring（監視）モジュールの実装拡充（現在 __all__ に含むが具象実装は別途）。
- 単体テスト・統合テストの充実（特に OpenAI 呼び出し周りのモック検証）。

もし必要であれば、この CHANGELOG をプロジェクトの現状（各ファイルの要点）に合わせてさらに詳細化します。どの粒度で記載するか（より短く／より詳細）を指定してください。
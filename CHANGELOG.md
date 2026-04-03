# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。

※以下はリポジトリ内のコード内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]
- 開発中の変更点や次リリース予定の項目をここに記載します。

---

## [0.1.0] - 2026-04-03
初期公開リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。__version__ = 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring を __all__ に設定。

- 設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサー実装（export 形式、クォートとエスケープ、インラインコメント扱いの考慮）。
  - override / protected オプションにより OS 環境変数を保護して .env.local を上書き可能。
  - 必須環境変数チェック (_require) と Settings クラスの公開（各種 API トークン、DB パス、監視閾値、環境/ログレベルのバリデーション等）。
  - 環境・ログレベルに対する許容値チェック（KABUSYS_ENV, LOG_LEVEL）。

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を算出・保存する処理を実装。
    - 時間ウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換して使用）。
    - バッチサイズ、記事数・文字数上限、レスポンスバリデーション、スコアクリップ（±1.0）。
    - API リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスの JSON モードでも前後ノイズを考慮した復元処理。
    - テスト容易性のため _call_openai_api をパッチ可能に設計。
    - ai_scores への冪等的な書き込み（DELETE → INSERT、部分失敗時の既存データ保護）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を組み合わせて日次レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存。
    - prices_daily からのデータ取得は lookahead バイアス防止のため target_date 未満のみを使用。
    - マクロニュース取得はキーワードフィルタを用い、記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0 を採用。
    - OpenAI 呼び出しは独立実装でモジュール間の密結合を避ける。
    - API エラー時のフォールバック（0.0）、リトライ、レスポンスパース失敗時の安全化。
    - market_regime への書き込みは BEGIN/DELETE/INSERT/COMMIT を用いた冪等処理とロールバック時の保護ログ。

- データ関連（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）に基づく営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未取得時は曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - カレンダー夜間バッチ更新ジョブ calendar_update_job（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数・先読み日数・バックフィル日数などの制御定数を実装。

  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを公開（ETL の取得件数・保存件数・品質問題・エラーを集約）。
    - 差分更新・バックフィル方針・品質チェックの設計に沿ったユーティリティの下地を実装。
    - DuckDB 互換性を考慮したテーブル存在チェックや最大日付取得ユーティリティ等（部分実装が含まれる）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR, 相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE） を DuckDB を用いて計算する関数を実装。
    - データ不足時の None 戻りとログ出力。
    - DuckDB 上のウィンドウ関数を活用した効率的な実装。
  - feature_exploration
    - 将来リターン計算（任意ホライズンの fwd リターン）、IC（Spearman の ρ）計算、ランク付けユーティリティ、ファクター統計サマリを実装。
    - 外部依存を持たず標準ライブラリで実装。

### Changed
- （初期リリースのため該当なし）

### Fixed / Hardening
- OpenAI レスポンス関連
  - レスポンスの JSON パース失敗や予期しない形式に対して安全にフォールバックし、例外を上位に投げず処理を継続するフェイルセーフ設計を適用（news_nlp / regime_detector）。
  - レート制限やネットワーク断、サーバーエラーに対して再試行（指数バックオフ）を実装。

- データベース操作
  - DuckDB の executemany に空リストを渡せない問題に対応するため、空チェックを行ってから実行する互換性処理を追加。
  - DB 書き込みは BEGIN/COMMIT/ROLLBACK を使用して冪等性と整合性を担保。ROLLBACK 失敗時は警告ログを出力。

- 時間の取り扱い
  - 全モジュールで datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアスの防止）。target_date を明示的に受け取る設計。

### Security
- 環境変数読み込み時に OS 環境変数を保護する機構（protected set）を用意し、.env による上書きを制御。

### Notes / 設計方針（重要）
- ルックアヘッドバイアス対策として、すべての時系列評定ロジックは target_date を明示的に受け取り、DB クエリでは target_date 未満・排他等の制御を行う。
- API キーは関数引数で注入可能（テスト容易性）、未指定時は OPENAI_API_KEY（環境変数）を参照。未設定時は ValueError を投げることで明示的に失敗させる。
- 外部 API の失敗は極力フェイルセーフ（スコア 0.0 などの中立値で継続）とし、システム全体の停止を避ける設計。
- DB 書き込みは可能な限り冪等に、部分失敗時に既存データを不必要に消さないよう配慮している。

---

開発・運用に関する補足や既知の制限はドキュメント（README / Design docs）に順次追加予定です。ご希望があれば、各モジュール毎に詳細な変更点や API 使い方のサンプルを追記します。
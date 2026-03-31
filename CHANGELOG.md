# Changelog

すべての重大な変更点をここに記載します。  
フォーマットは Keep a Changelog に準拠しています。  

なお、本ファイルの内容はソースコードから推測して作成したリリースノートです。実際のコミット履歴・差分に基づくものではなく、公開 API・挙動・設計上の注記を中心にまとめています。

## [Unreleased]

- なし

## [0.1.0] - 初期リリース
初版リリース。以下の主要機能群を実装・公開します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に含め公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定ロード機能を実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行うため CWD に依存しない。
  - .env と .env.local を読み込み、OS 環境変数を保護する protected 上書きロジックを実装。
  - export KEY=val 形式・クォートされた値（バックスラッシュエスケープ対応）・インラインコメントの扱いを考慮したパーサを実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を実装（テスト用等）。
  - 設定取得用 Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、環境種別、ログレベルなど）。
  - 必須環境変数未設定時は明確な例外メッセージを返す _require を実装。

- データプラットフォーム (kabusys.data)
  - ETL 基盤（pipeline）と ETL 結果を表す ETLResult を実装。
    - 差分取得、バックフィル、品質チェック、idempotent な保存（ON CONFLICT 相当）を想定した設計。
    - ETLResult は品質問題／エラー情報を収集して返す仕組みを提供。
  - マーケットカレンダー管理（calendar_management）
    - JPX カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得して保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
    - DB にカレンダーがない場合の曜日ベースフォールバック（週末除外）を実装。
    - カレンダーデータの不整合検出（NULL 値や極端な future date）に対する健全性チェックを実装。

- 研究用ユーティリティ (kabusys.research)
  - ファクター計算モジュール（factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER、ROE）を計算する関数を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、対象日を基準とした結果を返す設計。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns（将来リターン計算、複数ホライズン対応）
    - calc_ic（スピアマンのランク相関による IC 計算）
    - rank（同順位は平均ランクにするランク関数）
    - factor_summary（各ファクターの count/mean/std/min/max/median を計算）
  - zscore_normalize を含むデータ系ユーティリティ（kabusys.data.stats から再エクスポートを想定）。

- AI / NLP 機能 (kabusys.ai)
  - ニュース NLP スコアリング（news_nlp）
    - raw_news と news_symbols を基に、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信し、センチメントスコアを ai_scores に保存。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数トリム、JSON レスポンスの厳密バリデーションを実装。
    - 429・ネットワークエラー・タイムアウト・5xx に対する指数バックオフリトライを実装。失敗時は個別チャンクをスキップして継続するフェイルセーフ設計。
    - DuckDB の executemany に対する互換性（空リスト不可）を考慮して安全に DELETE/INSERT を行う処理。
    - calc_news_window で JST ベースのニュースウィンドウ計算（ルックアヘッド防止設計）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（Nikkei 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースに対する LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出用のキーワードリストを実装、OpenAI 呼び出しは専用実装でモジュール結合を避ける。
    - API リトライ、エラー時のフォールバック（macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス対策（target_date 未満のデータのみ参照、date.today() を直接参照しない）を設計上徹底。

### 変更 (Changed)
- 設計方針の明文化（ソース内 docstring・コメントでの記載）
  - ルックアヘッドバイアス対策、DuckDB の互換性、API 呼び出しのフェイルセーフ方針、idempotent 書き込み等を各モジュールで明示。

### 修正 (Fixed)
- エラーハンドリングとログ
  - DB 書き込み失敗時の ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログを出す扱いを実装。
  - OpenAI API レスポンスの JSON パース失敗や想定外フォーマットに対して警告ログを出し、継続するように実装（例外を投げずフォールバックする挙動）。

### セキュリティ (Security)
- API キー・機密情報の取り扱い
  - OpenAI API キーや各種トークンの取得は環境変数経由を原則とし、未設定時には ValueError で明示的にエラーを返す。
  - .env 自動ロード時に OS 環境変数を保護する仕組み（protected set）を実装。

### メモ / 注意点 (Notes)
- DuckDB を主要なデータストアとして想定しており、SQL（ウィンドウ関数等）でデータ処理を行う実装になっています。
- 日付・時間の扱いに関しては UTC naive datetime を DB 比較に使用する箇所があり、ニュースウィンドウ等は JST→UTC の変換ロジックを内部で計算しています。
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON Mode（response_format）でパース可能な JSON のみを要求する設計。レスポンスの妥当性チェックやトークン肥大対策（記事長トリム）を組み込んでいます。
- unit-test から差し替え可能な _call_openai_api の実装パターンを採用しており、外部 API をモックしてテスト可能です。
- DuckDB の executemany の仕様（空リスト不可など）に合わせた安全実装を行っています。

---

（補足）実際の運用や将来のリリースでは、各機能ごとに詳細な変更履歴（API 互換性、DB スキーマ、外部依存バージョン等）をコミット単位で記録することを推奨します。
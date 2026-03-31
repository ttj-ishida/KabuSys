# Changelog

すべての重要な変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョンはパッケージ内の __version__ に合わせて 0.1.0 としています。

なお、記載内容は提示されたコードベースの実装内容から推測して作成しています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初回リリース

### 追加
- 全体
  - 日本株自動売買システム「KabuSys」の初期実装を追加（パッケージ名: kabusys）。
  - パッケージのバージョンを 0.1.0 として設定。

- 設定 / 環境変数読み込み（kabusys.config）
  - Settings クラスを提供し、環境変数からアプリケーション設定を取得するインターフェースを実装。
  - .env/.env.local ファイルの自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .env パーサを実装し、export KEY=val 形式、引用符付き値（バックスラッシュエスケープ対応）、インラインコメント処理に対応。
  - OS 環境変数を保護する仕組み（読み込み時に protected set として上書き回避）を追加。
  - 必須環境変数取得用ヘルパー（_require）と各種プロパティ（J-Quants、kabuステーション、Slack、DB パス、監視閾値、実行環境・ログレベル判定など）を実装。
  - KABUSYS_ENV / LOG_LEVEL の値検証を実装（許容値以外は ValueError を送出）。

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む機能を実装（score_news）。
    - タイムウィンドウ計算（calc_news_window）を実装（JST に基づくウィンドウ、DB との比較は UTC naive datetime を使用）。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数トリム制御、JSON Mode を用いたレスポンスバリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライの実装。
    - レスポンス検証で不正なレスポンスはスキップ、スコアは ±1.0 にクリップ。
    - テスト用に OpenAI 呼び出しを差し替え可能（内部関数 _call_openai_api を patch 可能）。
    - API キーは引数で注入可能（api_key）／環境変数 OPENAI_API_KEY の両対応。未設定時は ValueError。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（score_regime）を実装。
    - prices_daily からの MA200 計算、raw_news からマクロキーワードに合致するタイトル抽出、OpenAI API 呼び出しによる macro_sentiment 評価を実装。
    - API 障害時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを採用。
    - 出力を market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込む処理を実装。
    - Look-ahead バイアス防止設計（date.today()/datetime.today() を直接参照しない、DB クエリに排他条件を付与）。

- 研究（kabusys.research）
  - factor_research モジュール
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）を DuckDB 上の prices_daily / raw_financials を使って計算する実装を追加。
    - 各関数は (date, code) をキーとする dict のリストを返す設計。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）・IC（calc_ic）・統計サマリー（factor_summary）・ランク関数（rank）を実装。
    - pandas 等外部依存なしで標準ライブラリ + DuckDB による実装。
  - 研究用ユーティリティとして zscore_normalize を data.stats から再エクスポート。

- データ基盤（kabusys.data）
  - calendar_management
    - market_calendar を用いた営業日判定・探索ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 未取得時の曜日ベースフォールバック、DB のある場合は DB 値を優先する一貫した挙動を実装。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API 経由で差分取得・バックフィル・健全性チェック・冪等保存）。
  - ETL / pipeline
    - ETLResult データクラス（ターゲット日や取得/保存件数、品質問題・エラーの集約）を実装し公開（kabusys.data.etl 経由で再エクスポート）。
    - 差分更新・バックフィル・品質チェック連携を想定した設計（jquants_client, quality モジュールとの連携箇所を含む）。
  - DuckDB を主体としたデータアクセス設計を採用し、DB 書き込み時はトランザクション（BEGIN/COMMIT/ROLLBACK）で安全に処理。

- ロギング・堅牢性
  - 各所で WARNING / INFO / DEBUG ログを適切に出力。
  - DB 書き込み失敗時の ROLLBACK、ROLLBACK 失敗時の警告ログを実装。
  - 各モジュールで入力チェック、NULL / 不足データ時のフォールバックを明示的に扱う。

### 変更
- なし（初回リリースのため）

### 修正
- .env パーサの強化
  - export プレフィックス対応、引用符付き文字列のバックスラッシュ・エスケープ処理、インラインコメント取り扱い等を実装し実用性を高めた。
  - override / protected の概念を導入し、OS 環境変数を誤って上書きしないようにした。

### 既知の設計上の注意点（ドキュメント的補足）
- OpenAI 呼び出しは gpt-4o-mini と JSON モードを想定している。API レスポンスの形が変わる可能性があるため、テスト時は内部の _call_openai_api をモックすることを想定している。
- レジーム判定およびニューススコアリングでは API 障害時に 0.0 を返すフェイルセーフを採用しており、完全な可用性を保証するものではない（ポリシー上の判断や運用時の監視が必要）。
- DuckDB executemany に空リストを渡せないバージョン依存の回避処理を組み込んでいる（空時は実行しない）。

### セキュリティ
- OpenAI（OPENAI_API_KEY）、J-Quants、KabuAPI、Slack トークン等の機密情報は環境変数経由で供給する設計。未設定時は ValueError を送出して処理を中断する箇所があるため、環境の設定を忘れないよう注意。

---

今後のリリースで想定される改善案（例）
- ETL/pipeline の具体的な差分取得処理・スケジューリングロジックの実装拡充
- テストカバレッジ向上（ユニット・統合テストの追加）
- OpenAI 呼び出しの抽象化（複数プロバイダ対応）やコスト制御の追加
- モデルやプロンプトのチューニング、応答検証の厳格化

※ 本 CHANGELOG はコードから仕様・実装を推測して作成しています。実際のリリースノート作成時はコミット履歴やリリースポリシーに基づいた調整を推奨します。